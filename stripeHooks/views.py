import json
import os
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.http import JsonResponse
import logging
import stripe
from instafitAPI.settings import env
from utils import get_env


logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
User =  get_user_model()

# Replace this endpoint secret with your endpoint's unique secret
# If you are testing with the CLI, find the secret by running 'stripe listen'
# If you are using an endpoint defined with the API or dashboard, look in your webhook settings
# at https://dashboard.stripe.com/webhooks
endpoint_secret = env("STRIPE_SIGNING_KEY") or os.getenv('STRIPE_SIGNING_KEY')


def get_user_by_customer_id(stripe_obj):
    try:
        cusomter_id = stripe_obj.customer
        return User.objects.get(cusomter_id=cusomter_id)
    except Exception as e:
        logger.critical(f"Failed to find user.", e)
    return None

class HookViewSet(viewsets.ViewSet):
    '''
    Listens for Stripe events to update memberships.
    charge.succeeded
    data.object is a charge
    '''

    @action(detail=False, methods=['POST'], permission_classes=[])
    def webhook(self, request, pk=None):
        payload = request.body.decode('utf-8')
        event = None
        user = None
        print(f"{event=}")

        # Testin dev server only...
        # try:
        #     event = json.loads(payload)
        # except Exception as e:
        #     print('⚠️  Webhook error while parsing basic request.' + str(e))
        #     return JsonResponse({"success": False})

        if endpoint_secret:
            # Only verify the event if there is an endpoint secret defined
            # Otherwise use the basic event deserialized with json
            sig_header = request.headers.get('stripe-signature')
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, endpoint_secret
                )
            except stripe.error.SignatureVerificationError as e:
                print('⚠️  Webhook signature verification failed.' + str(e))
                return JsonResponse({"success": False})

        # Handle the event
        if event and event['type'] == 'charge.succeeded':
            charge = event['data']['object']
            user = get_user_by_customer_id(charge)
            print('Payment for {} succeeded at amt {}'.format(user, charge['amount']))
            print(f"{charge=}")

        elif event['type'] == 'customer.subscription.created':
            sub = event['data']['object']
            user = get_user_by_customer_id(sub)
            print('Subscription for {} succeeded at amount {}'.format(user, charge['amount']))
            print(f"{sub=}")
        else:
            # Unexpected event type
            print('Unhandled event type {}'.format(event['type']))

        return JsonResponse({"success": True})