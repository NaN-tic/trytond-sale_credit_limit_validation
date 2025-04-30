# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import hashlib
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
        SaleLine = pool.get('sale.line')
        Config = pool.get('sale.configuration')

        config = Config(1)
        if not config.credit_limit_amount:
            raise UserError(gettext(
                'sale_credit_limit_validation.msg_configuration_not_found'))

        parties = {}
        for production in productions:
            if production.origin and isinstance(production.origin, SaleLine):
                party = production.origin.sale.party
                key = (party, production.company)
                if parties.get(key):
                    parties[key] += [production]
                else:
                    parties[key] = [production]

        for key, productions in parties.items():
            party, company = key
            # The origin is only needed to create the warning key
            origin = hashlib.md5(
                    str(productions).encode('utf-8')).hexdigest()
            minimal_amount = Decimal(str(10 ** -company.currency.digits))
            party.check_credit_limit(minimal_amount, company,
                origin='production_%s_%s' % (str(party), origin))

        return super(Production, cls).assign_try(productions)
