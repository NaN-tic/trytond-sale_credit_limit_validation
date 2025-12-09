# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import dualmethod
from trytond.pool import PoolMeta, Pool
from trytond.exceptions import UserError
from trytond.i18n import gettext
from decimal import Decimal


class Production(metaclass=PoolMeta):
    __name__ = 'production'

    @dualmethod
    def assign_try(cls, productions):
        pool = Pool()
        Config = pool.get('sale.configuration')
        SaleLine = pool.get('sale.line')

        config = Config(1)
        if not config.credit_limit_amount:
            raise UserError(gettext(
                'sale_credit_limit_validation.msg_configuration_not_found'))

        parties = {}
        for production in productions:
            if production.origin and isinstance(production.origin, SaleLine):
                party = production.origin.sale.party
                if party in parties:
                    parties[party] += [production]
                else:
                    parties[party] = [production]

        for party, productions in parties.items():
            for production in productions:
                company = production.company
                minimal_amount = Decimal(str(10 ** -company.currency.digits))
                party.check_credit_limit(minimal_amount, company, origin=str(production))

        super().assign_try(productions)
