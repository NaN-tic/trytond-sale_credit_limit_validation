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
        Company = pool.get('company.company')

        config = Config(1)
        if not config.credit_limit_amount:
            raise UserError(gettext(
                'sale_credit_limit_validation.msg_configuration_not_found'))

        parties = list(set([s.customer for s in shipments]))

        company_id = Transaction().context.get('company')
        digits = Company(company_id).currency.digits
        # check_credit_limit will not raise the exception if the credit limit
        # does not change so we increase it by the minimal amount possible
        # based on the currency digits
        minimal_amount = Decimal(str(10 ** -digits))
        for party in parties:
            # The origin is only needed to create the warning key
            origin = hashlib.md5(str([s for s in shipments
                if s.customer == party]).encode('utf-8')).hexdigest()
            party.check_credit_limit(minimal_amount,
                origin='shipment_out_%s_%s' % (str(party), origin))

        return res
