=====================================
Sale Credit Limit Validation Scenario
=====================================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> from trytond.modules.account_asset.tests.tools \
    ...     import add_asset_accounts
    >>> today = datetime.date.today()

Activate modules::

    >>> config = activate_modules('sale_credit_limit_validation')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> cash = accounts['cash']

Create tax::

    >>> tax = create_tax(Decimal('.10'))
    >>> tax.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.save()

Create account category::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.customer_taxes.append(tax)
    >>> account_category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.salable = True
    >>> template.list_price = Decimal('10')
    >>> template.cost_price = Decimal('5')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_category = account_category
    >>> template.save()
    >>> product.template = template
    >>> product.save()

Check sale configuration::
    >>> SaleConfig = Model.get('sale.configuration')
    >>> sale_config = SaleConfig(1)
    >>> sale_config.credit_limit_amount
    'total_amount'

Create sale::

    >>> Sale = Model.get('sale.sale')
    >>> sale = Sale()
    >>> sale.party = party
    >>> line = sale.lines.new()
    >>> line.product = product
    >>> line.quantity = 1
    >>> line.unit_price
    Decimal('10.0000')
    >>> sale.untaxed_amount, sale.tax_amount, sale.total_amount
    (Decimal('10.00'), Decimal('1.00'), Decimal('11.00'))
    >>> sale.click('quote')
    >>> sale.click('confirm')
    >>> sale.sale_credit_limit_amount
    'total_amount'

Check party credit amount with total_amount option::
    >>> party.credit_amount
    Decimal('11.00')

Change configuration to untaxed_amount::
    >>> sale_config.credit_limit_amount = 'untaxed_amount'
    >>> sale_config.save()

Create party2::

    >>> Party = Model.get('party.party')
    >>> party2 = Party(name='Party2')
    >>> party2.save()


Create new sale::
    >>> Sale = Model.get('sale.sale')
    >>> sale2 = Sale()
    >>> sale2.party = party2
    >>> line2 = sale2.lines.new()
    >>> line2.product = product
    >>> line2.quantity = 2
    >>> line2.unit_price
    Decimal('10.0000')
    >>> sale2.untaxed_amount, sale2.tax_amount, sale2.total_amount
    (Decimal('20.00'), Decimal('2.00'), Decimal('22.00'))
    >>> sale2.click('quote')
    >>> sale2.click('confirm')
    >>> sale2.sale_credit_limit_amount
    'untaxed_amount'

Check party credit amount with untaxed_amount option::
    >>> sale_config.credit_limit_amount
    'untaxed_amount'
    >>> party2.credit_amount
    Decimal('20.00')
