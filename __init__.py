# This file is part sale_credit_limit_validation module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import party
from . import sale
from . import production

def register():
    Pool.register(
        sale.ConfigurationCompanyCreditLimitAmount,
        sale.Configuration,
        party.Party,
        sale.Sale,
        production.Production,
        module='sale_credit_limit_validation', type_='model')
