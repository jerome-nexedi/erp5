##############################################################################
#
# Copyright (c) 2007 Nexedi SARL and Contributors. All Rights Reserved.
#                     Kazuhiko <kazuhiko@nexedi.com>
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

#
# ERP5 Naming Convention Test script.
#
# usage: python runUnitTest.py [OPTION]... namingConventionTest.py
#

import re
import unittest
import os

from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase

class TestNamingConvention(ERP5TypeTestCase):
    def getBusinessTemplateList(self):
        """
	  Return the list of business templates.
	"""
	# include all standard Business Templates, i.e. erp5_*
	return ('erp5_core_proxy_field_legacy','erp5_base', 'erp5_pdm',
		'erp5_simulation','erp5_trade', 'erp5_accounting',
		'erp5_apparel', 'erp5_mrp', 'erp5_project',
		'erp5_ingestion_mysql_innodb_catalog','erp5_ingestion',
		'erp5_jquery','erp5_web','erp5_dms', 'erp5_csv_style', 'erp5_crm',
		'erp5_budget', 'erp5_item','erp5_ui_test_core', 'erp5_ui_test',
		'erp5_accounting_l10n_fr', 'erp5_invoicing','erp5_accounting_ui_test',
		'erp5_banking_core', 'erp5_banking_cash', 'erp5_banking_check',
		'erp5_banking_inventory', 'erp5_commerce', 'erp5_consulting',
		'erp5_dummy_movement', 'erp5_forge', 'erp5_pdm',
		'erp5_mobile', 'erp5_payroll','erp5_credential','erp5_jquery_ui',
		'erp5_payroll_ui_test', 'erp5_pdf_editor', 'erp5_publication',
		'erp5_dms_ui_test','erp5_administration','erp5_advanced_invoicing',
		'erp5_apparel','erp5_archive','erp5_auto_logout','erp5_barcode',
		'erp5_budget','erp5_calendar','erp5_knowledge_pad','erp5_km',
		'erp5_oauth','erp5_ods_style','erp5_odt_style','erp5_ooo_import',
		'erp5_open_trade','erp5_open_trade_periodicity_line','erp5_payment_mean',
		'erp5_secure_payment','erp5_paypal_secure_payment','erp5_payzen_secure_payment',
		'erp5_public_accounting_budget','erp5_publication',
		'erp5_run_my_doc', 'erp5_short_message','erp5_simplified_invoicing',
		'erp5_trade_knowledge_pad','erp5_trade_proxy_field_legacy','erp5_trade_ui_test',
		# skip l10n templates to save time.
		# 'erp5_l10n_fr', 'erp5_l10n_ja',
		# 'erp5_l10n_pl_PL', 'erp5_l10n_pt-BR',
		# 'erp5_accounting_l10n_fr_m14', 'erp5_accounting_l10n_fr_m9',
		# 'erp5_accounting_l10n_pl',
		# 'erp5_accounting_l10n_sn',
		# 'erp5_accounting_l10n_in',
		)
  
    def getTitle(self):
        return "Naming Convention"

    def checkClosedClassWord(self, path, id, title, fdata):
         error_message = ''
         word_list = title.split(' ')
         for word in word_list:
            word = word.strip('()')
            if word.isdigit():
              continue
            if word != word_list[0] and word.lower() in fdata and word.istitle():
              error_message += '%s: %s : %r is a closed class word \n' % (path, id,  word)
         return error_message
      
    def testClosedClassWords(self):
        message_list = []
        test_path = os.path.dirname(__file__)
        source_path = os.path.join(test_path, 'input', 'closed_class_words.txt')
        assert os.path.exists(source_path)
        f = open(source_path, "r")
        fdata = f.read().split(' ')
        for folder in self.portal.portal_skins.objectValues(spec=('Folder',)):
          if not folder.id.startswith('erp5_'):
            continue
          for form in folder.objectValues(spec=('ERP5 Form',)):
            message = self.checkClosedClassWord('/'.join([folder.id, form.id]), "Title of the form itself", form.title, fdata)
            if message:
              message_list.append(message)
            for group in form.get_groups():
              if group == 'hidden':
                continue
            for field in form.get_fields_in_group(group):
              if field.get_value('hidden') or field.id == 'matrixbox':
                continue
              message = self.checkClosedClassWord('/'.join([folder.id, form.id]), field.id, field.title(), fdata)
              if message:
                message_list.append(message)
        self.assertEquals(0, len(message_list))

    def testNamingConvention(self):
        result = 'installed templates: %s\n' % repr(self.getBusinessTemplateList())
	result += self.getPortal().portal_skins.erp5_core.ERP5Site_checkNamingConventions(html_output=None)
	problems_re = re.compile('([0-9]+) problems found')
	problems = int(problems_re.search(result).group(1))
	self.assertEquals(0, problems, result)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestNamingConvention))
    return suite