##############################################################################
#
# Copyright (c) 2002 Nexedi SARL and Contributors. All Rights Reserved.
#                    Jean-Paul Smets-Solanes <jp@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import cPickle, sys
from hashlib import sha1
from DateTime import DateTime
from zLOG import LOG, WARNING, ERROR
from ZODB.POSException import ConflictError
from cStringIO import StringIO

import transaction

# Error values for message validation
EXCEPTION      = -1
VALID          = 0
INVALID_PATH   = 1
INVALID_ORDER  = 2

# Time global parameters
MAX_PROCESSING_TIME = 900 # in seconds
VALIDATION_ERROR_DELAY = 30 # in seconds

class Queue(object):
  """
    Step 1: use lists

    Step 2: add some object related dict which prevents calling twice the same method

    Step 3: add some time information for deferred execution

    Step 4: use MySQL as a way to store events (with locks)

    Step 5: use periodic Timer to wakeup Scheduler

    Step 6: add multiple threads on a single Scheduler

    Step 7: add control thread to kill "events which last too long"

    Some data:

    - reindexObject = 50 ms

    - calling a MySQL read = 0.7 ms

    - calling a simple method by HTTP = 30 ms

    - calling a complex method by HTTP = 500 ms

    References:

    http://www.mysql.com/doc/en/InnoDB_locking_reads.html
    http://www.python.org/doc/current/lib/thread-objects.html
    http://www-poleia.lip6.fr/~briot/actalk/actalk.html
  """

  #scriptable_method_id_list = ['appendMessage', 'nextMessage', 'delMessage']

  def __init__(self):
    self.is_initialized = 0

  def initialize(self, activity_tool):
    # This is the only moment when
    # we can set some global variables related
    # to the ZODB context
    if not self.is_initialized:
      self.is_initialized = 1

  def deleteMessage(self, activity_tool, m):
    if not getattr(m, 'is_deleted', 0):
      # We try not to delete twice
      # However this can not be garanteed in the case of messages loaded from SQL
      activity_tool.deferredDeleteMessage(self, m)  
    m.is_deleted = 1

  def dequeueMessage(self, activity_tool, processing_node):
    raise NotImplementedError

  def distribute(self, activity_tool, node_count):
    raise NotImplementedError

  def validate(self, activity_tool, message, check_order_validation=1, **kw):
    """
      This is the place where activity semantics is implemented
      **kw contains all parameters which allow to implement synchronisation,
      constraints, delays, etc.

      Standard synchronisation parameters:

      after_method_id   --  never validate message if after_method_id
                            is in the list of methods which are
                            going to be executed

      after_message_uid --  never validate message if after_message_uid
                            is in the list of messages which are
                            going to be executed

      after_path        --  never validate message if after_path
                            is in the list of path which are
                            going to be executed
    """
    try:
      if activity_tool.unrestrictedTraverse(message.object_path, None) is None:
        # Do not try to call methods on objects which do not exist
        LOG('CMFActivity', WARNING,
           'Object %s does not exist' % '/'.join(message.object_path))
        return INVALID_PATH
      if check_order_validation:
        for k, v in kw.iteritems():
          if activity_tool.validateOrder(message, k, v):
            return INVALID_ORDER
    except ConflictError:
      raise
    except:
      LOG('CMFActivity', WARNING,
          'Validation of Object %s raised exception' % '/'.join(message.object_path),
          error=sys.exc_info())
      # Do not try to call methods on objects which cause errors
      return EXCEPTION
    return VALID

  def getDependentMessageList(self, activity_tool, message):
    message_list = []
    for k, v in message.activity_kw.iteritems():
      message_list += activity_tool.getDependentMessageList(message, k, v)
    return message_list

  def getExecutableMessageList(self, activity_tool, message, message_dict,
                               validation_text_dict, now_date=None):
    """Get messages which have no dependent message, and store them in the dictionary.

    If the passed message itself is executable, simply store only that message.
    Otherwise, try to find at least one message executable from dependent messages.

    This may result in no new message, if all dependent messages are already present
    in the dictionary, if all dependent messages are in different activities, or if
    the message has a circular dependency.

    The validation text dictionary is used only to cache the results of validations,
    in order to reduce the number of SQL queries.
    """
    if message.uid in message_dict:
      # Nothing to do. But detect a circular dependency.
      if message_dict[message.uid] is None:
        LOG('CMFActivity', ERROR,
            'message uid %r has a circular dependency' % (message.uid,))
      return

    cached_result = validation_text_dict.get(message.order_validation_text)
    if cached_result is None:
      message_list = self.getDependentMessageList(activity_tool, message)
      transaction.commit() # Release locks.
      if message_list:
        # The result is not empty, so this message is not executable.
        validation_text_dict[message.order_validation_text] = 0
        if now_date is None:
          now_date = DateTime()
        for activity, m in message_list:
          # Note that the messages may contain ones which are already assigned or not
          # executable yet.
          if activity is self and m.processing_node == -1 and m.date <= now_date:
            # Call recursively. Set None as a marker to detect a circular dependency.
            message_dict[message.uid] = None
            try:
              self.getExecutableMessageList(activity_tool, m, message_dict,
                                             validation_text_dict, now_date=now_date)
            finally:
              del message_dict[message.uid]
      else:
        validation_text_dict[message.order_validation_text] = 1
        message_dict[message.uid] = message
    elif cached_result:
      message_dict[message.uid] = message

  def hasActivity(self, activity_tool, object, processing_node=None, active_process=None, **kw):
    return 0

  def flush(self, activity_tool, object, **kw):    
    pass

  def loadMessage(self, s, **kw):
    m = cPickle.load(StringIO(s))
    m.__dict__.update(kw)
    return m

  def dumpMessage(self, m):
    return cPickle.dumps(m)

  def getOrderValidationText(self, message):
    # Return an identifier of validators related to ordering.
    order_validation_item_list = []
    key_list = message.activity_kw.keys()
    key_list.sort()
    for key in key_list:
      method_id = "_validate_%s" % key
      if getattr(self, method_id, None) is not None:
        order_validation_item_list.append((key, message.activity_kw[key]))
    if len(order_validation_item_list) == 0:
      # When no order validation argument is specified, skip the computation
      # of the checksum for speed. Here, 'none' is used, because this never be
      # identical to SHA1 hexdigest (which is always 40 characters), and 'none'
      # is true in Python. This is important, because dtml-if assumes that an empty
      # string is false, so we must use a non-empty string for this.
      return 'none'
    return sha1(repr(order_validation_item_list)).hexdigest()

  def getMessageList(self, activity_tool, processing_node=None,**kw):
    return []

  def countMessage(self, activity_tool,**kw):
    return 0

  def countMessageWithTag(self, activity_tool,value):
    return 0

  # Transaction Management
  def prepareQueueMessageList(self, activity_tool, message_list):
    # Called to prepare transaction commit for queued messages
    raise NotImplementedError

  # Registration Management
  def registerActivityBuffer(self, activity_buffer):
    pass

  def isMessageRegistered(self, activity_buffer, activity_tool, m):
    message_list = activity_buffer.getMessageList(self)
    return m in message_list

  def registerMessage(self, activity_buffer, activity_tool, m):
    message_list = activity_buffer.getMessageList(self)
    message_list.append(m)
    m.is_registered = 1

  def unregisterMessage(self, activity_buffer, activity_tool, m):
    m.is_registered = 0

  def getRegisteredMessageList(self, activity_buffer, activity_tool):
    message_list = activity_buffer.getMessageList(self)
    return [m for m in message_list if m.is_registered]

  # Required for tests (time shift)
  def timeShift(self, activity_tool, delay):
    """
      delay is provided in fractions of day
    """
    pass

  def getPriority(self, activity_tool):
    """
      Get priority from this queue.
      Lower number means higher priority value.
      Legal value range is [-128, 127].
      Values out of this range might work, but are non-standard.
    """
    return 128
