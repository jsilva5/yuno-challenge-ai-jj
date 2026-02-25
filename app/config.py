"""
Country-method configuration, prior success rates, and adjustment factors.
These priors represent domain knowledge before any real transaction data.
"""

# Available payment methods per country
COUNTRY_METHODS = {
    "BR": ["pix", "credit_card", "boleto"],
    "MX": ["oxxo", "credit_card", "spei"],
    "PH": ["gcash", "grabpay", "credit_card"],
    "CO": ["pse", "credit_card", "neki"],
    "JP": ["paypay", "seven_eleven", "credit_card"],
}

# Prior success rates (domain knowledge before real data)
PRIOR_RATES = {
    ("BR", "pix"): 0.85,
    ("BR", "credit_card"): 0.15,
    ("BR", "boleto"): 0.65,
    ("MX", "oxxo"): 0.72,
    ("MX", "credit_card"): 0.20,
    ("MX", "spei"): 0.68,
    ("PH", "gcash"): 0.81,
    ("PH", "grabpay"): 0.75,
    ("PH", "credit_card"): 0.10,
    ("CO", "pse"): 0.70,
    ("CO", "credit_card"): 0.20,
    ("CO", "neki"): 0.62,
    ("JP", "paypay"): 0.82,
    ("JP", "seven_eleven"): 0.73,
    ("JP", "credit_card"): 0.42,
}

# Amount ranges where each method performs well (min, max in USD equivalent)
AMOUNT_RANGES = {
    "pix": (1, 5000),
    "credit_card": (1, 10000),
    "boleto": (5, 3000),
    "oxxo": (5, 2000),
    "spei": (10, 50000),
    "gcash": (1, 500),
    "grabpay": (1, 500),
    "pse": (10, 10000),
    "neki": (5, 5000),
    "paypay": (1, 3000),
    "seven_eleven": (1, 2000),
}

# Rough USD conversion rates for amount normalization
CURRENCY_TO_USD = {
    "BRL": 0.20,
    "MXN": 0.058,
    "PHP": 0.017,
    "COP": 0.00024,
    "JPY": 0.0067,
    "USD": 1.0,
}

# Methods that get a bonus during business hours (9am-5pm)
BUSINESS_HOURS_METHODS = {"spei", "pse", "neki"}
BUSINESS_HOURS_BONUS = 1.1   # 10% boost during business hours
OFF_HOURS_PENALTY = 0.85     # 15% penalty outside business hours

# Bayesian prior weight — number of "virtual" transactions representing our prior belief
ALPHA = 10
