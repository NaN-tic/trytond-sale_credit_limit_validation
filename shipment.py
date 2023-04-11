from trytond.pool import PoolMeta, Pool
from trytond.model import dualmethod
from trytond.exceptions import UserError
from trytond.i18n import gettext


class ShipmentOut(metaclass=PoolMeta):
    __name__ = 'stock.shipment.out'

    @dualmethod
    def assign_try(cls, shipments):
        res = super().assign_try(shipments)
        pool = Pool()
        SaleLine = pool.get('sale.line')
        Config = pool.get('sale.configuration')

        config = Config(1)
        if not config.credit_limit_amount:
            raise UserError(gettext(
                'sale_credit_limit_validation.msg_configuration_not_found'))

        for shipment in shipments:
            sales = set([
                s.origin.sale for s in shipment.outgoing_moves if isinstance(
                s.origin, SaleLine)])
            # get_credit_amount search all sales that state are ['confirmed', 'processing']
            # Sales that come from shipments are in this state. Therefore, we must omit
            # amounts from these sales and not sum
            untaxed_amount = sum(
                getattr(s, config.credit_limit_amount) for s in sales) * -1
            party = shipment.customer
            # The origin is only needed to create the warning key
            party.check_credit_limit(untaxed_amount, origin=str(shipment))
        return res
