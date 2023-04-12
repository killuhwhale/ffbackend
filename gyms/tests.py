import json
from django.test import Client, TestCase
from django.urls import reverse
from gyms.models import ClassMembers, Coaches, CompletedWorkoutGroups, CompletedWorkoutItems, CompletedWorkouts, Gyms, GymClasses, WorkoutGroups, WorkoutItems, WorkoutNames, Workouts
from django.contrib.auth import get_user_model
from gyms.utils import tz_aware_date, tz_aware_today

from gyms.views import GymViewSet
# Create your tests here.
User =  get_user_model()

class GymTestCase(TestCase):
    '''
        Collection of tests to ensure that basic funtionality is met.


    '''
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

        self.gym_a = Gyms.objects.create(
            title="NC Test",
            desc="A gym desc",
            owner_id=self.user_a.id
        )
        self.gym_class_a = GymClasses.objects.create(
            gym=self.gym_a,
            title="NC Test Class",
            desc="A gym class desc",
        )
        self.gym_b = Gyms.objects.create(
            title="CF Mayhem",
            desc="2nd gym",
            owner_id=self.user_b.id
        )
        self.gym_class_b = GymClasses.objects.create(
            gym=self.gym_b,
            title="CF Mayhem",
            desc="2nd gym class",
        )

        self.coach_b = Coaches.objects.create(
            gym_class=self.gym_class_b,
            user_id=self.user_b.id
        )
        self.member_b = ClassMembers.objects.create(
            gym_class=self.gym_class_b,
            user_id=self.user_b.id
        )

        self.workoutgroup_b = WorkoutGroups.objects.create(
            owner_id=self.user_b.id,
            owned_by_class=False,
            title="User B workoutgroup",
            caption="Test desc",
            for_date=tz_aware_today(),
            finished=False
        )

        # Gets Delete in test_delete_workoutgroup_by_workoutclass_when_not_finished
        self.workoutgroup_b_by_gymclass = WorkoutGroups.objects.create(
            owner_id=self.gym_class_b.id,
            owned_by_class=True,
            title="User B's gymclass workoutgroup",
            caption="Test desc",
            for_date=tz_aware_today(),
            finished=False
        )

        self.workoutgroup_b_unfinished = WorkoutGroups.objects.create(
            owner_id=self.user_b.id,
            owned_by_class=False,
            title="User B's unfinshed workoutgroup",
            caption="Test desc",
            for_date=tz_aware_today(),
            finished=False
        )

        self.workoutgroup_b_finished = WorkoutGroups.objects.create(
            owner_id=self.user_b.id,
            owned_by_class=False,
            title="User B finished workoutgroup",
            caption="Test desc  finished",
            for_date=tz_aware_today(),
            finished=True
        )

        self.workout_b = Workouts.objects.create(
            group= self.workoutgroup_b_finished,
            title= "My first regular workout",
            desc= "testing wod",
            scheme_type= 0,
            # "scheme_rounds": '[]',
        )

        self.squat = WorkoutNames.objects.create(
            name= 'Squat',
        )

        self.item_b = WorkoutItems.objects.create(
            workout= self.workout_b,
            name= self.squat,
            sets= '3',
            reps= '[5]',
            weights= '[135,150,185] ',
            weight_unit= 'lb',
            order= 1
        )

        self.completed_workout_group = CompletedWorkoutGroups.objects.create(
            workout_group=self.workoutgroup_b_finished,
            user_id=self.user_b.id,
            title='Test Completed UserB',
            caption='abc',
            for_date=tz_aware_today(),
        )
        self.completed_workout = CompletedWorkouts.objects.create(
            completed_workout_group=self.completed_workout_group,
            workout=self.workout_b,
            user_id=self.user_b.id,
            title="UserB Completed Workout",
            desc="xyz",
            scheme_type=self.workout_b.scheme_type,
            scheme_rounds=self.workout_b.scheme_rounds,
        )

        item = self.item_b.__dict__
        del item['_state']
        del item['id']
        del item['workout_id']
        self.completed_workout_item = CompletedWorkoutItems.objects.create(
            user_id=self.user_b.id,
            completed_workout=self.completed_workout,
            **item
        )




    def test_delete_gym(self):
        '''
            Ensure that user A cannot delete User B's Gym
        '''
        res = self.req.delete(f'/gyms/{self.gym_b.id}/', HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.content, b'{"detail":"Only Gym owners can remove their gym"}')

    def test_delete_gym_class(self):
        '''
            Ensure that user A cannot delete User B's GymClass
        '''

        res = self.req.delete(f'/gymClasses/{self.gym_class_b.id}/', HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.content, b'{"detail":"Only Gym owners can create or remove classes"}')

    def test_create_gym_class(self):
        '''
            Ensure that user A cannot create a GymClass under User B's GymC
        '''

        res = self.req.post(
            f'/gymClasses/',
            {
                'gym': self.gym_b.id,
                'title': 'Bad Gym',
                'desc': 'Gym that shouldnt be created',
            },
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.content, b'{"detail":"Only Gym owners can create or remove classes"}')

    def test_coach_create_by_nonowner(self):
        '''
            Ensure that a user cannot create a coach if the gym belongs to another user.
        '''

        res = self.req.post(f'/coaches/', {
            "user_id": 1,
            "gym_class": self.gym_class_b.id,
        }, HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only gym owners can create/delete a coach for their gymclasses.'}
        )

    def test_coach_delete_by_nonowner(self):
        '''
            Ensure that a user cannot delete a coach if the gym belongs to another user.
        '''
        res = self.req.delete(f'/coaches/{self.coach_b.id}/', HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only gym owners can create/delete a coach for their gymclasses.'}
        )

    def test_member_create_by_nonowner(self):
        '''
            Ensure that a user cannot create a member if the gymclass belongs to another user.
        '''

        res = self.req.post(f'/classMembers/', {
            "user_id": self.user_b.id,
            "gym_class": self.gym_class_b.id,
        }, HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only gym owners or coaches can create/delete a member for their gymclasses.'}
        )

    def test_member_delete_by_nonowner(self):
        '''
            Ensure that a user cannot delete a member if the gymclass belongs to another user.

            This should not be used. Blocked Endpoint.
        '''
        res = self.req.delete(f'/classMembers/{self.member_b.id}/', HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only gym owners or coaches can create/delete a member for their gymclasses.'}
        )

    def test_member_delete_by_nonowner_via_remove_endpoint(self):
        '''
            Ensure that a user cannot delete a member if the gymclass belongs to another user.
        '''
        data = {
            "user_id": self.member_b.id,
            "gym_class": self.gym_class_b.id
        }
        res = self.req.delete(f'/classMembers/remove/', data, HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}', content_type='application/json')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only gym owners or coaches can create/delete a member for their gymclasses.'}
        )

    def test_create_workoutgroup_another_user(self):
        '''
            Ensure that user A cannot create a WorkoutGroup under User B's ID
        '''

        res = self.req.post(
            f'/workoutGroups/',
            {

                'owner_id': self.user_b.id,
                'owned_by_class': False,
                'title': "Test Wod",
                'caption': "Test Wod desc",
            },
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
           {'detail': 'Only users can create/delete workouts for themselves or\n                for a class they own or are a coach of.'}
        )

    def test_create_workoutgroup_another_gymclass(self):
        '''
            Ensure that user A cannot create a WorkoutGroup under User B's GymClass
        '''

        res = self.req.post(
            f'/workoutGroups/',
            {

                'owner_id': self.gym_class_b.id,
                'owned_by_class': True,
                'title': "Test Wod",
                'caption': "Test Wod desc",
            },
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
           {'detail': 'Only users can create/delete workouts for themselves or\n                for a class they own or are a coach of.'}
        )


    def test_delete_workoutgroup_another_user(self):
        '''
            Ensure that user A cannot delete a WorkoutGroup under User B's ID
        '''

        res = self.req.delete(
            f'/workoutGroups/{self.workoutgroup_b.id}/',
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
           {'detail': 'Only users can create/delete workouts for themselves or\n                for a class they own or are a coach of.'}
        )

    def test_delete_workoutgroup_another_gymclass(self):
        '''
            Ensure that user A cannot delete a WorkoutGroup under User B's GymClass
        '''

        res = self.req.delete(
            f'/workoutGroups/{self.workoutgroup_b_by_gymclass.id}/',
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
           {'detail': 'Only users can create/delete workouts for themselves or\n                for a class they own or are a coach of.'}
        )



    def test_delete_workoutgroup_by_workoutclass_when_not_finished(self):
        '''
            Ensure that a user can delete a workoutGroup they control when the WorkoutGroup is not finsihed.
        '''

        self.assertEqual(self.workoutgroup_b_by_gymclass.archived, False)
        # Send delete request to marka s archived.
        res = self.req.delete(
            f'/workoutGroups/{self.workoutgroup_b_by_gymclass.id}/',
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_b}')
        self.assertEqual(res.status_code, 200)

        self.assertRaises(WorkoutGroups.DoesNotExist, self.workoutgroup_b_by_gymclass.refresh_from_db)

    def test_delete_workoutgroup_archived(self):
        '''
            Ensure that a user's workoutGroup is Archived instead of deleted when it is finished.
        '''

        self.assertEqual(self.workoutgroup_b_finished.finished, True)
        self.assertEqual(self.workoutgroup_b_finished.archived, False)
        # Send delete request to mark as archived.
        res = self.req.delete(
            f'/workoutGroups/{self.workoutgroup_b_finished.id}/',
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_b}')
        self.assertEqual(res.status_code, 200)

        # Now we should have successfully marked it as ARchived, lets check
        self.workoutgroup_b_finished.refresh_from_db()
        self.assertEqual(self.workoutgroup_b_finished.archived, True)


    def test_workoutgroup_prevent_empty_finish(self):
        '''
            Ensure that a user's workoutGroup not marked as finished unless there is at least 1 workout w/ 1 workout item.
        '''

        self.assertEqual(self.workoutgroup_b_unfinished.finished, False)

        res = self.req.post(
            f'/workoutGroups/finish/', {
                "group": self.workoutgroup_b_unfinished.id
            },
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_b}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.workoutgroup_b_unfinished.finished, False)

    def test_workoutgroup_finish(self):
        '''
            Ensure that a user's workoutGroup not marked as finished unless there is at least 1 workout w/ 1 workout item.
        '''

        self.assertEqual(self.workoutgroup_b_unfinished.finished, False)

        workout = Workouts.objects.create(
            group= self.workoutgroup_b_unfinished,
            title= "My first regular workout",
            desc= "testing wod",
            scheme_type= 0,
            # "scheme_rounds": '[]',
        )

        squat = WorkoutNames.objects.get(
            name= 'Squat',
        )

        item = WorkoutItems.objects.create(
            workout= workout,
            name= squat,
            sets= '3',
            reps= '[5]',
            weights= '[135,150,185] ',
            weight_unit= 'lb',
            order= 1
        )
        # Ensure that it marks finished

        res = self.req.post(
            f'/workoutGroups/finish/', {
                "group": self.workoutgroup_b_unfinished.id
            },
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_b}')
        self.assertEqual(res.status_code, 200)

        self.workoutgroup_b_unfinished.refresh_from_db()
        self.assertEqual(self.workoutgroup_b_unfinished.finished, True)

    def test_workoutgroup_completed_if_finished(self):
        '''
            Ensure that a user cannot complete a workout that is marked as not finished.
        '''
        workoutgroup_b_unfinished = WorkoutGroups.objects.create(
            owner_id=self.gym_class_b.id,
            owned_by_class=True,
            title="User B's unfinshed workoutgroup",
            caption="Test desc",
            for_date=tz_aware_today(),
            finished=False
        )

        self.assertEqual(workoutgroup_b_unfinished.finished, False)

        res = self.req.post(
            f'/completedWorkoutGroups/',{
                "workout_group": workoutgroup_b_unfinished.id,
                "title": "Test",
                "caption": "Test",
                "workouts":  "[]",
            },
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_b}')
        self.assertEqual(res.status_code, 200)
        self.assertDictEqual(
            json.loads(res.content.decode()),
            {"error":"Cannot create completedWorkoutGroup for a non finished WorkoutGroup","err_type":0}
        )

    # Test user_a attemp to create/delete WorkoutName, should fail cause they not superuser.
    def test_delete_workoutname(self):
        '''
            Ensure that user A cannot delete a WorkoutName
        '''

        res = self.req.delete(
            f'/workoutNames/{self.squat.id}/',
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
           {'detail': 'Only admins can create/delete workoutNames.'}
        )

    def test_create_workoutname(self):
        '''
            Ensure that user A cannot create a WorkoutName
        '''

        res = self.req.post(
            f'/workoutNames/',{
                "DataDoesntMatter": "Should fail in middeware..."
            },
            HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
           {'detail': 'Only admins can create/delete workoutNames.'}
        )

    def test_workout_delete_if_empty(self):
        '''
            Ensure that a user cannot delete a Workout if it belongs to a finished WorkoutGroup.
        '''

        res = self.req.delete(f'/workouts/{self.workout_b.id}/',HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_b}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
           {'err_type': 0, 'error': 'Cannot remove workouts from finished workout group.'}
        )

    def test_workout_create_under_wrong_gymclass(self):
        '''
            Ensure that a user A cannot create a Workout if it belongs to another user's WorkoutGroup.
        '''

        res = self.req.post(f'/workouts/', {
            "group": self.workoutgroup_b_finished.id,
        }, HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can create/delete workouts for themselves or for a class they own or are a coach of.'}
        )

    def test_workout_create_under_wrong_user(self):
        '''
            Ensure that a user A cannot create a Workout if it belongs to another user.
        '''

        res = self.req.post(f'/workouts/', {
            "group": self.workoutgroup_b.id,
        }, HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can create/delete workouts for themselves or for a class they own or are a coach of.'}
        )

    def test_workout_items_create_under_wrong_user(self):
        '''
            Ensure that user A cannot create a WorkoutItem if it belongs to another user.
        '''
        # Todo finish test... tbelow is just ccopy/paste
        res = self.req.post(f'/workoutItems/items/', {
            "workout": self.workout_b.id,
            "name": self.squat.id,
            "order": 0,
        }, HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can create workout Items for themselves or for a class they own or are a coach of.'}
        )

    def test_workout_items_blocked_create(self):
        '''
            Ensure that user A cannot create a single WorkoutItem.
        '''

        res = self.req.post(f'/workoutItems/', {
            "workout": self.workout_b.id,
            "name": self.squat.id,
            "order": 0,
        }, HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')

        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can create workout Items for themselves or for a class they own or are a coach of.'}
        )

    def test_workout_items_blocked_update(self):
        '''
            Ensure that a user cannot update a WorkoutItem directly.
        '''

        res = self.req.patch(f'/workoutItems/', {
            "workout": self.workout_b.id,
            "name": self.squat.id,
            "order": 0,
        }, HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can create workout Items for themselves or for a class they own or are a coach of.'}
        )

    def test_workout_items_blocked_delete(self):
        '''
            Ensure that a user cannot update a WorkoutItem directly.
        '''

        res = self.req.delete(f'/workoutItems/1/', HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can create workout Items for themselves or for a class they own or are a coach of.'}
        )

    def test_completed_workoutgroup_delete(self):
        '''
            Ensure that user A cannot delete user B's Completed WorkoutGroup.
        '''


        res = self.req.delete(f'/completedWorkoutGroups/{self.completed_workout_group.id}/', HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can create/delete completed workoutgroups for themselves.'}
        )

    def test_completed_workout_delete(self):
        '''
            Ensure that user A cannot delete user B's Completed Workout.
        '''

        res = self.req.delete(f'/completedWorkouts/{self.completed_workout.id}/', HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can create/delete completed workouts for themselves.'}
        )


    def test_completed_workout_create_blocked(self):
        '''
            Ensure that a user can't create a Completed Workout directly.
        '''

        res = self.req.post(f'/completedWorkouts/', {

        }, HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can create/delete completed workouts for themselves.'}
        )

    def test_completed_workout_update_blocked(self):
        '''
            Ensure that a user can't update a Completed Workout directly.
        '''

        res = self.req.put(f'/completedWorkouts/', {

        }, HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can create/delete completed workouts for themselves.'}
        )

    def test_completed_workout_partial_update_blocked(self):
        '''
            Ensure that a user can't update a Completed Workout directly.
        '''

        res = self.req.patch(f'/completedWorkouts/', {

        }, HTTP_AUTHORIZATION= f'Bearer {self.jwt_token_a}')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            json.loads(res.content.decode()),
            {'detail': 'Only users can create/delete completed workouts for themselves.'}
        )

