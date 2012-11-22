##############################################################################
#
# Copyright (c) 2006 Nexedi SARL and Contributors. All Rights Reserved.
#          Sebastien Robin <seb@nexedi.com>
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
##############################################################################

import unittest

from Testing import ZopeTestCase
from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
from Products.ERP5Type.tests.utils import DummyMailHost
from AccessControl.SecurityManagement import newSecurityManager, \
        getSecurityManager, setSecurityManager
from AccessControl import Unauthorized
from DateTime import DateTime
from zLOG import LOG
from Products.ERP5Type.DateUtils import addToDate

class TestAlarm(ERP5TypeTestCase):
  """
  This is the list of test

  test setNextStartDate :
  - every hour
  - at 6, 10, 15, 21 every day
  - every day at 10
  - every 3 days at 14 and 15 and 17
  - every monday and friday, at 6 and 15
  - every 1st and 15th every month, at 12 and 14
  - every 1st day of every 2 month, at 6
  """

  # Different variables used for this test
  run_all_test = 1
  source_company_id = 'Nexedi'
  destination_company_id = 'Coramy'
  component_id = 'brick'
  sales_order_id = '1'
  quantity = 10
  base_price = 0.7832
  # year/month/day hour:minute:second
  date_format = '%i/%i/%i %i:%i:%d GMT+0100'

  def getTitle(self):
    return "Alarm"

  def getBusinessTemplateList(self):
    return ('erp5_base',)

  def afterSetUp(self):
    # add a dummy mailhost to capture alarm notifications
    if 'MailHost' in self.portal.objectIds():
      self.portal.manage_delObjects(['MailHost'])
      self.portal._setObject('MailHost', DummyMailHost('MailHost'))

    self.login()

  def beforeTearDown(self):
    del self.portal.MailHost._message_list[:]

  def newAlarm(self, **kw):
    """
    Create an empty alarm
    """
    a_tool = self.getAlarmTool()
    return a_tool.newContent(**kw)

  def login(self, quiet=0, run=run_all_test):
    uf = self.getPortal().acl_users
    uf._doAddUser('seb', '', ['Manager'], [])
    user = uf.getUserById('seb').__of__(uf)
    newSecurityManager(None, user)


  def test_01_HasEverything(self, quiet=0, run=run_all_test):
    # Test if portal_alarms was created
    if not run: return
    if not quiet:
      ZopeTestCase._print('\nTest Has Everything ')
      LOG('Testing... ',0,'testHasEverything')
    self.assertNotEquals(self.portal._getOb('portal_alarms', None), None)
    self.assertNotEquals(self.portal.portal_types.getTypeInfo('Alarm Tool'), None)

  def test_02_Initialization(self, quiet=0, run=run_all_test):
    """
    Test some basic things right after the creation
    """
    if not run: return
    if not quiet:
      message = 'Test Initialization'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)
    alarm = self.newAlarm()
    self.tic()
    now = DateTime()
    date = addToDate(now,day=1)
    alarm.setPeriodicityStartDate(date)
    self.assertEquals(alarm.getAlarmDate(), None)
    alarm.setEnabled(True)
    self.assertEquals(alarm.getAlarmDate(), date)
    alarm.setNextAlarmDate(current_date=now) # This should not do change the alarm date
    self.assertEquals(alarm.getAlarmDate(),date)

  def test_03_EveryHour(self, quiet=0, run=run_all_test):
    if not run: return
    if not quiet:
      message = 'Test Every Hour'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)
    alarm = self.newAlarm(enabled=True)
    now = DateTime()
    date = addToDate(now, day=2)
    alarm.setPeriodicityStartDate(date)
    alarm.setPeriodicityHourFrequency(1)
    self.tic()
    alarm.setNextAlarmDate(current_date=now)
    self.assertEquals(alarm.getAlarmDate(), date)
    LOG(message + ' now :',0,now)
    now = addToDate(now,day=2)
    LOG(message + ' now :',0,now)
    alarm.setNextAlarmDate(current_date=now)
    next_date = addToDate(date,hour=1)
    self.assertEquals(alarm.getAlarmDate(),next_date)
    now = addToDate(now,hour=1,minute=5)
    alarm.setNextAlarmDate(current_date=now)
    next_date = addToDate(next_date,hour=1)
    self.assertEquals(alarm.getAlarmDate(),next_date)
    # check if manual invoking does not break getAlarmDate() result.
    alarm.activeSense()
    self.assertEquals(alarm.getAlarmDate(),next_date)

  def test_04_Every3Hours(self, quiet=0, run=run_all_test):
    if not run: return
    if not quiet:
      message = 'Test Every 3 Hours'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)
    alarm = self.newAlarm(enabled=True)
    now = DateTime().toZone('UTC')
    hour_to_remove = now.hour() % 3
    now = addToDate(now,hour=-hour_to_remove)
    date = addToDate(now,day=2)
    alarm.setPeriodicityStartDate(date)
    alarm.setPeriodicityHourFrequency(3)
    self.tic()
    alarm.setNextAlarmDate(current_date=now)
    self.assertEquals(alarm.getAlarmDate(),date)
    LOG(message + ' now :',0,now)
    now = addToDate(now,day=2)
    LOG(message + ' now :',0,now)
    alarm.setNextAlarmDate(current_date=now)
    next_date = addToDate(date,hour=3)
    self.assertEquals(alarm.getAlarmDate(),next_date)
    now = addToDate(now,hour=3,minute=7,second=4)
    alarm.setNextAlarmDate(current_date=now)
    next_date = addToDate(next_date,hour=3)
    self.assertEquals(alarm.getAlarmDate(),next_date)

  def test_05_SomeHours(self, quiet=0, run=run_all_test):
    if not run: return
    if not quiet:
      message = 'Test Some Hours'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)

    right_first_date = DateTime(self.date_format  % (2006,10,6,15,00,00))
    now = DateTime(self.date_format               % (2006,10,6,15,00,00))
    right_second_date = DateTime(self.date_format % (2006,10,6,21,00,00))
    right_third_date = DateTime(self.date_format  % (2006,10,7,06,00,00))
    right_fourth_date = DateTime(self.date_format % (2006,10,7,10,00,00))
    alarm = self.newAlarm(enabled=True)
    hour_list = (6,10,15,21)
    alarm.setPeriodicityStartDate(now)
    alarm.setPeriodicityHourList(hour_list)
    self.tic()
    self.assertEquals(alarm.getAlarmDate(),right_first_date)
    alarm.setNextAlarmDate(current_date=right_first_date)
    self.assertEquals(alarm.getAlarmDate(),right_second_date)
    alarm.setNextAlarmDate(current_date=right_second_date)
    self.assertEquals(alarm.getAlarmDate(),right_third_date)
    alarm.setNextAlarmDate(current_date=right_third_date)
    self.assertEquals(alarm.getAlarmDate(),right_fourth_date)

  def test_06_EveryDayOnce(self, quiet=0, run=run_all_test):
    if not run: return
    if not quiet:
      message = 'Every Day Once'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)

    now = DateTime(self.date_format               % (2006,10,6,10,00,00))
    right_first_date = DateTime(self.date_format  % (2006,10,6,10,00,00))
    right_second_date = DateTime(self.date_format % (2006,10,7,10,00,00))
    right_third_date = DateTime(self.date_format  % (2006,10,8,10,00,00))
    alarm = self.newAlarm(enabled=True)
    alarm.setPeriodicityStartDate(now)
    alarm.setPeriodicityDayFrequency(1)
    alarm.setPeriodicityHourList((10,))
    self.tic()
    self.assertEquals(alarm.getAlarmDate(),right_first_date)
    alarm.setNextAlarmDate(current_date=right_first_date)
    self.assertEquals(alarm.getAlarmDate(),right_second_date)
    alarm.setNextAlarmDate(current_date=right_second_date)
    self.assertEquals(alarm.getAlarmDate(),right_third_date)

  def test_07_Every3DaysSomeHours(self, quiet=0, run=run_all_test):
    """- every 3 days at 14 and 15 and 17"""
    if not run: return
    if not quiet:
      message = 'Every 3 Days Some Hours'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)

    right_first_date = DateTime(self.date_format % (2006,10,6,14,00,00))
    right_second_date = DateTime(self.date_format  % (2006,10,6,15,00,00))
    right_third_date = DateTime(self.date_format  % (2006,10,6,17,00,00))
    right_fourth_date = DateTime(self.date_format  % (2006,10,9,14,00,00))
    alarm = self.newAlarm(enabled=True)
    alarm.setPeriodicityStartDate(right_first_date)
    alarm.setPeriodicityDayFrequency(3)
    alarm.setPeriodicityHourList((14,15,17))
    self.tic()
    self.assertEquals(alarm.getAlarmDate(),right_first_date)
    alarm.setNextAlarmDate(current_date=right_first_date)
    self.assertEquals(alarm.getAlarmDate(),right_second_date)
    alarm.setNextAlarmDate(current_date=right_second_date)
    self.assertEquals(alarm.getAlarmDate(),right_third_date)
    alarm.setNextAlarmDate(current_date=right_third_date)
    self.assertEquals(alarm.getAlarmDate(),right_fourth_date)

  def test_07a_Every4DaysSomeHours(self, quiet=0, run=run_all_test):
    """- every 4 days at 14 and 15 and 17"""
    if not run: return
    if not quiet:
      message = 'Every 4 Days Some Hours'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)

    right_first_date = DateTime(self.date_format % (2006,10,7,13,00,00))
    right_second_date = DateTime(self.date_format  % (2006,10,8,14,00,00))
    right_third_date = DateTime(self.date_format  % (2006,10,8,15,00,00))
    right_fourth_date = DateTime(self.date_format  % (2006,10,8,17,00,00))
    right_fifth_date = DateTime(self.date_format  % (2006,10,12,14,00,00))
    alarm = self.newAlarm(enabled=True)
    alarm.setPeriodicityStartDate(right_first_date)
    alarm.setPeriodicityDayFrequency(4)
    alarm.setPeriodicityHourList((14,15,17))
    self.tic()
    self.assertEquals(alarm.getAlarmDate(),right_first_date)
    alarm.setNextAlarmDate(current_date=right_first_date)
    self.assertEquals(alarm.getAlarmDate(),right_second_date)
    alarm.setNextAlarmDate(current_date=right_second_date)
    self.assertEquals(alarm.getAlarmDate(),right_third_date)
    alarm.setNextAlarmDate(current_date=right_third_date)
    self.assertEquals(alarm.getAlarmDate(),right_fourth_date)
    alarm.setNextAlarmDate(current_date=right_fourth_date)
    self.assertEquals(alarm.getAlarmDate(),right_fifth_date)

  def test_08_SomeWeekDaysSomeHours(self, quiet=0, run=run_all_test):
    """- every monday and friday, at 6 and 15"""
    if not run: return
    if not quiet:
      message = 'Some Week Days Some Hours'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)

    right_first_date = DateTime(self.date_format  % (2006,9,27,6,00,00))
    right_second_date = DateTime(self.date_format  % (2006,9,29,6,00,00))
    right_third_date = DateTime(self.date_format  % (2006,9,29,15,00,00))
    right_fourth_date = DateTime(self.date_format  % (2006,10,2,6,00,00))
    right_fifth_date = DateTime(self.date_format  % (2006,10,2,15,00,00))
    alarm = self.newAlarm(enabled=True)
    self.tic()
    alarm.setPeriodicityStartDate(right_first_date)
    alarm.setPeriodicityWeekDayList(('Monday','Friday'))
    alarm.setPeriodicityHourList((6,15))
    self.checkDate(alarm, right_first_date, right_second_date, right_third_date, right_fourth_date)

  def checkDate(self,alarm,*args):
    """
    the basic test
    """
    for date in args[:-1]:
      LOG('checkDate, checking date...:',0,date)
      self.assertEquals(alarm.getAlarmDate(),date)
      alarm.setNextAlarmDate(current_date=date)
    self.assertEquals(alarm.getAlarmDate(),args[-1])

  def test_09_SomeMonthDaysSomeHours(self, quiet=0, run=run_all_test):
    """- every 1st and 15th every month, at 12 and 14"""
    if not run: return
    if not quiet:
      message = 'Some Month Days Some Hours'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)

    right_first_date = DateTime(self.date_format  % (2006,10,01,12,00,00))
    right_second_date = DateTime(self.date_format  % (2006,10,01,14,00,00))
    right_third_date = DateTime(self.date_format  % (2006,10,15,12,00,00))
    right_fourth_date = DateTime(self.date_format  % (2006,10,15,14,00,00))
    alarm = self.newAlarm(enabled=True)
    alarm.setPeriodicityStartDate(right_first_date)
    alarm.setPeriodicityMonthDayList((1,15))
    alarm.setPeriodicityHourList((12,14))
    self.tic()
    self.checkDate(alarm, right_first_date, right_second_date, right_third_date, right_fourth_date)

  def test_10_OnceEvery2Month(self, quiet=0, run=run_all_test):
    """- every 1st day of every 2 month, at 6"""
    if not run: return
    if not quiet:
      message = 'Once Every 2 Month'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)

    right_first_date = DateTime(self.date_format  % (2006,10,01,6,00,00))
    right_second_date = DateTime(self.date_format  % (2006,12,01,6,00,00))
    right_third_date = DateTime(self.date_format  % (2007,2,01,6,00,00))
    alarm = self.newAlarm(enabled=True)
    alarm.setPeriodicityStartDate(right_first_date)
    alarm.setPeriodicityMonthDayList((1,))
    alarm.setPeriodicityMonthFrequency(2)
    alarm.setPeriodicityHourList((6,))
    self.tic()
    self.checkDate(alarm, right_first_date, right_second_date, right_third_date)

  def test_11_EveryDayOnceWeek41And42(self, quiet=0, run=run_all_test):
    if not run: return
    if not quiet:
      message = 'Every Day Once Week 41 And 43'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)

    right_first_date = DateTime(self.date_format  % (2006,10,1,6,00,00))
    right_second_date = DateTime(self.date_format  % (2006,10,9,6,00,00))
    right_third_date = DateTime(self.date_format  % (2006,10,10,6,00,00))
    right_fourth_date = DateTime(self.date_format  % (2006,10,11,6,00,00))
    alarm = self.newAlarm(enabled=True)
    alarm.setPeriodicityStartDate(right_first_date)
    alarm.setPeriodicityHourList((6,))
    alarm.setPeriodicityWeekList((41,43))
    self.tic()
    self.checkDate(alarm, right_first_date, right_second_date, right_third_date,right_fourth_date)

  def test_12_Every5Minutes(self, quiet=0, run=run_all_test):
    if not run: return
    if not quiet:
      message = 'Test Every 5 Minutes'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)
    alarm = self.newAlarm(enabled=True)
    now = DateTime()
    minute_to_remove = now.minute() % 5
    now = addToDate(now,minute=-minute_to_remove)
    date = addToDate(now,day=2)
    alarm.setPeriodicityStartDate(date)
    alarm.setPeriodicityMinuteFrequency(5)
    self.tic()
    alarm.setNextAlarmDate(current_date=now)
    self.assertEquals(alarm.getAlarmDate(),date)
    LOG(message + ' now :',0,now)
    now = addToDate(now,day=2)
    LOG(message + ' now :',0,now)
    alarm.setNextAlarmDate(current_date=now)
    next_date = addToDate(date,minute=5)
    self.assertEquals(alarm.getAlarmDate(),next_date)
    now = addToDate(now,minute=5,second=14)
    alarm.setNextAlarmDate(current_date=now)
    next_date = addToDate(next_date,minute=5)
    self.assertEquals(alarm.getAlarmDate(),next_date)

  def test_13_EveryMinute(self, quiet=0, run=run_all_test):
    if not run: return
    if not quiet:
      message = 'Test Every Minute'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)
    alarm = self.newAlarm(enabled=True)
    now = DateTime()
    date = addToDate(now,hour=2)
    alarm.setPeriodicityStartDate(now)
    alarm.setPeriodicityMinuteFrequency(1)
    self.tic()
    alarm.setNextAlarmDate(current_date=date)
    self.assertEquals(alarm.getAlarmDate(),date)

  def test_14_NewActiveProcess(self, quiet=0, run=run_all_test):
    if not run: return
    if not quiet:
      message = 'Test New Active Process'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)
    alarm = self.newAlarm(enabled=True)
    active_process = alarm.newActiveProcess()
    self.assertEquals('Active Process', active_process.getPortalType())
    self.assertEquals(alarm, active_process.getCausalityValue())
    self.tic()
    self.assertEquals(active_process, alarm.getLastActiveProcess())

  def test_15_FailedAlarmsDoNotBlockFutureAlarms(self, quiet=0, run=run_all_test):
    if not run: return
    if not quiet:
      message = 'Test Failed Alarms Do Not Block Future Alarms'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)
    try:
      sense_method_id = 'Alarm_testSenseMethod'
      skin_folder_id = 'custom'
      skin_folder = self.getPortal().portal_skins[skin_folder_id]
      skin_folder.manage_addProduct['PythonScripts'].manage_addPythonScript(id=sense_method_id)
      # Make the sense method fail
      skin_folder[sense_method_id].ZPythonScript_edit('*args,**kw', 'raise Exception')
      del skin_folder
      alarm = self.newAlarm(enabled=True)
      self.tic()
      now = DateTime()
      alarm.setActiveSenseMethodId(sense_method_id)
      self.assertEquals(alarm.isActive(), 0)
      alarm.activeSense()
      self.commit()
      try:
        self.tic()
      except RuntimeError:
        pass
      else:
        raise Exception, 'Tic did not raise though activity was supposed to fail'
      # Check that the alarm is not considered active, although there is a remaining activity.
      self.assertEquals(alarm.hasActivity(), 1)
      self.assertEquals(alarm.isActive(), 0)
      self.assertEquals(alarm.getLastActiveProcess(), None)
      # Make the sense method succeed and leave a trace
      self.getPortal().portal_skins[skin_folder_id][sense_method_id].ZPythonScript_edit('*args,**kw', 'context.newActiveProcess()')
      alarm.activeSense()
      self.commit()
      # Note: this call to tic will fail, because the previous message is still there
      # This behaviour is logical if we consider that we want to keep errors
      # in order to know that an error occured.
      try:
        self.tic()
      except RuntimeError:
        pass
      else:
        raise Exception, 'Tic did not raise though activity was supposed to fail'
      # Chen that the second alarm execution did happen
      self.assertNotEquals(alarm.getLastActiveProcess(), None)
    finally:
      self.portal.portal_activities.manageClearActivities(keep=0)

  def test_16_uncatalog(self, quiet=0, run=run_all_test):
    """
    Check that deleting an alarm uncatalogs it.
    """
    if not run: return
    if not quiet:
      message = 'Test Uncatalog'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ', 0, message)
    alarm = self.newAlarm(enabled=True)
    self.tic()

    now = DateTime()
    date = addToDate(now, day=1)
    alarm.setPeriodicityStartDate(date)
    self.tic()
    self.assertEquals(alarm.getAlarmDate(), date)

    # This should not do change the alarm date
    alarm.setNextAlarmDate(current_date=now)
    self.tic()
    self.assertEquals(alarm.getAlarmDate(), date)

    # Delete the alarm
    a_tool = self.getAlarmTool()
    alarm_uid = alarm.getUid()
    a_tool.manage_delObjects(uids=[alarm_uid])
    self.tic()
    # Check that related entry was removed
    sql_connection = self.getSQLConnection()
    sql = 'select * from alarm where uid=%s' % alarm_uid
    result = sql_connection.manage_test(sql)
    self.assertEquals(0, len(result))

  def test_17_tic(self, quiet=0, run=run_all_test):
    """
    Make sure that the tic method on alarm is working
    """
    if not run: return
    if not quiet:
      message = 'Test AlarmTool Tic'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ', 0, message)
    alarm = self.newAlarm()
    alarm.setEnabled(True)
    self.tic()

    sense_method_id = 'Alarm_testSenseMethodForTic'
    skin_folder_id = 'custom'
    skin_folder = self.getPortal().portal_skins[skin_folder_id]
    skin_folder.manage_addProduct['PythonScripts']\
        .manage_addPythonScript(id=sense_method_id)
    # Make the sense method fail
    skin_folder[sense_method_id].ZPythonScript_edit('*args,**kw', 
          'context.setDescription("a")')
    del skin_folder
    alarm.setActiveSenseMethodId(sense_method_id)
    self.tic()
    alarm_tool = self.getPortal().portal_alarms
    # Nothing should happens yet
    alarm_tool.tic()
    self.tic()
    self.assertTrue(alarm.getDescription() in (None, ''))
    now = DateTime()
    date = addToDate(now, day=-1)
    alarm.setPeriodicityStartDate(date)
    alarm.setPeriodicityMinuteFrequency(1)
    self.tic()
    alarm_tool.tic()
    self.tic()
    self.assertEquals(alarm.getDescription(), 'a')

  def test_18_alarm_activities_execution_order(self, quiet=0, run=run_all_test):
    """
    Make sure active process created by an alarm get the right tag
    """
    if not run: return
    if not quiet:
      message = 'Test Activities execution order'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ', 0, message)

    alarm = self.newAlarm()
    # Create script that generate active process
    sense_method_id = 'Alarm_createActiveProcessSenseMethod'
    skin_folder_id = 'custom'
    skin_folder = self.getPortal().portal_skins[skin_folder_id]
    skin_folder.manage_addProduct['PythonScripts']\
        .manage_addPythonScript(id=sense_method_id)
    skin_folder[sense_method_id].ZPythonScript_edit('*args,**kw', 
          'context.newActiveProcess()')
    # update alarm properties
    alarm.edit(alarm_notification_mode="always",
               active_sense_method_id=sense_method_id,
               enabled=True)
    self.tic()
    alarm.activeSense()
    self.commit()
    messages_list = self.getActivityTool().getMessageList()
    self.assertEquals(2, len(messages_list))
    expected_tag = alarm.getRelativeUrl() + '_0'
    # check tags after activeSense
    for m in messages_list:
      if m.method_id == 'notify':
        self.assertEqual(expected_tag, m.activity_kw.get('after_tag'))
      elif m.method_id == sense_method_id:
        self.assertEqual(expected_tag, m.activity_kw.get('tag'))
      else:
        self.fail(m.method_id)
    # execute alarm sense script and check tags
    self.getActivityTool().manageInvoke(alarm.getPhysicalPath(),sense_method_id)
    self.commit()
    messages_list = self.getActivityTool().getMessageList()
    for m in messages_list:
      if m.method_id == 'notify':
        self.assertEqual(expected_tag, m.activity_kw.get('after_tag'))
      elif m.method_id == 'immediateReindexObject':
        self.assertEqual(expected_tag, m.activity_kw.get('tag'))
      else:
        self.fail(m.method_id)
    self.tic()

  def test_19_ManualInvocation(self, quiet=0, run=run_all_test):
    """
    test if an alarm can be invoked directly by the user securely,
    and if the results are identical when allowed.
    """
    if not run: return
    if not quiet:
      message = 'Test manual invocation'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ', 0, message)

    alarm = self.newAlarm()
    # Create script that generate active process
    sense_method_id = 'Alarm_setBogusLocalProperty'
    skin_folder_id = 'custom'
    skin_folder = self.portal.portal_skins[skin_folder_id]
    skin_folder.manage_addProduct['PythonScripts']\
        .manage_addPythonScript(id=sense_method_id)
    skin_folder[sense_method_id].ZPythonScript_edit('*args,**kw', 
          'context.setProperty("bogus", str(context.showPermissions()))')

    # update alarm properties
    alarm.edit(active_sense_method_id=sense_method_id,
               enabled=False)
    self.tic()

    # Make a normal user.
    uf = self.getPortal().acl_users
    uf._doAddUser('normal', '', ['Member', 'Auditor'], [])
    user = uf.getUserById('normal').__of__(uf)
    
    # Check the pre-conditions.
    self.assertEquals(alarm.getProperty('bogus', None), None)
    self.assertEquals(alarm.getEnabled(), False)
    sm = getSecurityManager()
    newSecurityManager(None, user)

    # Non-managers must not be able to invoke a disabled alarm.
    self.assertRaises(Unauthorized, alarm.activeSense)
    self.assertRaises(Unauthorized, alarm.activeSense, fixit=1)

    # Non-managers must not be able to invoke the automatic fixation.
    setSecurityManager(sm)
    alarm.setEnabled(True)
    self.assertEquals(alarm.getEnabled(), True)
    newSecurityManager(None, user)
    self.assertRaises(Unauthorized, alarm.activeSense, fixit=1)

    # Now, check that everybody can invoke an enabled alarm manually.
    setSecurityManager(sm)
    correct_answer = str(alarm.showPermissions())
    self.assertNotEquals(correct_answer, None)

    alarm.activeSense()
    self.tic()
    self.assertEquals(alarm.getProperty('bogus', None), correct_answer)
    alarm.setProperty('bogus', None)
    self.assertEquals(alarm.getProperty('bogus', None), None)

    newSecurityManager(None, user)
    alarm.activeSense()
    self.tic()
    self.assertEquals(alarm.getProperty('bogus', None), correct_answer)
    setSecurityManager(sm)
    alarm.setProperty('bogus', None)

    # Check that Manager can invoke an alarm freely.
    alarm.activeSense(fixit=1)
    self.tic()
    self.assertEquals(alarm.getProperty('bogus', None), correct_answer)
    alarm.setProperty('bogus', None)
    self.assertEquals(alarm.getProperty('bogus', None), None)

    alarm.setEnabled(False)
    self.assertEquals(alarm.getEnabled(), False)

    alarm.activeSense()
    self.tic()
    self.assertEquals(alarm.getProperty('bogus', None), correct_answer)
    alarm.setProperty('bogus', None)
    self.assertEquals(alarm.getProperty('bogus', None), None)

    alarm.activeSense(fixit=1)
    self.tic()
    self.assertEquals(alarm.getProperty('bogus', None), correct_answer)
    alarm.setProperty('bogus', None)
    self.assertEquals(alarm.getProperty('bogus', None), None)

  def test_20_UndefinedPeriodicityStartDate(self, quiet=0, run=run_all_test):
    """
    Test that getAlarmDate does not crash when PeriodicityStartDate is not set.
    """
    if not run: return
    if not quiet:
      message = 'Test undefined PeriodicityStartDate'
      ZopeTestCase._print('\n%s ' % message)
      LOG('Testing... ',0,message)
    alarm = self.newAlarm(enabled=True)
    # Test sanity check.
    self.assertEqual(alarm.getPeriodicityStartDate(), None)
    # Actual test.
    self.assertEquals(alarm.getAlarmDate(), None)

  def test_21_AlarmCatalogPresence(self):
    """Check that alarm date is properly stored in catalog upon first reindexation"""
    date = DateTime().earliestTime()
    alarm = self.newAlarm(enabled=True, periodicity_start_date=date)
    self.tic()
    self.assertEquals(alarm.getAlarmDate(), date)
    alarm_list = alarm.Alarm_zGetAlarmDate(uid=alarm.getUid())
    self.assertEqual(1, len(alarm_list))
    catalog_alarm_date = alarm_list[0].alarm_date
    self.assertEqual(date.toZone('UTC'), catalog_alarm_date)

  def test_21a_AlarmCatalogPresenceDoubleReindex(self):
    """Check that alarm date is properly stored in catalog"""
    date = DateTime().earliestTime()
    alarm = self.newAlarm(enabled=True, periodicity_start_date=date)
    self.tic()
    alarm.recursiveReindexObject()
    self.tic()
    self.assertEquals(alarm.getAlarmDate(), date)
    alarm_list = alarm.Alarm_zGetAlarmDate(uid=alarm.getUid())
    self.assertEqual(1, len(alarm_list))
    catalog_alarm_date = alarm_list[0].alarm_date
    self.assertEqual(date.toZone('UTC'), catalog_alarm_date)

  def test_21b_AlarmCatalogPresenceWithInitialEmptyStartDate(self):
    """Check that alarm date is properly stored in catalog if
       initially the periodicity start date was not there and
       then set later"""
    date = DateTime().earliestTime()
    alarm = self.newAlarm(enabled=True, periodicity_start_date=None)
    self.tic()
    alarm_list = alarm.Alarm_zGetAlarmDate(uid=alarm.getUid())
    self.assertEqual(None, alarm_list[0].alarm_date)
    alarm.edit(periodicity_start_date=date)
    self.tic()
    alarm_list = alarm.Alarm_zGetAlarmDate(uid=alarm.getUid())
    self.assertEqual(date.toZone('UTC'), alarm_list[0].alarm_date)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestAlarm))
  return suite

