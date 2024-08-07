import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear, create_tax,
                                                 get_accounts)
from trytond.modules.account_credit_limit.exceptions import CreditLimitWarning
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules, set_user

class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Activate modules
        config = activate_modules('sale_credit_limit_validation')

        # Create company
        _ = create_company()
        company = get_company()

        # Set employee
        User = Model.get('res.user')
        Party = Model.get('party.party')
        Employee = Model.get('company.employee')
        employee_party = Party(name="Employee")
        employee_party.save()
        employee = Employee(party=employee_party)
        employee.save()
        user = User(config.user)
        user.employees.append(employee)
        user.employee = employee
        user.save()
        set_user(user.id)

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']
        Journal = Model.get('account.journal')
        cash_journal, = Journal.find([('type', '=', 'cash')])
        cash_journal.save()

        # Create tax
        tax = create_tax(Decimal('.10'))
        tax.save()

        # Create parties
        Party = Model.get('party.party')
        customer = Party(name='Customer')
        customer.credit_limit_amount = Decimal('60')
        customer.save()

        # Create account categories
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()
        account_category_tax, = account_category.duplicate()
        account_category_tax.customer_taxes.append(tax)
        account_category_tax.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.salable = True
        template.list_price = Decimal('50')
        template.account_category = account_category_tax
        template.save()
        product, = template.products

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create an Inventory
        Inventory = Model.get('stock.inventory')
        Location = Model.get('stock.location')
        storage, = Location.find([
            ('code', '=', 'STO'),
        ])
        inventory = Inventory()
        inventory.location = storage
        inventory_line = inventory.lines.new(product=product)
        inventory_line.quantity = 100.0
        inventory_line.expected_quantity = 0.0
        inventory.click('confirm')
        self.assertEqual(inventory.state, 'done')

        # First Sale
        Sale = Model.get('sale.sale')
        SaleLine = Model.get('sale.line')
        sale = Sale()
        sale.party = customer
        sale.payment_term = payment_term
        sale.invoice_method = 'shipment'
        sale.shipment_method = 'order'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 1.0
        sale.click('quote')
        self.assertEqual(sale.untaxed_amount, Decimal('50.00'))

        self.assertEqual(sale.tax_amount, Decimal('5.00'))

        self.assertEqual(sale.total_amount, Decimal('55.00'))
        self.assertEqual(sale.quoted_by, employee)
        sale.click('confirm')
        self.assertEqual(sale.state, 'processing')
        shipment, = sale.shipments
        shipment.click('assign_try')
        shipment.click('pick')
        shipment.click('pack')
        shipment.click('done')

        # Second Sale
        sale = Sale()
        sale.party = customer
        sale.payment_term = payment_term
        sale.invoice_method = 'shipment'
        sale.shipment_method = 'order'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 1.0
        sale.click('quote')
        self.assertEqual(sale.untaxed_amount, Decimal('50.00'))

        self.assertEqual(sale.tax_amount, Decimal('5.00'))

        self.assertEqual(sale.total_amount, Decimal('55.00'))
        with self.assertRaises(CreditLimitWarning):
            sale.click('confirm')

        with self.assertRaises(CreditLimitWarning):
            try:
                sale.click('confirm')
            except CreditLimitWarning as warning:
                _, (key, *_) = warning.args
                raise

        Warning = Model.get('res.user.warning')
        Warning(user=config.user, name=key).save()
        sale.click('confirm')
        self.assertEqual(sale.state, 'processing')
        shipment, = sale.shipments
        with self.assertRaises(CreditLimitWarning):
            shipment.click('assign_try')

        # Increase credit limit
        customer.credit_limit_amount = Decimal('150')
        customer.save()

        # Continue assign when customer has enough credit limit
        shipment.click('assign_try')
        shipment.click('pick')
        shipment.click('pack')
        shipment.click('done')

        # Reload sale
        sale.reload()
        self.assertEqual(sale.state, 'processing')
        self.assertEqual(sale.shipment_state, 'sent')
        self.assertEqual(sale.invoice_state, 'pending')
