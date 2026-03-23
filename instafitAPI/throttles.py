"""
Custom DRF throttle classes for sensitive public endpoints.

Rates are configured in settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].
All throttles key on IP address (AnonRateThrottle base), so they work
without requiring the user to be authenticated.

NOTE: DRF throttling uses Django's cache backend. Currently LocMemCache
(per-process). If gunicorn runs multiple workers, limits are per-worker.
Upgrade to a shared Redis cache to enforce limits across all workers:

    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": "redis://127.0.0.1:6379/1",
        }
    }
    pip install django[redis]
"""

from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    POST /token/ — sign-in endpoint.
    Limits credential attempts per IP to block brute-force / credential stuffing.
    Rate: settings -> 'login'
    """
    scope = "login"


class PasswordResetSendThrottle(AnonRateThrottle):
    """
    POST /user/send_reset_code/ — triggers a reset email.
    Tight hourly cap to prevent email spam and Sendinblue quota drain.
    Rate: settings -> 'password_reset_send'
    """
    scope = "password_reset_send"


class PasswordResetSubmitThrottle(AnonRateThrottle):
    """
    POST /user/reset_password/ — submits the reset code + new password.
    Limits code-guessing attempts.
    Rate: settings -> 'password_reset_submit'
    """
    scope = "password_reset_submit"


class UserCreateThrottle(AnonRateThrottle):
    """
    POST /users/ — account registration.
    Prevents bulk account creation / Stripe customer spam.
    Rate: settings -> 'user_create'
    """
    scope = "user_create"
