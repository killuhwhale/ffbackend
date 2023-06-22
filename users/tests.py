from datetime import datetime
import json
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
import pytz

from gyms.models import ResetPasswords

User =  get_user_model()

tz = pytz.timezone("US/Pacific")
class TestUsers(TestCase):
    minute = 60
    CODE_VALID_TIME= 15 * minute
    def setUp(self):
        self.req = Client()

        self.user_a = User.objects.create_user(
            email="t1@g.com",
            password="test"
        )
        self.jwt_token_a = json.loads(self.req.post(
            "/token/",
            {'email': self.user_a.email, 'password': 'test'}
        ).content)['access']

        self.user_b = User.objects.create_user(
            email="t2@g.com",
            password="test"
        )
        self.jwt_token_b = json.loads(self.req.post(
            "/token/",
            {'email': self.user_b.email, 'password': 'test'}
        ).content)['access']

        self.user_del = User.objects.create_user(
            email="t3@g.com",
            password="test"
        )
        self.jwt_token_del = json.loads(self.req.post(
            "/token/",
            {'email': self.user_del.email, 'password': 'test'}
        ).content)['access']


    def test_user_change_other_user_password(self):
        ''' Ensure a user cannot change the password of another user.
            User must have the correct token and the previous password.
        '''
        # user/reset_password_with_old
        res = self.req.post(f'/user/reset_password_with_old/', {
                'password': 'badpass',
                'new_password': 'newpass',
                'password_confirm': 'newpass',
            },
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        self.assertEqual(res.status_code, 403)

    def test_user_delete_other_users(self):
        ''' Ensure a user cannot delete another user.
        '''
        res = self.req.delete(f'/users/{self.user_a.id}/',
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_b}')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can get or modify their own data. Except for profile image.'}
        )

    def test_user_delete_self(self):
        ''' Ensure a user can delete self.
        '''
        # Ensure user can delete themselves
        res = self.req.delete(f'/users/{self.user_del.id}/',
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_del}')
        self.assertEqual(res.status_code, 204)
        self.assertRaises(User.DoesNotExist, self.user_del.refresh_from_db)

    def test_user_change_other_user_username(self):
        ''' Ensure a user can change their username. Route protected via token.
        '''
        res = self.req.post(f'/users/update_username/', {'username': 'new username'},
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_b}')

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            json.loads(res.content.decode())['username'],
            'new username'
        )
        self.assertEqual(
            json.loads(res.content.decode())['email'],
            't2@g.com'
        )

    def test_user_reset_password(self):
        ''' Ensure a user can change their password via email.

            1. User sends request w/ email to get a code sent to their Email
            2. We generate, store and email a code for that user for w/ expiry in 15mins
          -----
            3. The user gets the code from email and sends a new request with email, code and new password.
            4. We clear all expired codes, check the new code given in request w/ email to get their code on server side
            5. if the server side code matches the code provided, we update the password and delete the code from the DB.

            Points of failure:
            - Not sure.
            - Codes are cleaned up and can be regenerated every 15 mins.
        '''

        res = self.req.post(f'/user/send_reset_code/', {'email': self.user_a.email},
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        print(f"{res.content=}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'data': 'Email Sent!'}
        )

        entry = ResetPasswords.objects.get(email=self.user_a.email)
        res = self.req.post(f'/user/reset_password/', {
                'email': self.user_a.email,
                'reset_code': entry.code,
                'new_password': 'new_apsswordabc',
            },
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(
            json.loads(res.content.decode()),
            {'data': 'Password reset.'}
        )


    def test_user_reset_password_expired_code(self):
        ''' Ensure OTP expiry date is works as expected when expired.
        '''

        res = self.req.post(f'/user/send_reset_code/', {'email': self.user_a.email},
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        print(f"{res.content=}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'data': 'Email Sent!'}
        )

        entry = ResetPasswords.objects.get(email=self.user_a.email)
        twenty_mins_ago = tz.localize(
            datetime.fromtimestamp(
                datetime.now().timestamp() - (self.CODE_VALID_TIME + 5)))
        entry.expires_at = twenty_mins_ago
        entry.save()

        res = self.req.post(f'/user/reset_password/', {
                'email': self.user_a.email,
                'reset_code': entry.code,
                'new_password': 'new_apsswordabc',
            },
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(
            json.loads(res.content.decode()),
            {'error': 'Failed to reset password.'}
        )


    def test_user_reset_password_expired_code(self):
        ''' Ensure OTP expiry date is works as expected when expired.
        '''
        codes = ResetPasswords.objects.filter(email=self.user_a.email)
        self.assertEqual(len(codes), 0)





