from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password

from users.models import User


class EmailAuth(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        try:
            user = User.objects.get(email=email)
            if(check_password(password, user.password)):
                return user
        except Exception as e:
            print("EmailAuth error: ", e)
        return None
