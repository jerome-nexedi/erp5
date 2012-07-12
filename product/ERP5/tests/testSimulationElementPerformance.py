##############################################################################
#
# Copyright (c) 2010 Nexedi SA and Contributors. All Rights Reserved.
#          Yoshinori Okuji <yo@nexedi.com>
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

"""Performance tests for simulation.

The purpose of these tests is to measure the performance of the following
basic operations in simulation:

  - the creation of new Applied Rules and the expansion of simulation
  - the expansion of simulation from existing Applied Rules
  - the expansion of simulation which results in convergence
  - the expansion of simulation which results in divergence
  - the adoption of previsions by a Target Solver
  - the acceptance of decisions by a Target Solver
  - the creation of new Applied Rules from partially simulated documents
  - the creation of new Deliveries by Delivery Builders
  - the addition of new Movements into existing Deliveries by Delivery Builders

For the testing environment, these document types are used for Deliveries:

  - Sale Order
  - Sale Packing List
  - Sale Invoice

Since Sale Invoices consist of Movements generated from Sale Packing Lists,
and Movements generated by Trade Model Lines, the simulation trees consist
of at most 4 levels in this order:

  - Order Simulation Rule
  - Packing List Simulation Rule
  - Invoice Simulation Rule
  - Trade Model Simulation Rule

In order to simulate various patterns of building, the following rules
are defined:

  - Sale Order is completed at "ordered"
  - Sale Packing List is completed at "stopped"
  - Sale Packing Lists are grouped by destination and by Sale Order
  - Sale Invoices are not

So, the relationship between Sale Order and Sale Packing List is 1:N,
and that between Sale Packing List and Sale Invoice is M:N.

"""

import unittest
from time import time
import gc
import subprocess
import hotshot

from DateTime import DateTime
from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
from zLOG import LOG
from Products.ERP5Type.tests.utils import LogInterceptor
from Products.ERP5Type.tests.Sequence import SequenceList

# Define variable to chek if performance are good or not
# XXX These variable are specific to the testing environment
#     (pystone results: min: < 75757.6 - mean: ~ 77174.4 - max: > 78125)
# Historical values are here to remember original values on this
# specific testing environment. We must always try to stay below max
# historical values.

EXPECTED_MIN_MAX_TIME = {
  'Creation Of New Applied Rules': (34.8, 36.8),

  'Expansion of Existing Applied Rules': (16.9, 19.5),

  'Creation of New Sale Packing Lists': (37.4, 38.9),

  'Expansion of Converged Changes': (22.0, 24.8),

  'Expansion of Diverged Changes': (24.6, 26.9),

  'Adoption of Previsions': (17.9, 18.7),

  'Acceptance of Decisions': (14.5, 15.2),

  'Creation of New Applied Rules from Partially Simulated Deliveries':
    (51.2, 52.8),

  'Creation Of New Sale Invoices': (90.0, 98.5),

  'Addition of New Invoices Lines': (145.1, 157.6),
}

class TestSimulationPerformance(ERP5TypeTestCase, LogInterceptor):

    def getTitle(self):
      return "Simulation Performance"

    def getBusinessTemplateList(self):
      """
        Return the list of business templates.
      """
      return ('erp5_core_proxy_field_legacy', 'erp5_base',
              'erp5_pdm', 'erp5_simulation', 'erp5_trade',
              'erp5_accounting', 'erp5_invoicing', 'erp5_simplified_invoicing',
              'erp5_simulation_performance_test')

    def afterSetUp(self):
      """
        Executed before each test_*.
      """
      self.login()
      portal = self.getPortal()

      # Validate some documents.
      for rule in portal.portal_rules.objectValues():
        if rule.getValidationState() != 'validated' \
                and rule.getId().startswith('test_'):
          rule.validate()

      for trade_condition in portal.sale_trade_condition_module.objectValues():
        if trade_condition.getValidationState() != 'validated':
          trade_condition.validate()

      business_process = portal.business_process_module.test_bp
      if business_process.getValidationState() != 'validated':
        business_process.validate()

      subprocess.call('sync')
      #self.prof = hotshot.Profile('hoge.prof')

    def beforeTearDown(self):
      #self.prof.close()
      self.abort()
      portal = self.getPortal()
      for module_id in ('sale_order_module', 'sale_packing_list_module',
                        'accounting_module', 'portal_simulation'):
        module = portal[module_id]
        module.manage_delObjects(list(module.objectIds()))
      self.tic()

    def _getMinMaxTime(self, target):
      return EXPECTED_MIN_MAX_TIME[target]

    def _checkSimulation(self,
            number_of_sale_orders=None,
            number_of_sale_order_lines=None,
            number_of_additional_sale_packing_list_lines=None,
            measurable=True):
      sequence_string = """
              Initialize
              Tic
              UseClientAsDestinationDecision
              UseClientAsDestinationAdministration
              UseResourceAsCommodityProduct
              CreateSaleOrders
              Tic
              PlanSaleOrders
              MeasureCreationOfNewAppliedRules
              Tic
              CheckSaleOrderSimulation
              UseRecipient1AsDestinationDecision
              ModifySaleOrders
              MeasureExpansionOfExistingAppliedRules
              Tic
              CheckSaleOrderSimulation
              OrderSaleOrders
              MeasureCreationOfNewSalePackingLists
              Tic
              CheckSaleOrderSimulation
              CheckBuiltSalePackingLists
              UseRecipient2AsDestinationDecision
              ModifySaleOrders
              MeasureExpansionOfConvergedChanges
              Tic
              CheckSaleOrderSimulation
              CheckConvergedSalePackingLists
              UseRecipient1AsDestinationAdministration
              ModifySaleOrders
              MeasureExpansionOfDivergedChanges
              Tic
              CheckSaleOrderSimulation
              CheckDivergedSalePackingLists
              SetSolverTargetToDestinationAdministration
              AdoptPrevisionToSalePackingLists
              MeasureAdoptionOfPrevisions
              Tic
              CheckConvergedSalePackingLists
              UseRecipient2AsDestinationAdministration
              ModifySaleOrders
              Tic
              CheckSaleOrderSimulation
              CheckDivergedSalePackingLists
              SetSolverTargetToDestinationAdministration
              AcceptDecisionOfSalePackingLists
              MeasureAcceptanceOfDecisions
              Tic
              UseRecipient1AsDestinationAdministration
              CheckConvergedSalePackingLists
              ConfirmSaleOrders
              Tic
              UseResourceAsCommodityProduct
              AddNewSalePackingLinesIntoSalePackingLists
              MeasureCreationOfNewAppliedRulesFromPartiallySimulatedDeliveries
              Tic
              CheckSalePackingListSimulation
              StopSalePackingLists
              MeasureCreationOfNewSaleInvoices
              Tic
              CheckBuiltSaleInvoices
              UseResourceAsLuxuryProduct
              AddNewSalePackingLinesIntoSalePackingLists
              DeliverSalePackingLists
              MeasureAdditionOfNewInvoiceLinesIntoSaleInvoices
              Tic
              CheckAddedSaleInvoices
              TestResult
              """

      sequence = SequenceList()

      self.assertTrue(isinstance(number_of_sale_orders, int))
      self.assertTrue(number_of_sale_orders > 0)

      self.assertTrue(isinstance(number_of_sale_order_lines, int))
      self.assertTrue(number_of_sale_order_lines > 0)

      self.assertTrue(isinstance(number_of_additional_sale_packing_list_lines,
                                 int))
      self.assertTrue(number_of_additional_sale_packing_list_lines > 0)

      self.assertTrue(measurable in (True, False))

      self._init_dict = dict(number_of_sale_orders=number_of_sale_orders,
              number_of_sale_order_lines=number_of_sale_order_lines,
              number_of_additional_sale_packing_list_lines=number_of_additional_sale_packing_list_lines,
              measurable=measurable)

      sequence.addSequenceString(sequence_string)
      sequence.play(self)

    def stepInitialize(self, sequence=None, sequence_list=None, **kw):
      sequence.edit(**self._init_dict)

    def stepTic(self, sequence, sequence_list=None, **kw):
      target = sequence.get('measure_target')
      measurable = target and sequence.get('measurable')

      # Reduce noise effect.
      subprocess.call('sync')
      gc.collect()

      if measurable:
        before_time = time()

      #self.prof.start()
      self.tic()
      #self.prof.stop()

      if measurable:
        after_time = time()
        amount_of_time = after_time - before_time
        min_time, max_time = self._getMinMaxTime(target)
        print "\n%s took %.4f (%.4f < %.4f < %.4f)" \
                % (target, amount_of_time, min_time, amount_of_time, max_time)
        # Reset the target to make sure that the same target is not
        # measured again.
        sequence.edit(measure_target=None)
        # Set the result.
        result = sequence.setdefault('result', [])
        result.append((target, min_time, amount_of_time, max_time))

    def stepMeasureCreationOfNewAppliedRules(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('measure_target', 'Creation Of New Applied Rules')

    def stepMeasureExpansionOfExistingAppliedRules(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('measure_target', 'Expansion of Existing Applied Rules')

    def stepMeasureCreationOfNewSalePackingLists(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('measure_target', 'Creation of New Sale Packing Lists')

    def stepMeasureExpansionOfConvergedChanges(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('measure_target', 'Expansion of Converged Changes')

    def stepMeasureExpansionOfDivergedChanges(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('measure_target', 'Expansion of Diverged Changes')

    def stepMeasureAdoptionOfPrevisions(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('measure_target', 'Adoption of Previsions')

    def stepMeasureAcceptanceOfDecisions(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('measure_target', 'Acceptance of Decisions')

    def stepMeasureCreationOfNewAppliedRulesFromPartiallySimulatedDeliveries(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('measure_target',
              'Creation of New Applied Rules from Partially Simulated Deliveries')

    def stepMeasureCreationOfNewSaleInvoices(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('measure_target', 'Creation Of New Sale Invoices')

    def stepMeasureAdditionOfNewInvoiceLinesIntoSaleInvoices(self,
            sequence=None, sequence_list=None, **kw):
      sequence.set('measure_target', 'Addition of New Invoices Lines')

    def stepUseClientAsDestinationDecision(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('destination_decision', 'organisation_module/client')

    def stepUseRecipient1AsDestinationDecision(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('destination_decision', 'organisation_module/recipient1')

    def stepUseRecipient2AsDestinationDecision(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('destination_decision', 'organisation_module/recipient2')

    def stepUseClientAsDestinationAdministration(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('destination_administration', 'organisation_module/client')

    def stepUseRecipient1AsDestinationAdministration(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('destination_administration',
              'organisation_module/recipient1')

    def stepUseRecipient2AsDestinationAdministration(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('destination_administration',
              'organisation_module/recipient2')

    def stepUseResourceAsCommodityProduct(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('resource', 'product_module/commodity')

    def stepUseResourceAsLuxuryProduct(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('resource', 'product_module/luxury')

    def stepCreateSaleOrders(self, sequence=None, sequence_list=None, **kw):
      portal = self.getPortal()
      module = portal.sale_order_module
      base_date = DateTime('2010-08-08')
      number_of_sale_orders = sequence.get('number_of_sale_orders')
      number_of_sale_order_lines = sequence.get('number_of_sale_order_lines')
      destination_decision = sequence.get('destination_decision')
      destination_administration = sequence.get('destination_administration')
      resource = sequence.get('resource')
      for i in xrange(number_of_sale_orders):
        start_date = base_date + i
        stop_date = base_date + i + 1
        order = module.newContent(
                portal_type='Sale Order',
                specialise='sale_trade_condition_module/test_stc',
                destination_decision=destination_decision,
                destination_administration=destination_administration,
                start_date=start_date,
                stop_date=stop_date)
        # Set the rest through the trade condition.
        order.SaleOrder_applySaleTradeCondition()
        for j in xrange(number_of_sale_order_lines):
          order.newContent(portal_type='Sale Order Line',
                  resource=resource, quantity=1.0)

    def stepModifySaleOrders(self, sequence=None, sequence_list=None, **kw):
      portal = self.getPortal()
      module = portal.sale_order_module
      destination_decision = sequence.get('destination_decision')
      destination_administration = sequence.get('destination_administration')
      for order in module.contentValues(portal_type='Sale Order'):
        order.edit(destination_decision=destination_decision,
                destination_administration=destination_administration)
        self.assertEquals(order.getDestinationDecision(), destination_decision)
        self.assertEquals(order.getDestinationAdministration(),
                destination_administration)

    def stepPlanSaleOrders(self, sequence=None, sequence_list=None, **kw):
      portal = self.getPortal()
      module = portal.sale_order_module
      for order in module.contentValues(portal_type='Sale Order'):
        self.assertEquals(order.getSimulationState(), 'draft')
        order.plan()
        self.assertEquals(order.getSimulationState(), 'planned')

    def stepOrderSaleOrders(self, sequence=None, sequence_list=None, **kw):
      portal = self.getPortal()
      module = portal.sale_order_module
      for order in module.contentValues(portal_type='Sale Order'):
        self.assertEquals(order.getSimulationState(), 'planned')
        order.order()
        self.assertEquals(order.getSimulationState(), 'ordered')

    def stepConfirmSaleOrders(self, sequence=None, sequence_list=None, **kw):
      portal = self.getPortal()
      module = portal.sale_order_module
      for order in module.contentValues(portal_type='Sale Order'):
        self.assertEquals(order.getSimulationState(), 'ordered')
        order.confirm()
        self.assertEquals(order.getSimulationState(), 'confirmed')

    def stepCheckSaleOrderSimulation(self, sequence=None, sequence_list=None,
            **kw):
      portal = self.getPortal()
      module = portal.sale_order_module
      number_of_sale_orders = sequence.get('number_of_sale_orders')
      number_of_sale_order_lines = sequence.get('number_of_sale_order_lines')
      destination_decision = sequence.get('destination_decision')
      destination_administration = sequence.get('destination_administration')
      resource = sequence.get('resource')
      self.assertEquals(module.objectCount(), number_of_sale_orders)
      for order in module.contentValues(portal_type='Sale Order'):
        causality_list = order.getCausalityRelatedValueList(portal_type='Applied Rule')
        self.assertEquals(len(causality_list), 1)
        applied_rule = causality_list[0]
        self.assertEquals(applied_rule.getPortalType(), 'Applied Rule')
        rule = applied_rule.getSpecialiseValue()
        self.assertNotEquals(rule, None)
        self.assertEquals(rule.getReference(),
                'test_order_root_simulation_rule')
        self.assertEquals(applied_rule.objectCount(),
                number_of_sale_order_lines)
        for simulation_movement in applied_rule.objectValues():
          self.assertEquals(simulation_movement.getPortalType(),
                  'Simulation Movement')
          self.assertEquals(simulation_movement.getQuantity(), 1.0)
          self.assertEquals(simulation_movement.getResource(), resource)
          self.assertEquals(set(simulation_movement.getCausalityList()), set((
                  'business_process_module/test_bp/order_path',
                  'business_process_module/test_bp/order')))
          self.assertEquals(simulation_movement.getDestinationDecision(),
                  destination_decision)
          self.assertEquals(simulation_movement.getDestinationAdministration(),
                  destination_administration)

    def stepCheckBuiltSalePackingLists(self, sequence=None, sequence_list=None,
            **kw):
      portal = self.getPortal()
      module = portal.sale_packing_list_module
      number_of_sale_orders = sequence.get('number_of_sale_orders')
      number_of_sale_order_lines = sequence.get('number_of_sale_order_lines')
      destination_decision = sequence.get('destination_decision')
      destination_administration = sequence.get('destination_administration')
      resource = sequence.get('resource')
      self.assertEquals(module.objectCount(), number_of_sale_orders)
      for packing_list in module.contentValues():
        self.assertEquals(packing_list.getSimulationState(), 'confirmed')
        self.assertEquals(packing_list.getCausalityState(), 'solved')
        self.assertEquals(packing_list.getDestinationDecision(),
                destination_decision)
        self.assertEquals(packing_list.getDestinationAdministration(),
                destination_administration)
        self.assertEquals(packing_list.objectCount(), 1)
        for line in packing_list.objectValues():
          self.assertEquals(line.getResource(), resource)
          self.assertAlmostEquals(line.getQuantity(),
                  1.0 * number_of_sale_order_lines)
          simulation_movement_list = line.getDeliveryRelatedValueList()
          self.assertEquals(len(simulation_movement_list),
                  number_of_sale_order_lines)
          for simulation_movement in simulation_movement_list:
            self.assertEquals(simulation_movement.getPortalType(),
                    'Simulation Movement')
            self.assertEquals(set(simulation_movement.getCausalityList()), set((
                    'business_process_module/test_bp/deliver_path',
                    'business_process_module/test_bp/deliver')))

    def stepCheckBuiltSaleInvoices(self, sequence=None, sequence_list=None,
            **kw):
      portal = self.getPortal()
      module = portal.accounting_module
      self.assertEquals(module.objectCount(), 1)
      number_of_sale_orders = sequence.get('number_of_sale_orders')
      number_of_sale_order_lines = sequence.get('number_of_sale_order_lines')
      number_of_additional_sale_packing_list_lines \
              = sequence.get('number_of_additional_sale_packing_list_lines')
      for invoice in module.contentValues():
        self.assertEquals(invoice.getSimulationState(), 'confirmed')
        self.assertEquals(invoice.getCausalityState(), 'solved')
        self.assertEquals(invoice.objectCount(), 2)
        invoice_line_list = invoice.objectValues(sort_on='resource')

        commodity_invoice_line = invoice_line_list[0]
        self.assertEquals(commodity_invoice_line.getResource(),
                'product_module/commodity')
        self.assertAlmostEquals(commodity_invoice_line.getQuantity(),
                1.0 * (number_of_sale_order_lines \
                        + number_of_additional_sale_packing_list_lines) \
                        * number_of_sale_orders)
        simulation_movement_list \
                = commodity_invoice_line.getDeliveryRelatedValueList()
        self.assertEquals(len(simulation_movement_list),
                (number_of_sale_order_lines \
                        + number_of_additional_sale_packing_list_lines) \
                        * number_of_sale_orders)
        for simulation_movement in simulation_movement_list:
          self.assertEquals(simulation_movement.getPortalType(),
                  'Simulation Movement')
          self.assertEquals(set(simulation_movement.getCausalityList()), set((
                  'business_process_module/test_bp/invoice_path',
                  'business_process_module/test_bp/invoice')))

        tax_invoice_line = invoice_line_list[1]
        self.assertEquals(tax_invoice_line.getResource(),
                'service_module/vat_low')
        self.assertAlmostEquals(tax_invoice_line.getQuantity(),
                commodity_invoice_line.getPrice() \
                        * (number_of_sale_order_lines \
                           + number_of_additional_sale_packing_list_lines) \
                        * number_of_sale_orders)
        simulation_movement_list \
                = tax_invoice_line.getDeliveryRelatedValueList()
        self.assertEquals(len(simulation_movement_list),
                (number_of_sale_order_lines \
                        + number_of_additional_sale_packing_list_lines) \
                        * number_of_sale_orders)
        for simulation_movement in simulation_movement_list:
          self.assertEquals(simulation_movement.getPortalType(),
                  'Simulation Movement')
          self.assertEquals(set(simulation_movement.getCausalityList()), set((
                  'business_process_module/test_bp/invoice_path',
                  'business_process_module/test_bp/invoice',
                  'sale_trade_condition_module/test_stc/vat_low')))

    def stepCheckAddedSaleInvoices(self, sequence=None, sequence_list=None,
            **kw):
      portal = self.getPortal()
      module = portal.accounting_module
      self.assertEquals(module.objectCount(), 1)
      number_of_sale_orders = sequence.get('number_of_sale_orders')
      number_of_sale_order_lines = sequence.get('number_of_sale_order_lines')
      number_of_additional_sale_packing_list_lines \
              = sequence.get('number_of_additional_sale_packing_list_lines')
      for invoice in module.contentValues():
        self.assertEquals(invoice.getSimulationState(), 'confirmed')
        self.assertEquals(invoice.getCausalityState(), 'solved')
        self.assertEquals(invoice.objectCount(), 4)
        invoice_line_list = invoice.objectValues(sort_on='resource')

        commodity_invoice_line = invoice_line_list[0]
        self.assertEquals(commodity_invoice_line.getResource(),
                'product_module/commodity')
        self.assertAlmostEquals(commodity_invoice_line.getQuantity(),
                1.0 * (number_of_sale_order_lines \
                        + number_of_additional_sale_packing_list_lines) \
                        * number_of_sale_orders)
        simulation_movement_list \
                = commodity_invoice_line.getDeliveryRelatedValueList()
        self.assertEquals(len(simulation_movement_list),
                (number_of_sale_order_lines \
                        + number_of_additional_sale_packing_list_lines) \
                        * number_of_sale_orders)
        for simulation_movement in simulation_movement_list:
          self.assertEquals(simulation_movement.getPortalType(),
                  'Simulation Movement')
          self.assertEquals(set(simulation_movement.getCausalityList()), set((
                  'business_process_module/test_bp/invoice_path',
                  'business_process_module/test_bp/invoice')))

        luxury_invoice_line = invoice_line_list[1]
        self.assertEquals(luxury_invoice_line.getResource(),
                'product_module/luxury')
        self.assertAlmostEquals(luxury_invoice_line.getQuantity(),
                1.0 * number_of_additional_sale_packing_list_lines \
                        * number_of_sale_orders)
        simulation_movement_list \
                = luxury_invoice_line.getDeliveryRelatedValueList()
        self.assertEquals(len(simulation_movement_list),
                number_of_additional_sale_packing_list_lines \
                        * number_of_sale_orders)
        for simulation_movement in simulation_movement_list:
          self.assertEquals(simulation_movement.getPortalType(),
                  'Simulation Movement')
          self.assertEquals(set(simulation_movement.getCausalityList()), set((
                  'business_process_module/test_bp/invoice_path',
                  'business_process_module/test_bp/invoice')))

        high_tax_invoice_line = invoice_line_list[2]
        self.assertEquals(high_tax_invoice_line.getResource(),
                'service_module/vat_high')
        self.assertAlmostEquals(high_tax_invoice_line.getQuantity(),
                luxury_invoice_line.getPrice() \
                        * number_of_additional_sale_packing_list_lines \
                        * number_of_sale_orders)
        simulation_movement_list \
                = high_tax_invoice_line.getDeliveryRelatedValueList()
        self.assertEquals(len(simulation_movement_list),
                number_of_additional_sale_packing_list_lines \
                        * number_of_sale_orders)
        for simulation_movement in simulation_movement_list:
          self.assertEquals(simulation_movement.getPortalType(),
                  'Simulation Movement')
          self.assertEquals(set(simulation_movement.getCausalityList()), set((
                  'business_process_module/test_bp/invoice_path',
                  'business_process_module/test_bp/invoice',
                  'sale_trade_condition_module/test_stc/vat_high')))

        low_tax_invoice_line = invoice_line_list[3]
        self.assertEquals(low_tax_invoice_line.getResource(),
                'service_module/vat_low')
        self.assertAlmostEquals(low_tax_invoice_line.getQuantity(),
                commodity_invoice_line.getPrice() \
                        * (number_of_sale_order_lines \
                           + number_of_additional_sale_packing_list_lines) \
                        * number_of_sale_orders)
        simulation_movement_list \
                = low_tax_invoice_line.getDeliveryRelatedValueList()
        self.assertEquals(len(simulation_movement_list),
                (number_of_sale_order_lines \
                        + number_of_additional_sale_packing_list_lines) \
                        * number_of_sale_orders)
        for simulation_movement in simulation_movement_list:
          self.assertEquals(simulation_movement.getPortalType(),
                  'Simulation Movement')
          self.assertEquals(set(simulation_movement.getCausalityList()), set((
                  'business_process_module/test_bp/invoice_path',
                  'business_process_module/test_bp/invoice',
                  'sale_trade_condition_module/test_stc/vat_low')))

    def stepCheckConvergedSalePackingLists(self, sequence=None,
            sequence_list=None, **kw):
      portal = self.getPortal()
      module = portal.sale_packing_list_module
      for packing_list in module.contentValues():
        self.assertEquals(packing_list.getCausalityState(), 'solved')

    def stepCheckDivergedSalePackingLists(self, sequence=None,
            sequence_list=None, **kw):
      portal = self.getPortal()
      module = portal.sale_packing_list_module
      for packing_list in module.contentValues():
        self.assertEquals(packing_list.getCausalityState(), 'diverged')

    def stepCheckSalePackingListSimulation(self, sequence=None,
            sequence_list=None, **kw):
      portal = self.getPortal()
      module = portal.sale_packing_list_module
      number_of_additional_sale_packing_list_lines \
              = sequence.get('number_of_additional_sale_packing_list_lines')
      destination_decision = sequence.get('destination_decision')
      destination_administration = sequence.get('destination_administration')
      for packing_list in module.contentValues(portal_type='Sale Packing List'):
        self.assertEquals(packing_list.getCausalityState(), 'solved')
        causality_list = packing_list.getCausalityRelatedValueList(portal_type='Applied Rule')
        self.assertEquals(len(causality_list), 1)
        applied_rule = causality_list[0]
        self.assertEquals(applied_rule.getPortalType(), 'Applied Rule')
        rule = applied_rule.getSpecialiseValue()
        self.assertNotEquals(rule, None)
        self.assertEquals(rule.getReference(),
                'test_delivery_root_simulation_rule')
        self.assertEquals(applied_rule.objectCount(),
                number_of_additional_sale_packing_list_lines)
        for simulation_movement in applied_rule.objectValues():
          self.assertEquals(simulation_movement.getPortalType(),
                  'Simulation Movement')
          delivery_list = simulation_movement.getDeliveryValueList()
          self.assertEquals(len(delivery_list), 1)
          delivery = delivery_list[0]
          self.assertEquals(delivery.getPortalType(), 'Sale Packing List Line')
          self.assertEquals(simulation_movement.getQuantity(),
                  delivery.getQuantity())
          self.assertEquals(simulation_movement.getResource(),
                  delivery.getResource())
          self.assertEquals(set(simulation_movement.getCausalityList()), set((
                  'business_process_module/test_bp/deliver_path',
                  'business_process_module/test_bp/deliver')))
          self.assertEquals(simulation_movement.getDestinationDecision(),
                  destination_decision)
          self.assertEquals(simulation_movement.getDestinationAdministration(),
                  destination_administration)

    def stepSetSolverTargetToDestinationAdministration(self, sequence=None,
            sequence_list=None, **kw):
      sequence.set('solver_target', 'destination_administration')

    def stepAdoptPrevisionToSalePackingLists(self, sequence=None,
            sequence_list=None, **kw):
      solver_target = sequence.get('solver_target')
      self.assertTrue(isinstance(solver_target, str))
      portal = self.getPortal()
      module = portal.sale_packing_list_module
      for packing_list in module.contentValues(portal_type='Sale Packing List'):
        divergence = packing_list.getDivergenceList()[0]
        self.assertEquals(divergence.tested_property, solver_target)
        packing_list.activate().SalePackingList_solveForTesting(
          solver_target, divergence.prevision_value)
        # XXX: Because divergence is ignored for 'destination_decision',
        #      its value is actually undefined after solving.
        #      Old solver updated the value on SPL at the same time as it
        #      adopted prevision for another property, but this is not the case
        #      anymore. So fix SPL for the rest of the sequence:
        packing_list.setDestinationDecisionList(
          packing_list.getCausalityValue().getDestinationDecisionList())
      # Make sure that the same taget is not used again.
      sequence.edit(solver_target=None)

    def stepAcceptDecisionOfSalePackingLists(self, sequence=None,
            sequence_list=None, **kw):
      solver_target = sequence.get('solver_target')
      self.assertTrue(isinstance(solver_target, str))
      portal = self.getPortal()
      module = portal.sale_packing_list_module
      for packing_list in module.contentValues(portal_type='Sale Packing List'):
        divergence = packing_list.getDivergenceList()[0]
        self.assertEquals(divergence.tested_property, solver_target)
        packing_list.activate().SalePackingList_solveForTesting(
          solver_target, divergence.decision_value)
      # Make sure that the same taget is not used again.
      sequence.edit(solver_target=None)

    def stepAddNewSalePackingLinesIntoSalePackingLists(self, sequence=None,
            sequence_list=None, **kw):
      portal = self.getPortal()
      module = portal.sale_packing_list_module
      number = sequence.get('number_of_additional_sale_packing_list_lines')
      resource = sequence.get('resource')
      for packing_list in module.contentValues(portal_type='Sale Packing List'):
        for i in xrange(number):
          packing_list.newContent(portal_type='Sale Packing List Line',
                  resource=resource, quantity=1.0)

    def stepStopSalePackingLists(self, sequence=None, sequence_list=None, **kw):
      portal = self.getPortal()
      module = portal.sale_packing_list_module
      for packing_list in module.contentValues(portal_type='Sale Packing List'):
        self.assertEquals(packing_list.getSimulationState(), 'confirmed')
        packing_list.stop()
        self.assertEquals(packing_list.getSimulationState(), 'stopped')

    def stepDeliverSalePackingLists(self, sequence=None, sequence_list=None,
            **kw):
      portal = self.getPortal()
      module = portal.sale_packing_list_module
      for packing_list in module.contentValues(portal_type='Sale Packing List'):
        self.assertEquals(packing_list.getSimulationState(), 'stopped')
        packing_list.deliver()
        self.assertEquals(packing_list.getSimulationState(), 'delivered')

    def stepTestResult(self, sequence=None, sequence_list=None, **kw):
      measurable = sequence.get('measurable')
      if measurable:
        result = sequence.get('result')
        if result:
          print ''
          failure_list = []
          for target, min_time, real_time, max_time in result:
            condition = (min_time < real_time < max_time)
            print '%s%s: %.4f < %.4f < %.4f' \
                    % (condition and ' ' or '!',
                            target, min_time, real_time, max_time)
            if not condition:
              failure_list.append(target)
          self.assertTrue(not failure_list,
                  'these tests failed: %s' % (', '.join(failure_list)))

    def test_01_CheckLogicAndMakeCacheHot(self):
      """Check the correctness of the logic as well as making the cache hot.
      """
      message = 'Check Logic'
      LOG('Testing... ', 0, message)
      #self.getPortal().portal_activities.manage_enableActivityTracking()
      self._checkSimulation(number_of_sale_orders=1,
              number_of_sale_order_lines=1,
              number_of_additional_sale_packing_list_lines=1,
              measurable=False)
      #self.getPortal().portal_activities.manage_disableActivityTracking()

    def test_02_CheckPerformance(self):
      """Check the performance.
      """
      message = 'Check Performance'
      LOG('Testing... ', 0, message)
      self._checkSimulation(number_of_sale_orders=5,
              number_of_sale_order_lines=5,
              number_of_additional_sale_packing_list_lines=5,
              measurable=True)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestSimulationPerformance))
  return suite