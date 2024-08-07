import datetime
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
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Activate modules
        config = activate_modules(
            ['sale_supply_production', 'sale_credit_limit_validation'])

        # Create company
        _ = create_company()
        company = get_company()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.save()
        customer = Party(name='Customer')
        customer.credit_limit_amount = Decimal('60')
        customer.save()

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Configure production location
        Location = Model.get('stock.location')
        warehouse, = Location.find([('code', '=', 'WH')])
        production_location, = Location.find([('code', '=', 'PROD')])
        warehouse.production_location = production_location
        warehouse.save()

        # Create tax
        tax = create_tax(Decimal('.10'))
        tax.save()

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
        template.producible = True
        template.supply_production_on_sale = True
        template.salable = True
        template.list_price = Decimal(30)
        template.account_category = account_category_tax
        product, = template.products
        product.cost_price = Decimal(20)
        template.save()
        product, = template.products

        # Create Components
        template1 = ProductTemplate()
        template1.name = 'component 1'
        template1.default_uom = unit
        template1.type = 'goods'
        template1.list_price = Decimal(5)
        component1, = template1.products
        component1.cost_price = Decimal(1)
        template1.save()
        component1, = template1.products
        meter, = ProductUom.find([('name', '=', 'Meter')])
        centimeter, = ProductUom.find([('name', '=', 'Centimeter')])
        template2 = ProductTemplate()
        template2.name = 'component 2'
        template2.default_uom = meter
        template2.type = 'goods'
        template2.list_price = Decimal(7)
        component2, = template2.products
        component2.cost_price = Decimal(5)
        template2.save()
        component2, = template2.products

        # Create Bill of Material
        BOM = Model.get('production.bom')
        BOMInput = Model.get('production.bom.input')
        BOMOutput = Model.get('production.bom.output')
        bom = BOM(name='product')
        input1 = BOMInput()
        bom.inputs.append(input1)
        input1.product = component1
        input1.quantity = 5
        input2 = BOMInput()
        bom.inputs.append(input2)
        input2.product = component2
        input2.quantity = 150
        input2.uom = centimeter
        output = BOMOutput()
        bom.outputs.append(output)
        output.product = product
        output.quantity = 1
        bom.save()
        ProductBom = Model.get('product.product-production.bom')
        product.boms.append(ProductBom(bom=bom))
        product.save()
        ProductionLeadTime = Model.get('production.lead_time')
        production_lead_time = ProductionLeadTime()
        production_lead_time.product = product
        production_lead_time.bom = bom
        production_lead_time.lead_time = datetime.timedelta(1)
        production_lead_time.save()

        # Create an Inventory
        Inventory = Model.get('stock.inventory')
        InventoryLine = Model.get('stock.inventory.line')
        Location = Model.get('stock.location')
        storage, = Location.find([
            ('code', '=', 'STO'),
        ])
        inventory = Inventory()
        inventory.location = storage
        inventory_line1 = InventoryLine()
        inventory.lines.append(inventory_line1)
        inventory_line1.product = component1
        inventory_line1.quantity = 20
        inventory_line2 = InventoryLine()
        inventory.lines.append(inventory_line2)
        inventory_line2.product = component2
        inventory_line2.quantity = 6
        inventory.click('confirm')
        self.assertEqual(inventory.state, 'done')

        # Sale product
        Sale = Model.get('sale.sale')
        SaleLine = Model.get('sale.line')
        sale = Sale()
        sale.party = customer
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 1.0
        sale.click('quote')
        sale.click('confirm')
        self.assertEqual(sale.state, 'processing')
        sale_line, = sale.lines
        production, = sale.productions
        self.assertEqual(production.product, product)
        self.assertEqual(production.quantity, 1.0)
        self.assertEqual(len(production.inputs), 2)
        self.assertEqual(len(production.outputs), 1)

        # Second Sale
        Sale = Model.get('sale.sale')
        SaleLine = Model.get('sale.line')
        sale = Sale()
        sale.party = customer
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 1.0
        sale.click('quote')

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
        sale_line, = sale.lines
        production, = sale.productions
        self.assertEqual(production.product, product)
        self.assertEqual(production.quantity, 1.0)
        self.assertEqual(len(production.inputs), 2)
        self.assertEqual(len(production.outputs), 1)
        production.click('wait')

        with self.assertRaises(CreditLimitWarning):
            production.click('assign_try')

        # Increase credit limit
        customer.credit_limit_amount = Decimal('150')
        customer.save()

        # Continue assign when customer has enough credit limit
        production.click('assign_try')
        production.click('run')
        production.click('done')
        self.assertEqual(production.state, 'done')
