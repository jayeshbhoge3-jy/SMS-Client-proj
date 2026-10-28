from django import template
from company.currency_utils import (
    convert_amount, get_exchange_rates, get_currency_symbol,
    format_price, get_currency_locale
)
from company.currency_data import DEFAULT_CURRENCY, CURRENCY_DATA

register = template.Library()


@register.filter
def currency(amount, code):
    if not code:
        code = DEFAULT_CURRENCY
    rates = get_exchange_rates()
    return format_price(amount, code, rates)


@register.filter
def currency_symbol(code):
    if not code:
        code = DEFAULT_CURRENCY
    return get_currency_symbol(code)


@register.filter
def convert_inr(amount, code):
    if not code:
        code = DEFAULT_CURRENCY
    rates = get_exchange_rates()
    return convert_amount(amount, code, rates)
