from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password

from django.contrib.auth import get_user_model
User = get_user_model()

class EmailAuth(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        try:
            print("My auth: email: " , email)
            user = User.objects.get(email=email)
            print("My auth: user: " , user)
            print("My auth: passowrd: " , password, user.password)

            if(check_password(password, user.password)):
                return user
        except Exception as e:
            print(f"EmailAuth error: ({email=})", e)
        return None
