from django.conf import settings

TOKENS_PER_CREDIT = 40_000

# Canonical credit pack definitions — single source of truth for both the
# Stripe webhook (stripeHooks/views.py) and the AI viewset (gyms/views/ai.py).
# Price IDs come from settings so they can be overridden per environment via env vars.
CREDIT_PACKS = [
    {
        "name":              "Starter",
        "description":       "5 AI Credits / month",
        "credits":           5,
        "tokens":            5 * TOKENS_PER_CREDIT,
        "price_usd":         4.99,
        "apple_product_id":  "credits_5",
        "google_product_id": "credits_5",
        "stripe_price_id":   settings.STRIPE_PRICE_ID_CREDITS_5,
    },
    {
        "name":              "Athleteeee",
        "description":       "15 AI Credits / month",
        "credits":           15,
        "tokens":            15 * TOKENS_PER_CREDIT,
        "price_usd":         9.99,
        "apple_product_id":  "credits_15",
        "google_product_id": "credits_15",
        "stripe_price_id":   settings.STRIPE_PRICE_ID_CREDITS_15,
    },
    {
        "name":              "Pro",
        "description":       "35 AI Credits / month",
        "credits":           35,
        "tokens":            35 * TOKENS_PER_CREDIT,
        "price_usd":         19.99,
        "apple_product_id":  "credits_35",
        "google_product_id": "credits_35",
        "stripe_price_id":   settings.STRIPE_PRICE_ID_CREDITS_35,
    },
]

# Keyed by Stripe price ID — used by the Stripe webhook
STRIPE_CREDIT_PACKAGES = {
    p["stripe_price_id"]: p for p in CREDIT_PACKS
}

# Keyed by store product ID — used by RevenueCat webhook and mobile IAP confirmation
RC_CREDIT_PACKAGES: dict = {}
for _p in CREDIT_PACKS:
    RC_CREDIT_PACKAGES[_p["apple_product_id"]]  = _p
    RC_CREDIT_PACKAGES[_p["google_product_id"]] = _p

# Default top-off for legacy/generic subscriptions that don't match a credit tier
SUB_CREDIT_CAP_DEFAULT = 10 * TOKENS_PER_CREDIT  # 400,000 tokens
