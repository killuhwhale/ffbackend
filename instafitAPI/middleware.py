from django.contrib.auth import get_user_model
from django.contrib.gis.geoip2 import GeoIP2
from django.http import JsonResponse
import pytz
from instafitAPI.settings  import JWT_KEY
from jwt import decode, ExpiredSignatureError
from pytz import timezone
import logging

import environ
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
    SPACES_ENDPOINT_FULL=(str, ""),
    SPACES_ENDPOINT_EDGE=(str, ""),
    SPACES_KEY=(str, ""),
    SPACES_SECRET=(str, ""),
    BUCKET=(str, ""),
    SENDGRID_API_KEY=(str, ""),
    SENDGRIPD_FROM_EMAIL=(str, ""),
    SECRET_KEY=(str, ""),
    DEV_DB_NAME=(str, ""),
    DEV_DB_USER=(str, ""),
    DEV_DB_PASS=(str, ""),
    DJANGO_ALLOWED_HOSTS=(str, "127.0.0.1,localhost"),
    RUN_ENV=(str, "dev"),
    REVENUECAT_TOKEN=(str, ""),
)
environ.Env.read_env()

User =  get_user_model()
logger = logging.getLogger(__name__)


def get_user_timezone(request):
    g = GeoIP2()
    user_ip = request.META.get('REMOTE_ADDR')
    print('get_user_timezone', user_ip)
    if user_ip:
        try:
            # Get the user's timezone based on their IP address
            user_timezone = g.city(user_ip)['time_zone']
            print(f"user_timezone: {user_timezone=}")
            return user_timezone
        except:
            pass
    return "US/Pacific"



class JWTMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"middleware req: {request.method=}, {request.path=} ")
        # Allow requests to endpoints without auth token
        if request.path == "/":
            return JsonResponse({'data': f'Hello world {request.path}'}, status=200)

        if request.path in ['/hooks/revenuecat/', '/hooks/webhook/', '/login/', '/register/', '/token/', '/token/refresh/', '/users/', '/user/send_reset_code/', '/user/reset_password/', '/emailvalidation/confirm_email/', '/emailvalidation/send_confirmation_email']:
            if request.path == "/users/" and not request.method == "POST":
                print(f"Needs access token  for this users request, only post is bypassed... {request.method=}",)
                # return JsonResponse({'error': f'Invalid access token, route not permitted '}, status=401)
            elif request.path == "/hooks/revenuecat/":
                if request.META.get('HTTP_AUTHORIZATION') == env("REVENUECAT_TOKEN"):
                    print("Reveneue cat access granted..")
                    response = self.get_response(request)
                    return response
                else:
                    return JsonResponse({'error': 'Invalid access token'}, status=401)
            else:
                print("No access token needed... ")
                response = self.get_response(request)
                return response


        authorization = request.META.get('HTTP_AUTHORIZATION')
        if not authorization:
            return JsonResponse({'error': f'Authorizationz header is missing {request.path=}'}, status=401)

        try:
            access_token = authorization.split(' ')[1]
            payload = decode(access_token, JWT_KEY, verify=False, algorithms=["HS256"])
            user_id = payload.get('user_id')
            user = User.objects.get(id=user_id)
        except (IndexError, User.DoesNotExist, ExpiredSignatureError):
            return JsonResponse({'error': 'Invalid access token'}, status=401)

        response = self.get_response(request)
        return response


class TzMiddleware:
    ''' Adds Timezone to user. '''
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # logger.critical(f"middleware req: {request=} {request.method=}, {request.path=} ")
        tz = get_user_timezone(request)
        print(f"TZMiddleware: {tz=}", )
        if tz is not None:
            request.tz = tz

        response = self.get_response(request)
        return response



class LogMiddleware:
    ''' Logs when activity. '''
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # logger.critical(f"middleware req: {request=} {request.method=}, {request.path=} ")
        response = self.get_response(request)
        return response