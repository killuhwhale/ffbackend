from urllib import parse
from django.http import HttpResponse, JsonResponse
import environ
import pyotp
from datetime import datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import Group
from django.db.utils import IntegrityError
import pytz
from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework_simplejwt.views import TokenObtainPairView
from time import time
from rest_framework.parsers import JSONParser
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from gyms.s3 import s3Client
from gyms.views import FILES_KINDS
from gyms.models import ResetPasswords
from users.models import ConfirmationEmailCodes
from users.serializers import (
    UserCreateSerializer, UserSerializer, GroupSerializer,
    UserWithoutEmailSerializer, MyTokenObtainPairSerializer
)
from instafitAPI.throttles import (
    LoginRateThrottle, PasswordResetSendThrottle,
    PasswordResetSubmitThrottle, UserCreateThrottle,
)
env = environ.Env()
tz = pytz.timezone("US/Pacific")
s3_client = s3Client()

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = env('SENDINBLUE_KEY')
import logging
logger = logging.getLogger(__name__)
User = get_user_model()

class UserGroupsPermission(BasePermission):
    message = """No perms"""

    def has_permission(self, request, view):
        return False

class UsersPermission(BasePermission):
    message = """Only users can get or modify their own data. Except for profile image."""

    def has_permission(self, request, view):
        if view.action == "update" or view.action == "partial_update":
            return False
        elif request.method in SAFE_METHODS:
            # Check permissions for read-only request
            return True

        elif request.method == "POST" and view.action == "create":
            return True
        elif view.action == "destroy":
            user = request.user
            user_id = view.kwargs['pk']
            return str(user.id) == user_id
        return False

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    /users/
    """
    queryset = get_user_model().objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [UsersPermission]

    def get_throttles(self):
        # Only throttle account creation; other actions use the global default.
        if self.action == "create":
            return [UserCreateThrottle()]
        return super().get_throttles()

    @action(detail=False, methods=['POST'], permission_classes=[permissions.IsAuthenticated])
    def update_username(self, request, pk=None):
        try:
            user_id = request.user.id
            user = get_user_model().objects.get(id=user_id)
            username = request.data.get("username", user.username)
            logger.debug("Updating username for user_id=%s", user_id)
            user.username = username
            user.save()
            return Response(UserSerializer(user).data)
        except Exception as e:
            logger.exception("Update username failed")
        return Response({'error': 'Unable to update username'})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def user_info(self, request, pk=None):
        if request.user:
            return Response(UserSerializer(request.user).data)
        return Response({})

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated], parser_classes=[JSONParser])
    def update_sub(self, request, pk=None):
        '''Deprecated. Sub is updated via webhooks.'''
        # if request.user:

        #     subbed = request.data.get("__SUBSCRIBED")
        #     sub_end_date = request.data.get("sub_end_date")
        #     user = User.objects.get(id=request.user.id)
        #     user.sub_end_date = sub_end_date
        #     user.save()

        #     return Response(UserSerializer(user).data)
        return Response({})

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated], parser_classes=[JSONParser])
    def update_customer_id(self, request, pk=None):
        """Deprecated. Customer_id is created during registration."""
        # if request.user:

        #     customer_id = request.data.get("customer_id")
        #     user = User.objects.get(id=request.user.id)
        #     user.customer_id = customer_id
        #     user.save()

        #     return Response(UserSerializer(user).data)
        return Response({})

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def profile_image(self, request, pk=None):
        try:
            user_id = request.user.id
            file = request.data.getlist("file", [None])[0]
            if file and user_id:
                return Response(s3_client.upload(file, FILES_KINDS[4], user_id, "profile_image"))
            return Response("Failed uploading image, no file given.")
        except Exception as e:
            logger.exception("User profile image upload failed")
            return Response("Error uploading user profile image")

    def get_serializer_class(self):
        logger.debug("Selecting user serializer for action=%s", self.action)
        if self.action == 'list' or self.action == 'retrieve':
            return UserWithoutEmailSerializer
        elif self.action == "create":
            return UserCreateSerializer
        return UserSerializer


class ConfirmEmailViewSet(viewsets.ViewSet):


    def _html_code(self, verified_msg: str):
        return f'''<!DOCTYPE html>
            <html>
            <head>
                <title>Verification Page</title>
                <!-- Load Bootstrap CSS from CDN -->
                <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css">
                <style>
                    pre {'{'}
                        line-height: 0.8;
                        height: 200px;
                    {'}'}
                    body {'{'}
                        background-color: #00bfff; /* Sick background color */
                        color: white; /* Cool text color */
                        font-size: 24px;
                        font-weight: bold;
                        text-align: center;
                        margin-top: 100px;
                    {'}'}
                </style>
            </head>
            <body>
                <img src="https://raw.githubusercontent.com/killuhwhale/ffbackend/main/reptrackrr.webp" width="300px" />

                <div class="container">
                    <h1>{verified_msg}</h1>
                </div>
                <!-- Load Bootstrap JS from CDN -->
                <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js"></script>
            </body>
            </html>'''

    @action(detail=False, methods=['GET'], permission_classes=[])
    def confirm_email(self, request, pk=None):
        # Get params
        try:
            code = request.query_params.get('code')
            email = request.query_params.get('email')
            logger.debug("Confirm email request received for email=%s", email)

            confirm_obj = ConfirmationEmailCodes.objects.get(email=email, code=code)
            user = get_user_model().objects.get(email=email)
            user.is_active = True
            user.save()
            confirm_obj.delete()
            return HttpResponse(self._html_code("Verified successfully!"))
        except Exception as error:
            logger.warning("Confirm email failed: %s", error)
            return HttpResponse(self._html_code("Failed to verify..."))



class ResetPasswordEmailViewSet(viewsets.ViewSet):
    '''
      Sends Email code to reset password.
      /user/
    '''
    minute = 60
    CODE_VALID_TIME= 15 * minute

    def _get_user(self, email: str):
        try:
            logger.debug("Looking up reset-password user for email=%s", email)
            return get_user_model().objects.get(email=email)
        except Exception as e:
            logger.debug("Reset-password user lookup failed for email=%s: %s", email, e)
            return None

    def _check_expired_entry(self, email: str):
        # 2. Check for all existing entries by email.
        entries = ResetPasswords.objects.filter(email=email)
        has_existing_code = False
        # 3.For each entry,
        now = tz.localize(datetime.now())


        for entry in entries:
            # Time for expiration is greater than now, its in future.
            if entry.expires_at >= now:
                has_existing_code = True
            else:
                # Expired code, delete it.
                entry.delete()
        return has_existing_code

    def _send_email(self, user):
        # 4. Now we if we are proceeding, we can generate a new coed and send it & store it
        # Time-Based One-Time Password Algorithm used to generate a unique code per user.
        code = pyotp.TOTP(user.secret, interval=5).now()  # Just create a code
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration))
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[sib_api_v3_sdk.SendSmtpEmailTo(email=user.email)],
            template_id=1,
            params={'reset_code': code},
        )

        new_entry = None

        try:
            new_entry = ResetPasswords.objects.create(
                email=user.email,
                code=code,
                expires_at= tz.localize(datetime.fromtimestamp(int(time()) + (self.CODE_VALID_TIME)))
            )
        except IntegrityError as e:
            logger.debug("Reset-password code already exists for user_id=%s: %s", user.id, e)
            return {'error': 'Code already exsits.'}
        except Exception as e:
            logger.exception("Error creating reset-password code")
            return {'error': 'Server Failed!.'}

        try:
            # Send a transactional email
            api_response = api_instance.send_transac_email(send_smtp_email)
            logger.debug("Reset-password email API response: %s", api_response)
        except ApiException as e:
            # If Failed to send Email, delete entry on our side.
            if not new_entry is None:
                new_entry.delete()
            logger.warning("Exception when calling TransactionalEmailsApi->send_transac_email: %s", e)
            return {'error': 'Email API Failed!.'}
        return {'data': "Email Sent!"}

    @action(detail=False, methods=['POST'], permission_classes=[], throttle_classes=[PasswordResetSendThrottle])
    def send_reset_code(self, request, pk=None):
        '''  '''
        email = request.data.get("email") or request.data.get("resetEmail")
        logger.debug("Reset-password code requested for email=%s", email)
        user = self._get_user(email)

        if user is None:
            return Response({'error': 'Failed to find email.'})

        has_existing_code = self._check_expired_entry(email)
        if has_existing_code:
            logger.debug("Reset-password code already exists for email=%s", email)
            return Response({'error': 'You already have an existing code. Please enter the code on the Submit Code page; or wait 15 mins.'})

        return Response(self._send_email(user))



    @action(detail=False, methods=['POST'], permission_classes=[], throttle_classes=[PasswordResetSubmitThrottle])
    def reset_password(self, request, pk=None):
        email = request.data.get("email")
        user_code = request.data.get("reset_code")
        new_password = request.data.get("new_password")

        fifteen_mins_ago = tz.localize(
            datetime.fromtimestamp(
                datetime.now().timestamp() - (self.CODE_VALID_TIME)))

        try:
            self._check_expired_entry(email)  # Clear all previously expired tokens.
            entry = ResetPasswords.objects.get(
                email=email,
                code=user_code,
                expires_at__gte= fifteen_mins_ago
            )

            if user_code == entry.code:
                # Change password
                user = get_user_model().objects.get(email=email)
                user.set_password(new_password)
                user.save()
                entry.delete()
                return Response({'data': "Password reset."})

        except Exception as e:
            logger.warning("Error resetting password for email=%s: %s", email, e)
            # TODO,

        return Response({'error': 'Failed to reset password.'})



    @action(detail=False, methods=['POST'], permission_classes=[])
    def reset_password_with_old(self, request, pk=None):
        email = request.user.email
        password = request.data.get("password")
        new_password = request.data.get("new_password")
        password_confirm = request.data.get("password_confirm")
        try:
            user = get_user_model().objects.get(email=email)
            password_matches = check_password(password, user.password)
            passwords_match = new_password == password_confirm
            logger.debug(
                "Password change requested for user_id=%s password_matches=%s passwords_match=%s",
                user.id,
                password_matches,
                passwords_match,
            )
            if password_matches and passwords_match and new_password:
                user.set_password(new_password)
                user.save()
                return Response({'data': 'Changed password'})
            return Response({'error': 'Invalid password'}, status=403)
        except Exception as e:
            logger.exception("Reset password with old password failed")
            return Response({'error': ''}, status=501)


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [UserGroupsPermission]


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def ping(request):
    return JsonResponse({"message": "pong 🏓"})


# class EmailTokenObtainPairView(TokenObtainPairView):
#     serializer_class = MyTokenObtainPairSerializer

#     def post(self, request, *args, **kwargs):
#         logger.debug("🔥 Token endpoint hit, payload=", request.data)

#         # serializer = self.get_serializer(data=request.data)
#         serializer = MyTokenObtainPairSerializer(data=request.data)
#         try:
#             # this is where it will raise a ValidationError on bad creds
#             serializer.is_valid(raise_exception=True)
#         except Exception as exc:
#             # log the full error detail
#             logger.exception("🚨 TokenObtainPair failed")
#             # re-raise so DRF still returns 401 with detail
#             raise

#         # if you get here, it succeeded
#         logger.debug("✅ TokenObtainPair succeeded for user %r", serializer.user)
#         return Response(serializer.validated_data, status=status.HTTP_200_OK)
