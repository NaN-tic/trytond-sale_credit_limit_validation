# This file is part sale_credit_limit_validation module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import shipment
from . import production

def register():
    Pool.register(
        shipment.ShipmentOut,
        module='sale_credit_limit_validation', type_='model')
    Pool.register(
        production.Production,
        module='sale_credit_limit_validation', type_='model', depends=['production'])
