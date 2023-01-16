from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
import pyotp
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Users require an email field')
        email = self.normalize_email(email)

        # Prevents an issue with:
        # TypeError: Direct assignment to the forward side of a many-to-many set is prohibited. Use groups.set() instead.
        # However, we most likely wont need to add perms or groups at time of creation.
        # groups = extra_fields['groups']
        # perms = extra_fields['user_permissions']



        # TODO Change to false and have an email verification process
        # When use confirms email, change their account to active, is_active: True
        print("_create_user extra fields", extra_fields)
        extra_fields['is_active'] = True


        if "groups" in extra_fields:
            del extra_fields['groups']
        if "user_permissions" in extra_fields:
            del extra_fields['user_permissions']

        user = self.model(email=email, secret=pyotp.random_base32(), **extra_fields)

        user.set_password(password)
        user.save()
        return user

    def create_user(self, email, password=None, **extra_fields):
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
    secret = models.CharField(_('secret'), max_length=32, blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []


@receiver(post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
