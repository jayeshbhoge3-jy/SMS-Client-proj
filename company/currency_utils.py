import requests
from decimal import Decimal
from django.core.cache import cache
from babel.numbers import format_currency as babel_format_currency

from company.currency_data import (
    CURRENCY_DATA, FALLBACK_RATES, DEFAULT_CURRENCY
)

CACHE_KEY = 'inr_exchange_rates'
CACHE_TIMEOUT = 3600


def get_exchange_rates():
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    rates = dict(FALLBACK_RATES)

    try:
        resp = requests.get(
            'https://api.frankfurter.app/latest?from=INR',
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            api_rates = data.get('rates', {})
            for code in rates:
                if code in api_rates and code != 'INR':
                    rates[code] = api_rates[code]
    except Exception:
        pass

    cache.set(CACHE_KEY, rates, CACHE_TIMEOUT)
    return rates


def convert_amount(amount_inr, target_currency, rates=None):
    if rates is None:
        rates = get_exchange_rates()
    if target_currency == DEFAULT_CURRENCY:
        return Decimal(str(amount_inr))
    rate = Decimal(str(rates.get(target_currency, 1)))
    return Decimal(str(amount_inr)) * rate


def get_currency_symbol(code):
    meta = CURRENCY_DATA.get(code, CURRENCY_DATA[DEFAULT_CURRENCY])
    return meta['symbol']


def get_currency_locale(code):
    meta = CURRENCY_DATA.get(code, CURRENCY_DATA[DEFAULT_CURRENCY])
    return meta['locale']


def format_price(amount, code, rates=None):
    if rates is None:
        rates = get_exchange_rates()
    converted = convert_amount(amount, code, rates)
    locale = get_currency_locale(code)
    try:
        return babel_format_currency(
            float(converted), code, locale=locale
        )
    except Exception:
        symbol = get_currency_symbol(code)
        return f"{symbol}{converted:,.2f}"


def convert_to_inr(amount_foreign, source_currency, rates=None):
    if rates is None:
        rates = get_exchange_rates()
    if source_currency == DEFAULT_CURRENCY:
        return Decimal(str(amount_foreign))
    rate = Decimal(str(rates.get(source_currency, 1)))
    if rate == 0:
        return Decimal('0')
    return Decimal(str(amount_foreign)) / rate
