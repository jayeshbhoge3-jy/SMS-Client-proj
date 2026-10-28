DEFAULT_CURRENCY = 'INR'

CURRENCY_DATA = {
    'INR': {
        'symbol': '₹',
        'name': 'Indian Rupee',
        'locale': 'en_IN',
    },
    'USD': {
        'symbol': '$',
        'name': 'US Dollar',
        'locale': 'en_US',
    },
    'EUR': {
        'symbol': '€',
        'name': 'Euro',
        'locale': 'de_DE',
    },
    'GBP': {
        'symbol': '£',
        'name': 'British Pound',
        'locale': 'en_GB',
    },
    'AED': {
        'symbol': 'AED',
        'name': 'UAE Dirham',
        'locale': 'ar_AE',
    },
    'CAD': {
        'symbol': 'C$',
        'name': 'Canadian Dollar',
        'locale': 'en_CA',
    },
    'AUD': {
        'symbol': 'A$',
        'name': 'Australian Dollar',
        'locale': 'en_AU',
    },
    'SGD': {
        'symbol': 'S$',
        'name': 'Singapore Dollar',
        'locale': 'en_SG',
    },
    'MYR': {
        'symbol': 'RM',
        'name': 'Malaysian Ringgit',
        'locale': 'ms_MY',
    },
    'SAR': {
        'symbol': 'SAR',
        'name': 'Saudi Riyal',
        'locale': 'ar_SA',
    },
}

CURRENCY_CHOICES = tuple(
    (code, f"{data['name']} ({data['symbol']})")
    for code, data in CURRENCY_DATA.items()
)

FALLBACK_RATES = {
    'INR': 1.0,
    'USD': 0.012,
    'EUR': 0.011,
    'GBP': 0.0095,
    'AED': 0.044,
    'CAD': 0.016,
    'AUD': 0.018,
    'SGD': 0.016,
    'MYR': 0.056,
    'SAR': 0.045,
}
