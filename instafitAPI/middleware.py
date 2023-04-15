from django.http import JsonResponse
from jwt import decode, ExpiredSignatureError
from django.contrib.auth import get_user_model
from instafitAPI.settings  import JWT_KEY
User =  get_user_model()

class JWTMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"middleware req: {request.method=}, {request.path=}")
        # Allow requests to endpoints without auth token
        if request.path in ['/login/', '/register/', '/token/', '/token/refresh/', '/users/', '/emailvalidation/confirm_email/', '/emailvalidation/send_confirmation_email']:
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