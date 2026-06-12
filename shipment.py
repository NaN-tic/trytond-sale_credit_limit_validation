# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import PoolMeta, Pool
from trytond.model import dualmethod
from trytond.exceptions import UserError
from trytond.i18n import gettext
from decimal import Decimal


class ShipmentOut(metaclass=PoolMeta):
    __name__ = 'stock.shipment.out'

    def _credit_limit_parties(self):
        parties = []
        for move in self.outgoing_moves:
            sale = move.sale
            if not sale:
                parties.append(self.customer)
                continue
            parties.append(sale.invoice_party or sale.party)
        if parties:
            return list(set(parties))
        return [self.customer]

    @dualmethod
    def assign_try(cls, shipments):
        pool = Pool()
        Config = pool.get('sale.configuration')

        config = Config(1)
        if not config.credit_limit_amount:
            raise UserError(gettext(
                'sale_credit_limit_validation.msg_configuration_not_found'))

        for shipment in shipments:
            company = shipment.company
            minimal_amount = Decimal(str(10 ** -company.currency.digits))
            for party in shipment._credit_limit_parties():
                party.check_credit_limit(
                    minimal_amount, company, origin=str(shipment))

        super().assign_try(shipments)
