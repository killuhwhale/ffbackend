import environ
import sendgrid
from datetime import datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework_simplejwt.views import TokenObtainPairView
from time import time
from sendgrid.helpers.mail import Email, To, TemplateId, Mail
from gyms.s3 import s3Client
from gyms.views import FILES_KINDS
from gyms.models import ResetPasswords
from users.serializers import (
    UserCreateSerializer, UserSerializer, GroupSerializer,
    UserWithoutEmailSerializer, TokenObtainPairSerializer
)
env = environ.Env()

s3_client = s3Client()


# Deprecated since we dont send user info with requests. We have tokens...
class SelfActionPermission(BasePermission):
    message = """Only users can perform actions for themselves."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        if request.method == "POST" and not view.action == "CREATE":
            user_id = view.kwargs['pk']
            return str(user_id) == str(request.user.id)
        return False


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = get_user_model().objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = []

    @action(detail=False, methods=['POST'], permission_classes=[permissions.IsAuthenticated])
    def update_username(self, request, pk=None):
        try:
            user_id = request.user.id
            user = get_user_model().objects.get(id=user_id)
            username = request.data.get("username", user.username)
            print("New username: ", username)
            user.username = username
            user.save()
            return Response(UserSerializer(user).data)
        except Exception as e:
            print("Update username error: ", e)
        return Response({'error': 'Unable to update username'})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def user_info(self, request, pk=None):
        if request.user:
            return Response(UserSerializer(request.user).data)
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
            print("User profile image upload: ", e)
            return Response("Error uploading user profile image")

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return UserWithoutEmailSerializer
        elif self.action == "create":
            return UserCreateSerializer
        return UserSerializer


class ResetPasswordEmailViewSet(viewsets.ViewSet):
    '''
     Returns workouts between a range of dates either for a user's workouts or a classes workouts.
    '''
    @action(detail=False, methods=['POST'], permission_classes=[])
    def send_reset_code(self, request, pk=None):
        email = request.data.get("email")
        generated_code = "1337godlike"
        print(f"Sending {generated_code} to {email}")
        # https://github.com/sendgrid/sendgrid-python/blob/main/use_cases/transactional_templates.md
        minute = 60
        try:
            if not get_user_model().objects.filter(email=email).exists():
                return Response({'error': 'User not found'})

        except Exception as e:
            print("Error getting user or creating code.", e)
            return Response({'error': 'Failed to find user with email.'})
        try:
            ResetPasswords.objects.get_or_create(
                email=email,
                code=generated_code,
                expires_at=datetime.fromtimestamp(int(time()) + (15 * minute))
            )
        except Exception as e:
            print("Error getting user or creating code.", e)
            return Response({'error': 'Failed to create code.'})

        # sg = sendgrid.SendGridAPIClient(
        #     api_key=env('SENDGRID_API_KEY'))
        # from_email = Email(env('SENDGRIPD_FROM_EMAIL'))
        # to_email = To(email)
        # message = Mail(from_email, to_email)
        # message.dynamic_template_data = {
        #     'reset_code': generated_code,
        # }
        # message.template_id = 'd-37c297a72a8243ca8f105a0137ec304d'

        # response = sg.send(message)
        # print(response.status_code)
        # print(response.body)
        # print(response.headers)

        return Response({'data': "Email Sent!"})

    @action(detail=False, methods=['POST'], permission_classes=[])
    def reset_password_with_old(self, request, pk=None):
        email = request.user.email
        print("reset_password_with_old", request.data)
        password = request.data.get("password")
        new_password = request.data.get("new_password")
        password_confirm = request.data.get("password_confirm")
        try:
            user = get_user_model().objects.get(email=email)
            print('Password check: ', password, user.password, new_password, password_confirm, check_password(password, user.password),
                  new_password == password_confirm)
            if check_password(password, user.password) and new_password == password_confirm and new_password:
                user.set_password(new_password)
                user.save()
                return Response({'data': 'Changed password'})
            return Response({'error': 'Invalid password'})
        except Exception as e:
            print("Error", e)
            return Response({'error': ''})

    @action(detail=False, methods=['POST'], permission_classes=[])
    def reset_password(self, request, pk=None):
        email = request.data.get("email")
        user_code = request.data.get("reset_code")
        new_password = request.data.get("new_password")
        fifteen_mins_ago = datetime.now().timestamp() - (60 * 15)
        try:
            entries = ResetPasswords.objects.filter(
                email=email,
                expires_at__gte=datetime.fromtimestamp(fifteen_mins_ago)
            )

            if not entries or not entries.exists():
                return Response({'error': "Code not found."})
            entry = entries.first()
            if user_code == entry.code:
                # Change password
                user = get_user_model().objects.get(email=email)
                user.set_password(new_password)
                user.save()
                entry.delete()
                return Response({'data': "Password reset."})

        except Exception as e:
            print("Error resetting password", e)

        return Response({'error': 'Failed to reset password.'})


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = []


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
