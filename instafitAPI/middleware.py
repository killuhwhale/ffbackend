from django.http import JsonResponse
from jwt import decode, ExpiredSignatureError
from django.contrib.auth import get_user_model
from instafitAPI.settings  import JWT_KEY
User =  get_user_model()
import logging

logger = logging.getLogger(__name__)


class JWTMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.critical(f"middleware req: {request.method=}, {request.path=} ")
        # Allow requests to endpoints without auth token
        if request.path in ['/login/', '/register/', '/token/', '/token/refresh/', '/users/', '/user/send_reset_code/', '/user/reset_password/', '/emailvalidation/confirm_email/', '/emailvalidation/send_confirmation_email']:
            if request.path == "/users/" and not request.method == "POST":
                print("Needs access token... go along and procedd")
                # return JsonResponse({'error': f'Invalid access token, route not permitted '}, status=401)
            else:
                response = self.get_response(request)
                return response


        authorization = request.META.get('HTTP_AUTHORIZATION')
        if not authorization:
            return JsonResponse({'error': f'Authorization header is missing {request.path}'}, status=401)

        try:
            access_token = authorization.split(' ')[1]
            payload = decode(access_token, JWT_KEY, verify=False, algorithms=["HS256"])
            user_id = payload.get('user_id')
            user = User.objects.get(id=user_id)
        except (IndexError, User.DoesNotExist, ExpiredSignatureError):
            return JsonResponse({'error': 'Invalid access token'}, status=401)

        response = self.get_response(request)
        return response