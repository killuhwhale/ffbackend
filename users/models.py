from datetime import datetime, timedelta
import traceback
from urllib import parse
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.http import JsonResponse
import pyotp
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.base_user import BaseUserManager
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import logging
import stripe
from instafitAPI.settings import BASE_URL, env
from utils import get_env

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

stripe_key = get_env("STRIPE_API_KEY")
logger.critical(f"{stripe_key=}")
stripe.api_key = stripe_key


configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = env('SENDINBLUE_KEY')


class UserManager(BaseUserManager):
    use_in_migrations = True
    TESTING = get_env("RUN_ENV") == "dev"
    logger.critical(f"{TESTING=}")

    def send_confirmation_email(self, email):
        ''' After register is called, this should be called,'''
        if self.TESTING:
            logger.critical(f"{self.TESTING=} returning and not sending confirmation email.")
            return True
        try:
            code = pyotp.TOTP(pyotp.random_base32()).now()  # Just create a code
            ConfirmationEmailCodes.objects.create(email=email, code=code)

            url = f"{BASE_URL}/emailvalidation/confirm_email/?code={parse.quote(code)}&email={parse.quote(email)}"
            # localhost:8000/user/confirm_email/?code=420&email=t%40g.com
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration))
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[sib_api_v3_sdk.SendSmtpEmailTo(email=email)],
                template_id=2,
                params={'confirmURL': url},
            )
            api_response = api_instance.send_transac_email(send_smtp_email)
            logger.critical("Confirmation email sent!")
            return True

        except Exception as error:
            logger.critical(f"Error sending confirmation email: {error}")
            traceback.print_exc()
            return False

    def _create_stripe_customer(self, email):
        try:
            customer = stripe.Customer.create(
                email=email
            )
            return customer.id
        except Exception as err:
            logger.critical(f"Error creating customer id: {err=}")
            return None

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Users require an email field')
        email = self.normalize_email(email)

        # Prevents an issue with:
        # TypeError: Direct assignment to the forward side of a many-to-many set is prohibited. Use groups.set() instead.
        # However, we most likely wont need to add perms or groups at time of creation.
        # groups = extra_fields['groups']
        # perms = extra_fields['user_permissions']

        extra_fields['is_active'] = False
        if self.TESTING:
            extra_fields['is_active'] = True


        if "groups" in extra_fields:
            del extra_fields['groups']
        if "user_permissions" in extra_fields:
            del extra_fields['user_permissions']

        user: User = self.model(email=email, secret=pyotp.random_base32(), **extra_fields)
        customer_id = self._create_stripe_customer(email)
        logger.critical(f"Setting customer_id: {customer_id=}")
        logger.critical(f"Setting password: {password=}")
        user.customer_id = customer_id
        user.set_password(password)
        user.save()
        self.send_confirmation_email(email)
        return user

    def create_user(self, email, password=None, **extra_fields):
        logger.critical("Creating user!")

        print("Creating user!!!")
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    username = models.CharField(_('username'), max_length=100)
    # Used for Time-Based One-Time Password Algorithm key
    secret = models.CharField(_('secret'), max_length=32, blank=True, null=True)
    customer_id = models.CharField(_('customer_id'), max_length=64, blank=True, null=True)
    subscribed = models.BooleanField(_('subscribed'), default=False)
    sub_end_date = models.DateTimeField(_('sub_end_date'), default=datetime.now() - timedelta(days=1))
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class META:
        app_label='users'

@receiver(post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


class ConfirmationEmailCodes(models.Model):
    email = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=1000)


