import logging
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password

from django.contrib.auth import get_user_model
User = get_user_model()
logger = logging.getLogger(__name__)

class EmailAuth(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        try:
            user = User.objects.get(email=email)

            if(check_password(password, user.password)):
                logger.debug("Email authentication succeeded for user_id=%s", user.id)
                return user
        except Exception as e:
            logger.debug("Email authentication failed for email=%s: %s", email, e)
        return None
