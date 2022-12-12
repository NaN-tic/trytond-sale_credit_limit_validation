# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import dualmethod
from trytond.pool import PoolMeta, Pool
from trytond.exceptions import UserError
from trytond.i18n import gettext


class Production(metaclass=PoolMeta):
    __name__ = 'production'

    @dualmethod
    def assign_try(cls, productions):
        pool = Pool()
        SaleLine = pool.get('sale.line')
        Config = pool.get('sale.configuration')

        config = Config(1)
        if not config.credit_limit_amount:
            raise UserError(gettext(
                'sale_credit_limit_validation.msg_configuration_not_found'))

        for production in productions:
            if production.origin and isinstance(production.origin, SaleLine):
                untaxed_amount = getattr(production.origin.sale,
                    config.credit_limit_amount)
                party = production.origin.sale.party
                # The origin is only needed to create the warning key
                party.check_credit_limit(untaxed_amount,
                    origin=str(production))

        super(Production, cls).assign_try(productions)
