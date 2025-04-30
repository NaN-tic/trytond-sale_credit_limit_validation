# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import hashlib
from trytond.pool import PoolMeta, Pool
from trytond.model import dualmethod
from trytond.exceptions import UserError
from trytond.transaction import Transaction
from trytond.i18n import gettext
from decimal import Decimal


class ShipmentOut(metaclass=PoolMeta):
    __name__ = 'stock.shipment.out'

    @dualmethod
    def assign_try(cls, shipments):
        res = super().assign_try(shipments)
        pool = Pool()
        Config = pool.get('sale.configuration')

        config = Config(1)
        if not config.credit_limit_amount:
            raise UserError(gettext(
                'sale_credit_limit_validation.msg_configuration_not_found'))

        parties = {}
        for shipment in shipments:
            party = shipment.customer
            key = (party, shipment.company)
            if parties.get(key):
                parties[key] += [shipment]
            else:
                parties[key] = [shipment]

        # check_credit_limit will not raise the exception if the credit limit
        # does not change so we increase it by the minimal amount possible
        # based on the currency digits
        for key in parties:
            party, company = key
            minimal_amount = Decimal(str(10 ** -company.currency.digits))
            # The origin is only needed to create the warning key
            origin = hashlib.md5(str([s for s in shipments
                if s.customer == party]).encode('utf-8')).hexdigest()
            party.check_credit_limit(minimal_amount, company,
                origin='shipment_out_%s_%s' % (str(party), origin))

        return res
