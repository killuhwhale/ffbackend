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
from gyms.credit_packs import RC_CREDIT_PACKAGES, STRIPE_CREDIT_PACKAGES, SUB_CREDIT_CAP_DEFAULT

logger = logging.getLogger(__name__)
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
        logger.debug("Error getting user via user_id=%s: %s", user_id, err)
    return user


def revenuecat_user_ids(values) -> list:
    """Extract app user ids from RevenueCat alias lists, excluding anonymous ids."""
    user_ids = []
    for value in values or []:
        value = str(value)
        if value and not value.startswith("$RCAnonymousID:"):
            user_ids.append(value)
    return user_ids


def move_revenuecat_subscription_state(source_user_ids, destination_user_ids) -> None:
    """Move credits/purchase history after RevenueCat transfers an Apple/Google subscription."""
    for source_user_id in revenuecat_user_ids(source_user_ids):
        for destination_user_id in revenuecat_user_ids(destination_user_ids):
            if source_user_id == destination_user_id:
                continue

            source_quota = TokenQuota.objects.filter(user_id=source_user_id).first()
            destination_quota, _ = TokenQuota.objects.get_or_create(user_id=destination_user_id)

            if source_quota:
                destination_quota.remaining_tokens = max(
                    destination_quota.remaining_tokens,
                    source_quota.remaining_tokens,
                )
                destination_quota.reset_at = max(destination_quota.reset_at, source_quota.reset_at)
                destination_quota.save()
                source_quota.delete()

            TokenPurchase.objects.filter(user_id=source_user_id).update(user_id=destination_user_id)
            logger.info("[RevenueCat] Transferred subscription state source_user_id=%s destination_user_id=%s", source_user_id, destination_user_id)


def get_future_datetime(dt: datetime) -> datetime:
    '''Compares the given dt to the current datetime and returns the datetime that is furthest in the future.'''
    current_dt = datetime.now().replace(tzinfo=timezone.utc)
    dt = dt.replace(tzinfo=timezone.utc)
    logger.debug("Comparing datetimes current_dt=%s dt=%s", current_dt, dt)
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

    @action(detail=False, methods=['POST'], permission_classes=[], url_path=r'create[-_]checkout')
    def create_checkout(self, request, pk=None):
        """
        Create a Stripe Checkout Session.

        Body params:
          price_id    — Stripe price ID (defaults to STRIPE_PRICE_ID / No-Ads plan)
          success_url — redirect on success (required)
          cancel_url  — redirect on cancel (required)
          email       — pre-fill checkout email (optional)
        """
        price_id    = request.data.get("price_id") or settings.STRIPE_PRICE_ID
        success_url = request.data.get("success_url", "").strip()
        cancel_url  = request.data.get("cancel_url", "").strip()
        email       = request.data.get("email", "").strip().lower()

        if not success_url or not cancel_url:
            return JsonResponse(
                {"detail": "success_url and cancel_url are required."},
                status=400,
            )

        mode = "subscription"

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
            params["allow_promotion_codes"] = True

            if customer_id:
                params["customer"] = customer_id
            elif email:
                params["customer_email"] = email

            session = stripe.checkout.Session.create(**params)
            logger.info("Created checkout session id=%s mode=%s price=%s", session.id, mode, price_id)
            return JsonResponse({"session_id": session.id, "url": session.url}, status=201)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            return JsonResponse({"detail": str(e)}, status=400)
        except Exception as err:
            logger.error(f"Error creating checkout session: {err}")
            return JsonResponse({"detail": "Internal error."}, status=500)

    # ── POST /hooks/customer-portal/ ─────────────────────────────────────────

    @action(detail=False, methods=['POST'], permission_classes=[], url_path=r'customer[-_]portal')
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
            logger.info("Created portal session for customer=%s", customer_id)
            return JsonResponse({"url": portal_session.url})
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal session: {e}")
            return JsonResponse({"detail": str(e)}, status=400)

    # ── GET /hooks/session-status/ ────────────────────────────────────────────

    @action(detail=False, methods=['GET'], permission_classes=[], url_path=r'session[-_]status')
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
            logger.debug("[RevenueCat] Raw event=%r", event)

            if event is None:
                resp = JsonResponse({})
                resp.status_code = 500
                logger.warning("[RevenueCat] Could not get event from request data keys=%s", list(request.data.keys()))
                return resp

            event_type = event.get("type")
            app_user_id = event.get("app_user_id")
            subscriber_attributes = event.get("subscriber_attributes") or {}
            user_id_attr = subscriber_attributes.get("userID") or {}
            user_id = user_id_attr.get("value")
            product_id = event.get("product_id", "")
            store = event.get("store", "")
            environment = event.get("environment", "")

            logger.info(
                "[RevenueCat] event_type=%s user_id=%s app_user_id=%s product_id=%s store=%s environment=%s",
                event_type, user_id, app_user_id, product_id, store, environment,
            )

            # ── Subscription purchase / renewal ─────────────────────────────
            if event_type in ("INITIAL_PURCHASE", "RENEWAL"):
                exp_date = event.get("expiration_at_ms")
                is_trial = event.get("is_trial_conversion", False)
                period_type = event.get("period_type", "")
                logger.info("[RevenueCat] Sub event event_type=%s period_type=%s is_trial=%s product_id=%s", event_type, period_type, is_trial, product_id)

                user = get_user(user_id)
                if user and exp_date:
                    logger.info("[RevenueCat] User subbed user_id=%s exp_date=%s", user_id, exp_date)
                    user.sub_end_date = datetime.fromtimestamp(exp_date // 1000, tz=timezone.utc)
                    user.save()
                elif user and not exp_date:
                    # Sandbox/test purchases may not have an expiration — grant 30 days
                    logger.info("[RevenueCat] User subbed with no exp_date, granting 30d user_id=%s", user_id)
                    user.sub_end_date = datetime.now(tz=timezone.utc) + timedelta(days=30)
                    user.save()
                else:
                    msg = f"[RevenueCat] Error getting user to update sub: {app_user_id=}, {user_id=}, {exp_date=}"
                    logger.warning(msg)

                # Hard-reset subscriber credits to the subscribed tier.
                # We RESET (not top-off) so that:
                #   - Downgrades work (15-credit → 5-credit actually reduces)
                #   - Renewals reset the full monthly allowance
                #   - No rollover from previous billing cycles
                if user_id:
                    package = RC_CREDIT_PACKAGES.get(product_id)
                    quota, _ = TokenQuota.objects.get_or_create(user_id=user_id)

                    if package:
                        quota.remaining_tokens = package["tokens"]
                    else:
                        quota.top_off_tokens(SUB_CREDIT_CAP_DEFAULT)

                    # Set reset_at to the next billing date so the UI shows
                    # when credits will refresh.
                    if exp_date:
                        quota.reset_at = datetime.fromtimestamp(exp_date // 1000, tz=timezone.utc)
                    else:
                        quota.reset_at = datetime.now(tz=timezone.utc) + timedelta(days=30)
                    quota.save()

                    # Record the purchase for analytics using RC's reported price
                    # (RC's `price` field is normalized to USD).
                    if package:
                        transaction_ref = event.get("transaction_id", "")
                        rc_price_usd = event.get("price")
                        method = TokenPurchase.GOOGLE if store == "PLAY_STORE" else TokenPurchase.APPLE

                        already_recorded = (
                            transaction_ref
                            and TokenPurchase.objects.filter(transaction_ref=transaction_ref).exists()
                        )
                        if already_recorded:
                            logger.info("[RevenueCat] Duplicate sub purchase skipped transaction_ref=%s", transaction_ref)
                        else:
                            TokenPurchase.objects.create(
                                user_id=user_id,
                                package_id=product_id,
                                tokens_added=package["tokens"],
                                price_paid_usd=rc_price_usd if rc_price_usd is not None else 0,
                                method=method,
                                transaction_ref=transaction_ref,
                            )
                            logger.info("[RevenueCat] Recorded %s transaction_ref=%s price_usd=%s product_id=%s", event_type, transaction_ref, rc_price_usd, product_id)

                        logger.info("[RevenueCat] Reset to %s credits tier=%s user_id=%s remaining=%s", package['credits'], product_id, user_id, quota.remaining_tokens)
                    else:
                        logger.warning("[RevenueCat] Unknown sub product_id=%r applied default top-off remaining=%s", product_id, quota.remaining_tokens)

            # ── Consumable credit pack ──────────────────────────────────────
            elif event_type == "NON_RENEWING_PURCHASE":
                transaction_ref = event.get("transaction_id", "")
                method = TokenPurchase.GOOGLE if store == "PLAY_STORE" else TokenPurchase.APPLE

                package = RC_CREDIT_PACKAGES.get(product_id)
                logger.info("[RevenueCat] NON_RENEWING_PURCHASE product_id=%s transaction_ref=%s store=%s user_id=%s", product_id, transaction_ref, store, user_id)

                if not package:
                    logger.warning("[RevenueCat] Unknown credit product_id=%r ignoring", product_id)
                elif not user_id:
                    logger.warning("[RevenueCat] No user_id in subscriber_attributes for credit purchase transaction_ref=%s", transaction_ref)
                elif transaction_ref and TokenPurchase.objects.filter(transaction_ref=transaction_ref).exists():
                    logger.info("[RevenueCat] Duplicate credit purchase skipped transaction_ref=%s", transaction_ref)
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
                    logger.info("[RevenueCat] Credited %s tokens (%s credits) to user=%s", package['tokens'], package['credits'], user_id)

            # ── Cancellation ────────────────────────────────────────────────
            elif event_type == "CANCELLATION":
                cancel_reason = event.get("cancel_reason", "UNKNOWN")
                exp_date = event.get("expiration_at_ms")
                logger.info("[RevenueCat] CANCELLATION user_id=%s cancel_reason=%s exp_date=%s product_id=%s", user_id, cancel_reason, exp_date, product_id)

                # Ensure sub_end_date reflects the expiration so access stops at the right time
                user = get_user(user_id)
                if user and exp_date:
                    user.sub_end_date = datetime.fromtimestamp(exp_date // 1000, tz=timezone.utc)
                    user.save()
                    logger.info("[RevenueCat] Set sub_end_date to expiration for user_id=%s sub_end_date=%s", user_id, user.sub_end_date)

            # ── Uncancellation (user re-enabled auto-renew) ─────────────────
            elif event_type == "UNCANCELLATION":
                exp_date = event.get("expiration_at_ms")
                logger.info("[RevenueCat] UNCANCELLATION user_id=%s exp_date=%s product_id=%s", user_id, exp_date, product_id)

                # User re-enabled auto-renew — restore subscription access and credits.
                user = get_user(user_id)
                if user:
                    if exp_date:
                        reset_at = datetime.fromtimestamp(exp_date // 1000, tz=timezone.utc)
                    else:
                        reset_at = datetime.now(tz=timezone.utc) + timedelta(days=30)

                    user.sub_end_date = reset_at
                    user.save()
                    logger.info("[RevenueCat] Updated sub_end_date for user_id=%s sub_end_date=%s", user_id, user.sub_end_date)
                else:
                    msg = f"[RevenueCat] Error getting user to uncancel sub: {app_user_id=}, {user_id=}, {exp_date=}"
                    logger.warning(msg)

                if user_id:
                    package = RC_CREDIT_PACKAGES.get(product_id)
                    quota, _ = TokenQuota.objects.get_or_create(user_id=user_id)

                    if package:
                        quota.remaining_tokens = package["tokens"]
                    else:
                        quota.top_off_tokens(SUB_CREDIT_CAP_DEFAULT)

                    if exp_date:
                        quota.reset_at = datetime.fromtimestamp(exp_date // 1000, tz=timezone.utc)
                    else:
                        quota.reset_at = datetime.now(tz=timezone.utc) + timedelta(days=30)
                    quota.save()

                    tier = f"{package['credits']} credits" if package else "default"
                    logger.info("[RevenueCat] UNCANCELLATION reset tier=%s user_id=%s remaining=%s reset_at=%s", tier, user_id, quota.remaining_tokens, quota.reset_at)

            # ── Expiration ──────────────────────────────────────────────────
            elif event_type == "EXPIRATION":
                expiration_reason = event.get("expiration_reason", "UNKNOWN")
                exp_date = event.get("expiration_at_ms")
                logger.info("[RevenueCat] EXPIRATION user_id=%s expiration_reason=%s exp_date=%s product_id=%s", user_id, expiration_reason, exp_date, product_id)

                # Sub expired — revoke access and zero out subscription credits
                user = get_user(user_id)
                if user:
                    user.sub_end_date = datetime.now(tz=timezone.utc)
                    user.save()
                    logger.info("[RevenueCat] Expired sub for user_id=%s", user_id)

                if user_id:
                    quota, _ = TokenQuota.objects.get_or_create(user_id=user_id)
                    prev = quota.remaining_tokens
                    quota.remaining_tokens = 0
                    quota.save()
                    logger.info("[RevenueCat] Zeroed credits for user_id=%s previous=%s", user_id, prev)

            # ── Billing issue ───────────────────────────────────────────────
            elif event_type == "BILLING_ISSUE":
                grace_period_exp = event.get("grace_period_expiration_at_ms")
                logger.warning("[RevenueCat] BILLING_ISSUE user_id=%s grace_period_exp=%s product_id=%s", user_id, grace_period_exp, product_id)

            # ── Product change (upgrade/downgrade) ──────────────────────────
            elif event_type == "PRODUCT_CHANGE":
                new_product_id = event.get("new_product_id", "")
                logger.info("[RevenueCat] PRODUCT_CHANGE user_id=%s product_id=%s new_product_id=%s", user_id, product_id, new_product_id)

            # ── Subscription paused (Android only) ──────────────────────────
            elif event_type == "SUBSCRIPTION_PAUSED":
                auto_resume_at = event.get("auto_resume_at_ms")
                logger.info("[RevenueCat] SUBSCRIPTION_PAUSED user_id=%s auto_resume_at=%s product_id=%s", user_id, auto_resume_at, product_id)

            # ── Subscription extended ───────────────────────────────────────
            elif event_type == "SUBSCRIPTION_EXTENDED":
                exp_date = event.get("expiration_at_ms")
                logger.info("[RevenueCat] SUBSCRIPTION_EXTENDED user_id=%s exp_date=%s product_id=%s", user_id, exp_date, product_id)

                user = get_user(user_id)
                if user and exp_date:
                    user.sub_end_date = datetime.fromtimestamp(exp_date // 1000, tz=timezone.utc)
                    user.save()
                    logger.info("[RevenueCat] Extended sub for user_id=%s sub_end_date=%s", user_id, user.sub_end_date)

            # ── Transfer ────────────────────────────────────────────────────
            elif event_type == "TRANSFER":
                transferred_from = event.get("transferred_from", [])
                transferred_to = event.get("transferred_to", [])
                logger.info("[RevenueCat] TRANSFER transferred_from=%s transferred_to=%s", transferred_from, transferred_to)
                move_revenuecat_subscription_state(transferred_from, transferred_to)

            # ── Refund reversed ─────────────────────────────────────────────
            elif event_type == "REFUND_REVERSED":
                logger.info("[RevenueCat] REFUND_REVERSED user_id=%s product_id=%s", user_id, product_id)

            # ── Temporary entitlement grant ─────────────────────────────────
            elif event_type == "TEMPORARY_ENTITLEMENT_GRANT":
                exp_date = event.get("expiration_at_ms")
                entitlements = event.get("entitlement_ids", [])
                logger.info("[RevenueCat] TEMPORARY_ENTITLEMENT_GRANT user_id=%s entitlements=%s exp_date=%s", user_id, entitlements, exp_date)

            # ── Invoice issuance ────────────────────────────────────────────
            elif event_type == "INVOICE_ISSUANCE":
                logger.info("[RevenueCat] INVOICE_ISSUANCE user_id=%s product_id=%s", user_id, product_id)

            # ── Experiment enrollment ───────────────────────────────────────
            elif event_type == "EXPERIMENT_ENROLLMENT":
                experiment_id = event.get("experiment_id", "")
                experiment_variant = event.get("experiment_variant", "")
                logger.info("[RevenueCat] EXPERIMENT_ENROLLMENT user_id=%s experiment_id=%s experiment_variant=%s", user_id, experiment_id, experiment_variant)

            # ── Test event ──────────────────────────────────────────────────
            elif event_type == "TEST":
                logger.info("[RevenueCat] TEST event received")

            # ── Unknown / unhandled ─────────────────────────────────────────
            else:
                logger.warning("[RevenueCat] Unhandled event type=%s", event_type)
                logger.debug("[RevenueCat] Unhandled event=%r", event)

        except Exception as err:
            logger.exception("[RevenueCat] Error processing webhook")

        return JsonResponse({"success": True})

    # ── POST /hooks/webhook/ ──────────────────────────────────────────────────

    @action(detail=False, methods=['POST'], permission_classes=[])
    def webhook(self, request, pk=None):
        logger.debug("Stripe webhook called")
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
                    logger.warning("Webhook signature verification failed: %s", e)
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
            logger.info("Webhook event type=%s", event_type)

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

                    logger.info("checkout.session.completed customer_id=%s customer_email=%s subscription_id=%s", customer_id, customer_email, subscription_id)

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
                        logger.warning("No user found for completed checkout customer_id=%s customer_email=%s", customer_id, customer_email)
                    else:
                        # Always sync customer_id — checkout may use a newer customer
                        if customer_id and user.customer_id != customer_id:
                            user.customer_id = customer_id
                            user.save(update_fields=["customer_id"])
                            logger.info("Updated customer_id=%s for user_id=%s", customer_id, user.id)

                        # All plans are subscriptions — set sub_end_date and credit pack if applicable
                        if subscription_id:
                            try:
                                sub = stripe.Subscription.retrieve(subscription_id)
                                period_end = sub.get('current_period_end')
                                if period_end:
                                    user.sub_end_date = unix_to_datetime(period_end)
                                    user.save()
                                    logger.info("Set sub_end_date for user_id=%s until %s", user.id, user.sub_end_date)

                                price_id = (session.get('metadata') or {}).get('price_id', '')
                                session_id = session.get('id', '')
                                credit_pack = STRIPE_CREDIT_PACKAGES.get(price_id)
                                quota, _ = TokenQuota.objects.get_or_create(user_id=str(user.id))

                                if credit_pack:
                                    if session_id and TokenPurchase.objects.filter(transaction_ref=session_id).exists():
                                        logger.info("Duplicate Stripe sub purchase skipped session_id=%s", session_id)
                                    else:
                                        quota.add_tokens(credit_pack["tokens"])
                                        amount_minor = session.get('amount_total') or 0
                                        price_paid = (amount_minor / 100.0) if amount_minor else 0
                                        TokenPurchase.objects.create(
                                            user_id=str(user.id),
                                            package_id=price_id,
                                            tokens_added=credit_pack["tokens"],
                                            price_paid_usd=price_paid,
                                            method=TokenPurchase.STRIPE,
                                            transaction_ref=session_id,
                                        )
                                        logger.info("Credited %s tokens (%s credits) via Stripe sub to user_id=%s price_paid=%s", credit_pack['tokens'], credit_pack['credits'], user.id, price_paid)

                                if period_end:
                                    quota.reset_at = unix_to_datetime(period_end)
                                quota.save()
                                tier = f"{credit_pack['credits']} credits" if credit_pack else "no-ads"
                                logger.info("Checkout complete tier=%s user_id=%s remaining=%s", tier, user.id, quota.remaining_tokens)
                            except Exception as sub_err:
                                logger.exception("Error retrieving subscription")
                except Exception as err:
                    logger.exception("Error with checkout.session.completed")

            # ── charge.succeeded ──────────────────────────────────────────────
            elif event_type == 'charge.succeeded':
                try:
                    charge = event_data
                    user = get_user_by_customer_id(charge)
                    if not user:
                        logger.warning("User not found for charge.succeeded")
                        return JsonResponse({"success": False})
                    logger.info("Payment for user_id=%s succeeded amount=%s", user.id, charge['amount'])
                    logger.debug("Stripe charge=%r", charge)

                    if 'duration' in charge['metadata']:
                        days_to_add: int = int(charge['metadata']['duration'])
                        logger.info("Adding subscription days user_id=%s days=%s", user.id, days_to_add)
                        user.sub_end_date = add_days(get_future_datetime(user.sub_end_date), days_to_add)
                        user.save()
                except Exception as err:
                    logger.exception("Error with charge event webhook")
                    return JsonResponse({"success": False})

            # ── invoice.paid ──────────────────────────────────────────────────
            elif event_type == 'invoice.paid':
                invoice = event_data
                logger.debug("Invoice event=%r", invoice)
                user = get_user_by_customer_id(invoice)
                if not user:
                    logger.warning("User not found for invoice.paid")
                    return JsonResponse({"success": False})

                lines = (invoice.get('lines') or {}).get('data') or []
                first_line = lines[0] if lines else {}

                sub_end = first_line.get('period', {}).get('end')
                if sub_end:
                    user.sub_end_date = datetime.fromtimestamp(sub_end, tz=timezone.utc)
                    user.save()

                billing_reason = invoice.get('billing_reason', '')
                # New Stripe API: pricing.price_details.price; fall back to old price.id
                pricing = first_line.get('pricing') or {}
                price_id = (
                    (pricing.get('price_details') or {}).get('price', '')
                    or (first_line.get('price') or {}).get('id', '')
                )
                credit_pack = STRIPE_CREDIT_PACKAGES.get(price_id)
                logger.info("[invoice.paid] billing_reason=%s price_id=%s credit_pack=%s", billing_reason, price_id, credit_pack is not None)

                if credit_pack and billing_reason in ('subscription_create', 'subscription_cycle'):
                    invoice_id = invoice.get('id', '')
                    if invoice_id and TokenPurchase.objects.filter(transaction_ref=invoice_id).exists():
                        logger.info("[invoice.paid] Duplicate skipped invoice_id=%s", invoice_id)
                    else:
                        quota, _ = TokenQuota.objects.get_or_create(user_id=str(user.id))
                        if billing_reason == 'subscription_cycle':
                            # Renewal: reset to tier (no rollover)
                            quota.remaining_tokens = credit_pack["tokens"]
                        else:
                            # Initial purchase: add tokens
                            quota.add_tokens(credit_pack["tokens"])
                        if sub_end:
                            quota.reset_at = datetime.fromtimestamp(sub_end, tz=timezone.utc)
                        quota.save()

                        amount_minor = invoice.get('amount_paid') or 0
                        price_paid = (amount_minor / 100.0) if amount_minor else 0
                        TokenPurchase.objects.create(
                            user_id=str(user.id),
                            package_id=price_id,
                            tokens_added=credit_pack["tokens"],
                            price_paid_usd=price_paid,
                            method=TokenPurchase.STRIPE,
                            transaction_ref=invoice_id,
                        )
                        logger.info("[invoice.paid] %s granted %s tokens (%s credits) to user_id=%s price_paid=%s", billing_reason, credit_pack['tokens'], credit_pack['credits'], user.id, price_paid)

            # ── invoice.payment_failed ────────────────────────────────────────
            elif event_type == 'invoice.payment_failed':
                try:
                    invoice = event_data
                    customer_id = invoice.get('customer')
                    if customer_id:
                        user = get_user_by_customer_id_str(customer_id)
                        if user:
                            logger.info("Payment failed for user_id=%s, no access change yet", user.id)
                            # We don't expire immediately — Stripe will retry
                            # and send customer.subscription.deleted when truly over
                except Exception as err:
                    logger.exception("Error with invoice.payment_failed")

            # ── customer.subscription.updated ─────────────────────────────────
            elif event_type == 'customer.subscription.updated':
                try:
                    subscription = event_data
                    customer_id = subscription.get('customer')
                    period_end = subscription.get('current_period_end')
                    sub_status = subscription.get('status', '')
                    logger.info("Subscription updated customer_id=%s sub_status=%s period_end=%s", customer_id, sub_status, period_end)

                    if customer_id:
                        user = get_user_by_customer_id_str(customer_id)
                        if user and period_end:
                            user.sub_end_date = unix_to_datetime(period_end)
                            user.save()
                            logger.info("Updated sub_end_date for user_id=%s until %s", user.id, user.sub_end_date)

                            # Tier-aware top-off: pull the price_id from the
                            # subscription's first line item. Fall back to the
                            # default cap for legacy/generic subs.
                            price_id = ""
                            try:
                                items = (subscription.get('items') or {}).get('data') or []
                                if items:
                                    price_id = (items[0].get('price') or {}).get('id', '')
                            except Exception:
                                price_id = ""

                            credit_pack = STRIPE_CREDIT_PACKAGES.get(price_id)
                            quota, _ = TokenQuota.objects.get_or_create(user_id=str(user.id))
                            if credit_pack:
                                quota.remaining_tokens = credit_pack["tokens"]
                            else:
                                quota.top_off_tokens(SUB_CREDIT_CAP_DEFAULT)
                            quota.reset_at = unix_to_datetime(period_end)
                            quota.save()
                            tier = f"{credit_pack['credits']} credits" if credit_pack else "default"
                            logger.info("Reset tier=%s for user_id=%s remaining=%s", tier, user.id, quota.remaining_tokens)
                except Exception as err:
                    logger.exception("Error with customer.subscription.updated")

            # ── customer.subscription.deleted ─────────────────────────────────
            elif event_type == 'customer.subscription.deleted':
                try:
                    subscription = event_data
                    customer_id = subscription.get('customer')
                    logger.info("Subscription deleted customer_id=%s", customer_id)

                    if customer_id:
                        user = get_user_by_customer_id_str(customer_id)
                        if user:
                            # Expire immediately — subscription is fully cancelled
                            user.sub_end_date = datetime.now(tz=timezone.utc) - timedelta(days=1)
                            user.save()
                            logger.info("Expired subscription for user_id=%s", user.id)

                            # Zero out subscription credits
                            quota, _ = TokenQuota.objects.get_or_create(user_id=str(user.id))
                            prev = quota.remaining_tokens
                            quota.remaining_tokens = 0
                            quota.save()
                            logger.info("Zeroed credits for user_id=%s previous=%s", user.id, prev)
                except Exception as err:
                    logger.exception("Error with customer.subscription.deleted")

            else:
                logger.info("Unhandled event type=%s", event_type)

            return JsonResponse({"success": True})

        except Exception as err:
            logger.exception("Webhook error")
        return JsonResponse({"success": False})
