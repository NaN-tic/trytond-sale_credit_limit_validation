# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields, ModelSQL
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.modules.company.model import CompanyValueMixin
from trytond.exceptions import UserError
from trytond.i18n import gettext


credit_limit_amount_values = [
    ('untaxed_amount', 'Untaxed Amount'),
    ('total_amount', 'Total Amount')]


class Configuration(metaclass=PoolMeta):
    __name__ = 'sale.configuration'

    credit_limit_amount = fields.MultiValue(
        fields.Selection(credit_limit_amount_values, "Credit Limit Amount",
        required=True))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in {'credit_limit_amount'}:
            return pool.get('sale.configuration.credit_limit_amount')
        return super(Configuration, cls).multivalue_model(field)

    @classmethod
    def default_credit_limit_amount(cls, **pattern):
        return cls.multivalue_model(
            'credit_limit_amount').default_credit_limit_amount()


class ConfigurationCompanyCreditLimitAmount(ModelSQL, CompanyValueMixin):
    "Configuration Company Credit Limit Amount"
    __name__ = 'sale.configuration.credit_limit_amount'

    credit_limit_amount = fields.Selection(credit_limit_amount_values,
        "Credit Limit Amount", required=True)

    @classmethod
    def default_credit_limit_amount(cls):
        return 'total_amount'


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    sale_credit_limit_amount = fields.Selection(credit_limit_amount_values,
        "Credit Limit Amount",
        states={
            'readonly': ~Eval('state').in_(['draft', 'quotation']),
            'required': ~Eval('state').in_(
                ['draft', 'quotation', 'cancelled']),
        }, depends=['state'])

    @classmethod
    def default_sale_credit_limit_amount(cls, **pattern):
        pool = Pool()
        Configuration = pool.get('sale.configuration')
        config = Configuration(1)
        if not config.get_multivalue(
                'credit_limit_amount', **pattern):
            raise UserError(gettext(
                'sale_credit_limit_validation.msg_configuration_not_found'))
        return config.get_multivalue('credit_limit_amount',
            **pattern)

    @property
    def credit_limit_amount(self):
        pool = Pool()
        Config = pool.get('sale.configuration')

        config = Config(1)

        if (config.credit_limit_amount and
                config.credit_limit_amount == 'total_amount'):
            return self.total_amount
        return self.untaxed_amount

    @classmethod
    def copy(cls, sales, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('sale_credit_limit_amount',
            cls.default_sale_credit_limit_amount())
        return super(Sale, cls).copy(sales, default=default)
