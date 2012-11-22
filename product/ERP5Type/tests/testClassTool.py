##############################################################################
#
# Copyright (c) 2002-2007 Nexedi SARL and Contributors. All Rights Reserved.
#                     Jean-Paul Smets <jp@nexedi.com>
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

from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
from AccessControl.SecurityManagement import newSecurityManager
from Products.ERP5Type.tests.utils import installRealClassTool
from App.config import getConfiguration

class TestClassTool(ERP5TypeTestCase):

  def getTitle(self):
    return "Class Tool"

  def afterSetUp(self):
    self.login()
    installRealClassTool(self.portal)

  def login(self):
    uf = self.portal.acl_users
    uf._doAddUser('seb', '', ['Manager'], [])
    uf._doAddUser('ERP5TypeTestCase', '', ['Manager'], [])
    user = uf.getUserById('seb').__of__(uf)
    newSecurityManager(None, user)

  def test_01_CheckClassTool(self):
    """
      Make sure that portal_classes exists
    """
    portal = self.portal
    self.assertNotEqual(None,getattr(portal,'portal_classes',None))
    self.commit()
    # check if web UI works
    portal_classes = portal.portal_classes
    portal_classes.manage_viewDocumentList()
    portal_classes.manage_viewPropertySheetList()
    portal_classes.manage_viewConstraintList()
    portal_classes.manage_viewExtensionList()
    portal_classes.manage_viewTestList()


  def test_02_CheckFileWriteIsTransactional(self):
    portal = self.portal
    portal_classes = portal.portal_classes

    self.assertEqual(portal_classes.getLocalDocumentList(), [],
        'Test environment is dirty. Please clean up the instance home of '
        'the test environment and fix up tests that might have left over '
        'files at %s' % getConfiguration().instancehome
    )
    portal_classes.newDocument('Toto')
    self.abort()
    self.assertNotEqual(portal_classes.getLocalDocumentList(), ['Toto'])

    portal_classes.newDocument('Toto')
    self.commit()
    self.assertEqual(portal_classes.getLocalDocumentList(), ['Toto'])


  # Test self-documentating features of ERP5Type documents through
  # portal_classes.
  def test_AsDocumentationHelperOnDocument(self):
    """
    All Documents can be turned into a documentation helper
    """
    portal = self.getPortal()
    folder = portal.newContent(portal_type='Folder', id='test_folder')
    doc_helper = folder.asDocumentationHelper()
    self.assertNotEquals(doc_helper, None)
    # We simply check that we can access methods of the documentation helper
    self.failUnless('Base' in doc_helper.getInheritanceList())
    self.assertNotEquals([], doc_helper.getStaticMethodList())


  def test_AsDocumentationHelperOnClassTool(self):
    """
    From the class tool, we can get documentation helper for classes defining
    a Document
    """
    class_tool = self.getPortal().portal_classes
    class_doc_helper = class_tool.asDocumentationHelper(class_id='Folder')
    self.assertNotEquals(class_doc_helper, None)
    # We simply check that we can access methods of the documentation helper
    self.assertNotEquals([], class_doc_helper.getStaticPropertyList())


  def test_DocumentationHelperActivities(self):
    """
    Using documentation helpers should not create any activity
    """
    portal = self.getPortal()
    folder = portal.newContent(portal_type='Folder', id='test_folder')
    self.tic()
    doc_helper = folder.asDocumentationHelper()
    self.commit()
    self.assertEquals(0, len(portal.portal_activities.getMessageList()))


  def test_DocumentationHelperExpressionCategory(self):
    """
    This tests checks that Documentation Helper works with propertysheets
    that define their categories using expressions.
    """
    from Products.ERP5Type.Core import DynamicCategoryProperty
    from erp5.portal_type import Movement, Delivery
    movement = Movement('dummy_movement').__of__(
                        Delivery('dummy_delivery').__of__(self.portal))
    # This test relies on the fact that Movement class has categories defined
    # by an expression.
    portal_property_sheets = self.portal.portal_property_sheets
    movement_propert_sheet = portal_property_sheets.Movement

    for ps in movement_propert_sheet.contentValues():
      if isinstance(ps, DynamicCategoryProperty.DynamicCategoryProperty):
          break
    else:
      self.fail("Movement _categories doesn't include expressions; "
                "this test is outdated")
    self.assertNotEquals(None, movement.asDocumentationHelper())


import unittest
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestClassTool))
    return suite

