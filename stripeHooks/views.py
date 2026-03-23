import logging
import os
import stripe

from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from typing import Union

from instafitAPI.settings import env
from users.models import User as UserType
from utils import get_env
from gyms.models import TokenQuota, TokenPurchase

# ── Credit pack definitions ────────────────────────────────────────────────────
# Two purchase paths — keep these IDs in sync with gyms/views/ai.py TOKEN_PACKAGES.
#
#   Mobile path : App Store / Google Play → RevenueCat webhook → RC_CREDIT_PACKAGES
#   Web path    : Stripe Checkout         → Stripe webhook     → STRIPE_CREDIT_PACKAGES
#
# IMPORTANT: Stripe price IDs must NEVER be sent to or used by the mobile app.
# Apple will reject apps that route IAP revenue outside their payment system.

_CREDIT_PACKS = [
    {"credits": 5,  "tokens": 90_000,  "price_usd": 3.99,
     "apple_product_id": "com.liftl0g.aicredits.5",   "google_product_id": "ai_credits_5",   # placeholders
     "stripe_price_id":  "price_1TDsVQGjKlPKN3XK7wY16yQb"},
    {"credits": 15, "tokens": 270_000, "price_usd": 9.99,
     "apple_product_id": "com.liftl0g.aicredits.15",  "google_product_id": "ai_credits_15",  # placeholders
     "stripe_price_id":  "price_1TDsVQGjKlPKN3XKyGB2Vhft"},
    {"credits": 35, "tokens": 630_000, "price_usd": 19.99,
     "apple_product_id": "com.liftl0g.aicredits.35",  "google_product_id": "ai_credits_35",  # placeholders
     "stripe_price_id":  "price_1TDsVRGjKlPKN3XKDOWj1CQ8"},
]

# Mobile: keyed by store-native product ID (RC webhook sends the store's own ID)
RC_CREDIT_PACKAGES: dict = {}
for _pack in _CREDIT_PACKS:
    _entry = {"credits": _pack["credits"], "tokens": _pack["tokens"], "price_usd": _pack["price_usd"]}
    RC_CREDIT_PACKAGES[_pack["apple_product_id"]]  = _entry
    RC_CREDIT_PACKAGES[_pack["google_product_id"]] = _entry

# Web: keyed by Stripe price ID — used in checkout.session.completed webhook
STRIPE_CREDIT_PACKAGES = {
    _pack["stripe_price_id"]: {"credits": _pack["credits"], "tokens": _pack["tokens"], "price_usd": _pack["price_usd"]}
    for _pack in _CREDIT_PACKS
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
User = get_user_model()

# Stripe keys
stripe.api_key = get_env("STRIPE_API_KEY")

# Webhook signing secret
endpoint_secret = env("STRIPE_SIGNING_KEY") or os.getenv('STRIPE_SIGNING_KEY')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_user_by_customer_id(stripe_obj) -> Union[UserType, None]:
    """Look up user from a Stripe object with a .customer attribute."""
    try:
        customer_id = stripe_obj.customer
        return User.objects.get(customer_id=customer_id)
    except Exception as e:
        logger.critical(f"Failed to find user w/ customer_id={stripe_obj.customer}.", e)
    return None


def get_user_by_customer_id_str(customer_id: str) -> Union[UserType, None]:
    """Look up user directly by customer_id string."""
    try:
        return User.objects.get(customer_id=customer_id)
    except User.DoesNotExist:
        logger.warning(f"No user found for Stripe customer_id={customer_id}")
        return None
    except Exception as e:
        logger.critical(f"Error looking up user by customer_id={customer_id}: {e}")
        return None


def get_user(user_id) -> Union[UserType, None]:
    user = None
    try:
        user = User.objects.get(id=user_id)
    except Exception as err:
        print(f"Error getting user via user_id : ", err)
        logger.debug(f"Error getting user via user_id: ", err)
    return user


def get_future_datetime(dt: datetime) -> datetime:
    '''Compares the given dt to the current datetime and returns the datetime that is furthest in the future.'''
    current_dt = datetime.now().replace(tzinfo=timezone.utc)
    dt = dt.replace(tzinfo=timezone.utc)
    print(f"Comparing datetimes {current_dt=} {dt=}")
    if dt > current_dt:
        return dt
    return current_dt


def add_days(start_date: datetime, days: int) -> datetime:
    delta = timedelta(days=days)
    new_date = start_date + delta
    return new_date


def unix_to_datetime(ts: int) -> datetime:
    """Convert a Unix timestamp (from Stripe) to an aware datetime."""
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def get_or_create_stripe_customer(user) -> str:
    """
    Return a verified Stripe customer ID for the user.
    If the stored ID is missing or no longer exists in Stripe, creates a new
    customer, persists it, and returns the new ID.
    """
    if user.customer_id:
        try:
            stripe.Customer.retrieve(user.customer_id)
            return user.customer_id
        except stripe.error.InvalidRequestError:
            logger.warning(f"Stale customer_id={user.customer_id} for user={user.email}, recreating.")

    customer = stripe.Customer.create(email=user.email)
    user.customer_id = customer.id
    user.save(update_fields=["customer_id"])
    logger.info(f"Created new Stripe customer {customer.id} for user={user.email}")
    return customer.id


# ─── ViewSet ──────────────────────────────────────────────────────────────────

class HookViewSet(viewsets.ViewSet):
    '''
    Stripe and RevenueCat webhook handlers + checkout/portal endpoints.

    Routes:
      POST /hooks/create-checkout/   — Create a Stripe Checkout Session
      POST /hooks/customer-portal/   — Get Stripe Customer Portal URL
      GET  /hooks/session-status/    — Check checkout session result
      POST /hooks/webhook/           — Stripe webhook events
      POST /hooks/revenuecat/        — RevenueCat webhook events
    '''

    # ── POST /hooks/create-checkout/ ─────────────────────────────────────────

    @action(detail=False, methods=['POST'], permission_classes=[])
    def create_checkout(self, request, pk=None):
        """
        Create a Stripe Checkout Session.

        Body params:
          price_id    — Stripe price ID (defaults to STRIPE_PRICE_ID / Plus plan)
          success_url — redirect on success (required)
          cancel_url  — redirect on cancel (required)
          email       — pre-fill checkout email (optional)
          mode        — "subscription" or "payment" (auto-detected from price if omitted)
        """
        price_id    = request.data.get("price_id") or settings.STRIPE_PRICE_ID
        success_url = request.data.get("success_url", "").strip()
        cancel_url  = request.data.get("cancel_url", "").strip()
        email       = request.data.get("email", "").strip().lower()
        mode        = request.data.get("mode", "").strip()

        if not success_url or not cancel_url:
            return JsonResponse(
                {"detail": "success_url and cancel_url are required."},
                status=400,
            )

        # Auto-detect mode: Pro Plan is a one-time payment, everything else is subscription
        if not mode:
            mode = "payment" if price_id == settings.STRIPE_PRICE_ID_PRO else "subscription"

        # Link checkout to the user's verified Stripe customer
        customer_id = None
        if email:
            try:
                user = User.objects.get(email__iexact=email)
                customer_id = get_or_create_stripe_customer(user)
            except User.DoesNotExist:
                pass

        try:
            params = {
                "mode": mode,
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": cancel_url,
                "metadata": {"source": "reptrackrr-web", "price_id": price_id},
            }
            if mode == "subscription":
                params["allow_promotion_codes"] = True

            if customer_id:
                params["customer"] = customer_id
            elif email:
                params["customer_email"] = email

            session = stripe.checkout.Session.create(**params)
            print(f"Created checkout session: {session.id} mode={mode} price={price_id}")
            return JsonResponse({"session_id": session.id, "url": session.url}, status=201)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            return JsonResponse({"detail": str(e)}, status=400)
        except Exception as err:
            logger.error(f"Error creating checkout session: {err}")
            return JsonResponse({"detail": "Internal error."}, status=500)

    # ── POST /hooks/customer-portal/ ─────────────────────────────────────────

    @action(detail=False, methods=['POST'], permission_classes=[])
    def customer_portal(self, request, pk=None):
        """
        Generate a Stripe Customer Portal URL.

        Body params:
          email — account email (required)
        """
        email = request.data.get("email", "").strip().lower()

        if not email:
            return JsonResponse({"detail": "Email is required."}, status=400)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return JsonResponse(
                    {"detail": "No active subscription found for that email address."},
                    status=404,
                )

        try:
            customer_id = get_or_create_stripe_customer(user)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error ensuring customer for user={user.email}: {e}")
            return JsonResponse({"detail": "Failed to locate Stripe account."}, status=400)

        return_url = request.data.get("return_url", "").strip() or settings.BASE_URL

        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            print(f"Created portal session for customer={customer_id}")
            return JsonResponse({"url": portal_session.url})
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal session: {e}")
            return JsonResponse({"detail": str(e)}, status=400)

    # ── GET /hooks/session-status/ ────────────────────────────────────────────

    @action(detail=False, methods=['GET'], permission_classes=[])
    def session_status(self, request, pk=None):
        """
        Check the status of a Checkout Session (called from /success page).

        Query params:
          session_id — Stripe session ID from success URL
        """
        session_id = request.query_params.get("session_id", "").strip()

        if not session_id:
            return JsonResponse({"detail": "session_id is required."}, status=400)

        try:
            session = stripe.checkout.Session.retrieve(
                session_id,
                expand=["subscription", "customer"],
            )
        except stripe.error.InvalidRequestError:
            return JsonResponse({"detail": "Session not found."}, status=404)
        except stripe.error.StripeError as e:
            return JsonResponse({"detail": str(e)}, status=400)

        customer_email = None
        if session.customer_details:
            customer_email = session.customer_details.get("email")

        return JsonResponse({
            "status": session.status,
            "customer_email": customer_email,
            "payment_status": session.payment_status,
        })

    # ── POST /hooks/revenuecat/ ───────────────────────────────────────────────

    @action(detail=False, methods=['POST'], permission_classes=[])
    def revenuecat(self, request, pk=None):
        # I am not supporting refunds or cancellation
        # If a user cancels a sub, they will remain subbed until exp-date
        try:
            event = request.data.get("event")
            print(f"Raw event: {event=}")

            if event is None:
                resp = JsonResponse({})
                resp.status_code = 500
                print(f"Could not get data from request: ", request.data)
                return resp

            event_type = event.get("type")  # RENEWAL, EXPIRATION, CANCELLATION, NON_SUBSCRIPTION_PURCHASE, …
            app_user_id = event.get("app_user_id")
            subscriber_attributes = event.get("subscriber_attributes") or {}
            user_id_attr = subscriber_attributes.get("userID") or {}
            user_id = user_id_attr.get("value")

            print(f"User requested subbed: {event_type=}, {user_id=}")
            logger.debug(f"User requested subbed: {user_id=}")

            if event_type == "RENEWAL" or event_type == "INITIAL_PURCHASE":
                exp_date = event.get("expiration_at_ms")
                user = get_user(user_id)
                if user:
                    print(f"User subbed: {user_id=}, {exp_date=}, ")
                    user.sub_end_date = datetime.fromtimestamp(exp_date // 1000)
                    user.save()
                else:
                    msg = f"Error getting user to update sub: {app_user_id=}, {user_id=}, {exp_date=}, "
                    logger.debug(msg)
                    print(msg)

            elif event_type == "NON_SUBSCRIPTION_PURCHASE":
                # Consumable credit pack purchased via App Store / Google Play.
                product_id      = event.get("product_id", "")
                transaction_ref = event.get("transaction_id", "")
                store           = event.get("store", "")
                method          = TokenPurchase.APPLE if store == "APP_STORE" else TokenPurchase.GOOGLE

                package = RC_CREDIT_PACKAGES.get(product_id)
                print(f"NON_SUBSCRIPTION_PURCHASE: {product_id=} {transaction_ref=} {store=} {user_id=}")

                if not package:
                    print(f"Unknown credit product_id={product_id!r} — ignoring")
                elif not user_id:
                    print(f"No user_id in subscriber_attributes for credit purchase {transaction_ref=}")
                elif transaction_ref and TokenPurchase.objects.filter(transaction_ref=transaction_ref).exists():
                    print(f"Duplicate credit purchase skipped: {transaction_ref=}")
                else:
                    quota, _ = TokenQuota.objects.get_or_create(user_id=user_id)
                    quota.add_tokens(package["tokens"])
                    TokenPurchase.objects.create(
                        user_id=user_id,
                        package_id=product_id,
                        tokens_added=package["tokens"],
                        price_paid_usd=package["price_usd"],
                        method=method,
                        transaction_ref=transaction_ref,
                    )
                    print(f"Credited {package['tokens']} tokens ({package['credits']} credits) to user={user_id}")

        except Exception as err:
            print(f"Error RevenueCat web hook: {err=}")

        return JsonResponse({"success": True})

    # ── POST /hooks/webhook/ ──────────────────────────────────────────────────

    @action(detail=False, methods=['POST'], permission_classes=[])
    def webhook(self, request, pk=None):
        print(f"webhook called...")
        try:
            payload = request.body.decode('utf-8')
            event = None
            user = None

            if endpoint_secret:
                sig_header = request.headers.get('stripe-signature')
                try:
                    event = stripe.Webhook.construct_event(
                        payload, sig_header, endpoint_secret
                    )
                except stripe.error.SignatureVerificationError as e:
                    print('⚠️  Webhook signature verification failed.' + str(e))
                    return JsonResponse({"success": False}, status=400)
            else:
                # No signing secret — parse without verification.
                # Fine for local dev; set STRIPE_SIGNING_KEY in production.
                import json
                logger.warning("STRIPE_SIGNING_KEY not set — skipping webhook signature verification.")
                event = stripe.Event.construct_from(
                    json.loads(payload), stripe.api_key
                )

            if not event:
                logger.error("Webhook: failed to construct event from payload.")
                return JsonResponse({"success": False}, status=400)

            event_type = event['type']
            event_data = event['data']['object']
            print(f"Webhook event type: {event_type}")

            # ── checkout.session.completed ────────────────────────────────────
            if event_type == 'checkout.session.completed':
                try:
                    session = event_data
                    customer_id = session.get('customer')
                    customer_email = (
                        session.get('customer_email') or
                        (session.get('customer_details') or {}).get('email')
                    )
                    subscription_id = session.get('subscription')

                    print(f"checkout.session.completed: {customer_id=} {customer_email=} {subscription_id=}")

                    # Find user by customer_id, then fall back to email
                    user = None
                    if customer_id:
                        user = get_user_by_customer_id_str(customer_id)
                    if user is None and customer_email:
                        try:
                            user = User.objects.get(email__iexact=customer_email)
                        except User.DoesNotExist:
                            pass

                    if user is None:
                        print(f"No user found for completed checkout. {customer_id=} {customer_email=}")
                    else:
                        # Always sync customer_id — checkout may use a newer customer
                        if customer_id and user.customer_id != customer_id:
                            user.customer_id = customer_id
                            user.save(update_fields=["customer_id"])
                            print(f"Updated customer_id={customer_id} for user={user.email}")

                        session_mode = session.get('mode')

                        if session_mode == 'payment':
                            # One-time purchase — check if it's a credit pack
                            price_id    = (session.get('metadata') or {}).get('price_id', '')
                            session_id  = session.get('id', '')
                            credit_pack = STRIPE_CREDIT_PACKAGES.get(price_id)
                            if credit_pack:
                                if session_id and TokenPurchase.objects.filter(transaction_ref=session_id).exists():
                                    print(f"Duplicate Stripe credit purchase skipped: {session_id=}")
                                else:
                                    quota, _ = TokenQuota.objects.get_or_create(user_id=str(user.id))
                                    quota.add_tokens(credit_pack["tokens"])
                                    TokenPurchase.objects.create(
                                        user_id=str(user.id),
                                        package_id=price_id,
                                        tokens_added=credit_pack["tokens"],
                                        price_paid_usd=credit_pack["price_usd"],
                                        method=TokenPurchase.STRIPE,
                                        transaction_ref=session_id,
                                    )
                                    print(f"Credited {credit_pack['tokens']} tokens ({credit_pack['credits']} credits) "
                                          f"via Stripe to user={user.email}")
                            else:
                                print(f"One-time checkout completed but no credit pack matched price_id={price_id!r}")

                        elif session_mode == 'subscription':
                            # Subscription checkout — set sub_end_date
                            if subscription_id:
                                try:
                                    sub = stripe.Subscription.retrieve(subscription_id)
                                    period_end = sub.get('current_period_end')
                                    if period_end:
                                        user.sub_end_date = unix_to_datetime(period_end)
                                        user.save()
                                        print(f"Set sub_end_date for user={user.email} until {user.sub_end_date}")
                                except Exception as sub_err:
                                    print(f"Error retrieving subscription: {sub_err}")
                except Exception as err:
                    print(f"Error with checkout.session.completed: {err}")

            # ── charge.succeeded ──────────────────────────────────────────────
            elif event_type == 'charge.succeeded':
                try:
                    charge = event_data
                    user = get_user_by_customer_id(charge)
                    if not user:
                        print(f"User not found, user is None.")
                        return JsonResponse({"success": False})
                    print('Payment for {} succeeded at amt {}'.format(user, charge['amount']))
                    print(f"{charge=}")

                    if 'duration' in charge['metadata']:
                        days_to_add: int = int(charge['metadata']['duration'])
                        print(f"Adding {days_to_add} of days to user: {user.email}")
                        user.sub_end_date = add_days(get_future_datetime(user.sub_end_date), days_to_add)
                        user.save()
                except Exception as err:
                    print(f"Error with charge event webhook: ", err)
                    return JsonResponse({"success": False})

            # ── invoice.paid ──────────────────────────────────────────────────
            elif event_type == 'invoice.paid':
                invoice = event_data
                print(f"Invoice event: ", invoice)
                user = get_user_by_customer_id(invoice)
                sub_start = invoice['lines']['data'][0]['period']['start']
                sub_end = invoice['lines']['data'][0]['period']['end']
                if not user:
                    print(f"User not found, user is None.")
                    return JsonResponse({"success": False})
                user.sub_end_date = datetime.fromtimestamp(sub_end)
                user.save()

            # ── invoice.payment_failed ────────────────────────────────────────
            elif event_type == 'invoice.payment_failed':
                try:
                    invoice = event_data
                    customer_id = invoice.get('customer')
                    if customer_id:
                        user = get_user_by_customer_id_str(customer_id)
                        if user:
                            print(f"Payment failed for user={user.email} — no access change yet (grace period)")
                            # We don't expire immediately — Stripe will retry
                            # and send customer.subscription.deleted when truly over
                except Exception as err:
                    print(f"Error with invoice.payment_failed: {err}")

            # ── customer.subscription.updated ─────────────────────────────────
            elif event_type == 'customer.subscription.updated':
                try:
                    subscription = event_data
                    customer_id = subscription.get('customer')
                    period_end = subscription.get('current_period_end')
                    sub_status = subscription.get('status', '')
                    print(f"Subscription updated: {customer_id=} {sub_status=} period_end={period_end}")

                    if customer_id:
                        user = get_user_by_customer_id_str(customer_id)
                        if user and period_end:
                            user.sub_end_date = unix_to_datetime(period_end)
                            user.save()
                            print(f"Updated sub_end_date for user={user.email} until {user.sub_end_date}")
                except Exception as err:
                    print(f"Error with customer.subscription.updated: {err}")

            # ── customer.subscription.deleted ─────────────────────────────────
            elif event_type == 'customer.subscription.deleted':
                try:
                    subscription = event_data
                    customer_id = subscription.get('customer')
                    print(f"Subscription deleted: {customer_id=}")

                    if customer_id:
                        user = get_user_by_customer_id_str(customer_id)
                        if user:
                            # Expire immediately — subscription is fully cancelled
                            user.sub_end_date = datetime.now(tz=timezone.utc) - timedelta(days=1)
                            user.save()
                            print(f"Expired subscription for user={user.email}")
                except Exception as err:
                    print(f"Error with customer.subscription.deleted: {err}")

            else:
                print('Unhandled event type {}'.format(event_type))

            return JsonResponse({"success": True})

        except Exception as err:
            print(f"Webhook error: ", err)
        return JsonResponse({"success": False})
