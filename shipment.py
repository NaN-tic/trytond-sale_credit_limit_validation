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
            raise UserError(gettext('helsa.msg_configuration_not_found'))

        for shipment in shipments:
            sales = set([
                s.origin.sale for s in shipment.outgoing_moves if isinstance(
                s.origin, SaleLine)])
            untaxed_amount = sum(
                getattr(s, config.credit_limit_amount) for s in sales)
            party = shipment.customer
            # The origin is only needed to create the warning key
            party.check_credit_limit(untaxed_amount, origin=str(shipment))
        return res
