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

from AccessControl import ClassSecurityInfo

from Products.ERP5Type import Permissions, PropertySheet
from Products.ERP5.Document.DeliveryLine import DeliveryLine

class OrderLine(DeliveryLine):
    """
      A order line defines quantity and price
    """

    meta_type = 'ERP5 Order Line'
    portal_type = 'Order Line'

    # Declarative security
    security = ClassSecurityInfo()
    security.declareObjectProtected(Permissions.AccessContentsInformation)

    # Declarative properties
    property_sheets = ( PropertySheet.Base
                      , PropertySheet.XMLObject
                      , PropertySheet.CategoryCore
                      , PropertySheet.Amount
                      , PropertySheet.Task
                      , PropertySheet.DublinCore
                      , PropertySheet.Arrow
                      , PropertySheet.Movement
                      , PropertySheet.Price
                      , PropertySheet.VariationRange
                      , PropertySheet.ItemAggregation
                      )


    def applyToOrderLineRelatedMovement(self, portal_type='Simulation Movement', 
                                        method_id = 'expand'):
      """
        Warning: does not work if it was not catalogued immediately
      """
      # XXX This method seems to be not used at all.
      # Find related in simulation
      for my_simulation_movement in self.getOrderRelatedValueList(
          portal_type = 'Simulation Movement') or \
          self.getDeliveryRelatedValueList(portal_type = 'Simulation Movement'):
        # And apply
        getattr(my_simulation_movement, method_id)()
      for c in self.contentValues(filter={'portal_type': 'Delivery Cell'}):
        for my_simulation_movement in c.getOrderRelatedValueList(
            portal_type = 'Simulation Movement') or \
            c.getDeliveryRelatedValueList(portal_type = 'Simulation Movement'):
          # And apply
          getattr(my_simulation_movement, method_id)()

