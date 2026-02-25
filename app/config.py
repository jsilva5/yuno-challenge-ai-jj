"""
Country-method configuration, prior success rates, and adjustment factors.
These priors represent domain knowledge before any real transaction data.
"""

# Available payment methods per country
COUNTRY_METHODS = {
    "BR": ["pix", "credit_card", "bank_transfer"],
    "MX": ["oxxo", "credit_card", "bank_transfer"],
    "PH": ["gcash", "grabpay", "credit_card"],
    "CO": ["pse", "credit_card", "bank_transfer"],
    "KE": ["mpesa", "credit_card", "bank_transfer"],
}

# Prior success rates (domain knowledge before real data)
PRIOR_RATES = {
    ("BR", "pix"): 0.85,
    ("BR", "credit_card"): 0.15,
    ("BR", "bank_transfer"): 0.40,
    ("MX", "oxxo"): 0.72,
    ("MX", "credit_card"): 0.20,
    ("MX", "bank_transfer"): 0.35,
    ("PH", "gcash"): 0.81,
    ("PH", "grabpay"): 0.75,
    ("PH", "credit_card"): 0.10,
    ("CO", "pse"): 0.70,
    ("CO", "credit_card"): 0.20,
    ("CO", "bank_transfer"): 0.35,
    ("KE", "mpesa"): 0.82,
    ("KE", "credit_card"): 0.15,
    ("KE", "bank_transfer"): 0.30,
}

# Amount ranges where each method performs well (min, max in USD equivalent)
AMOUNT_RANGES = {
    "pix": (1, 5000),
    "credit_card": (1, 10000),
    "bank_transfer": (50, 50000),
    "oxxo": (5, 2000),
    "gcash": (1, 500),
    "grabpay": (1, 500),
    "pse": (10, 10000),
    "mpesa": (1, 1000),
}

# Rough USD conversion rates for amount normalization
CURRENCY_TO_USD = {
    "BRL": 0.20,
    "MXN": 0.058,
    "PHP": 0.017,
    "COP": 0.00024,
    "KES": 0.0077,
    "USD": 1.0,
}

# Methods that get a bonus during business hours (9am-5pm)
BUSINESS_HOURS_METHODS = {"bank_transfer", "pse"}
BUSINESS_HOURS_BONUS = 1.1   # 10% boost during business hours
OFF_HOURS_PENALTY = 0.85     # 15% penalty outside business hours

# Bayesian prior weight — number of "virtual" transactions representing our prior belief
ALPHA = 10
