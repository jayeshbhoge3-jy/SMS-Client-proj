from company.currency_utils import (
    get_exchange_rates, get_currency_symbol, get_currency_locale
)
from company.currency_data import DEFAULT_CURRENCY


def currency_context(request):
    if not request.user.is_authenticated:
        return {
            'currency_code': DEFAULT_CURRENCY,
            'currency_symbol': get_currency_symbol(DEFAULT_CURRENCY),
            'currency_locale': get_currency_locale(DEFAULT_CURRENCY),
            'exchange_rates': get_exchange_rates(),
        }

    profile = getattr(request.user, 'userprofile', None)
    if not profile or not hasattr(profile, 'company'):
        return {
            'currency_code': DEFAULT_CURRENCY,
            'currency_symbol': get_currency_symbol(DEFAULT_CURRENCY),
            'currency_locale': get_currency_locale(DEFAULT_CURRENCY),
            'exchange_rates': get_exchange_rates(),
        }

    company = profile.company
    code = getattr(company, 'display_currency', DEFAULT_CURRENCY) or DEFAULT_CURRENCY

    return {
        'currency_code': code,
        'currency_symbol': get_currency_symbol(code),
        'currency_locale': get_currency_locale(code),
        'exchange_rates': get_exchange_rates(),
    }
