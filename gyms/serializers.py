from importlib.metadata import requires
from django.core.serializers import serialize
from itertools import chain
from rest_framework import serializers
from gyms.models import (
    BodyMeasurements, CompletedWorkoutGroups, CompletedWorkoutItems, CompletedWorkouts, GymClassFavorites, ClassMembers, Coaches,
    Gyms, GymClasses, GymFavorites, LikedWorkouts, WorkoutCategories,
    Workouts, WorkoutItems, WorkoutNames, WorkoutGroups)


class Gym_ClassSerializer(serializers.ModelSerializer):
    ''' Searilzier gym_class for gym list. Avoid circular dependency'''
    class Meta:
        model = GymClasses
        fields = '__all__'


class GymSerializer(serializers.ModelSerializer):
    gym_classes = serializers.SerializerMethodField()

    class Meta:
        model = Gyms
        fields = '__all__'

    def get_gym_classes(self, instance):
        print('Gym View instance: ', instance)
        classes = instance.gymclasses_set.order_by('-date')
        return Gym_ClassSerializer(classes, many=True, required=False).data


class GymSerializerWithoutClasses(serializers.ModelSerializer):
    # Adding this made me unable to create a gym without add gym_classes

    class Meta:
        model = Gyms
        fields = '__all__'


class GymClassSerializer(serializers.ModelSerializer):
    ''' Serialize gym_class for gym_class list.'''
    gym = GymSerializerWithoutClasses(required=False)

    class Meta:
        model = GymClasses
        fields = '__all__'


class GymClassCreateSerializer(serializers.ModelSerializer):
    ''' Serialize gym_class for gym_class list.'''

    class Meta:
        model = GymClasses
        fields = '__all__'


class WorkoutCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutCategories
        fields = '__all__'


class WorkoutNamesSerializer(serializers.ModelSerializer):
    primary = WorkoutCategorySerializer(required=False)
    secondary = WorkoutCategorySerializer(required=False)
    categories = WorkoutCategorySerializer(many=True, required=False)

    class Meta:
        model = WorkoutNames
        fields = '__all__'


class CompletedWorkoutItemSerializer(serializers.ModelSerializer):
    name = WorkoutNamesSerializer()

    class Meta:
        model = CompletedWorkoutItems
        fields = '__all__'


class CompletedWorkoutItemCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = CompletedWorkoutItems
        fields = '__all__'


class CompletedWorkoutSerializer(serializers.ModelSerializer):
    completed_workout_items = CompletedWorkoutItemSerializer(
        source='completedworkoutitems_set',  many=True, required=False)

    class Meta:
        model = CompletedWorkouts
        exclude = ('completed_workout_group', )
        depth = 2


class CompletedWorkoutCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = CompletedWorkouts
        fields = '__all__'


class CompletedWorkoutGroupsSerializer(serializers.ModelSerializer):
    completed_workouts = CompletedWorkoutSerializer(
        source="completedworkouts_set", many=True, required=False)

    class Meta:
        model = CompletedWorkoutGroups
        fields = '__all__'
        depth = 2


class CompletedWorkoutGroupsNoWorkoutsSerializer(serializers.ModelSerializer):
    completed = serializers.BooleanField(default=True)

    class Meta:
        model = CompletedWorkoutGroups
        fields = '__all__'


# Create a stats class serializer to return a list of WOrkout Groups for
#  Completed WOrkouts and Workouts Groups By User/Not by Class that


########################################################
#   ////////////////////////////////////////////////   #
########################################################

class WorkoutItemSerializer(serializers.ModelSerializer):
    name = WorkoutNamesSerializer()

    class Meta:
        model = WorkoutItems
        fields = '__all__'


class WorkoutItemCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = WorkoutItems
        fields = '__all__'


class WorkoutSerializer(serializers.ModelSerializer):
    workout_items = WorkoutItemSerializer(
        source='workoutitems_set',  many=True, required=False)

    class Meta:
        model = Workouts
        # exclude = ('group', )
        fields = '__all__'
        depth = 1


class WorkoutCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Workouts
        fields = '__all__'


class WorkoutGroupsNoWorkoutsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutGroups
        fields = '__all__'


class WorkoutGroupsSerializer(serializers.ModelSerializer):
    workouts = WorkoutSerializer(
        source="workouts_set", many=True, required=False)

    completed = serializers.SerializerMethodField('has_completed')

    def has_completed(self, workout_group):
        print("Has completed: (WorkoutGroupsSerializer)",
              workout_group,  self.context)

        return CompletedWorkoutGroups.objects.filter(
            workout_group_id=workout_group.id,
            user_id=self.context["request"].user.id
        ).exists()

    class Meta:
        model = WorkoutGroups
        fields = '__all__'
        depth = 2


class WorkoutGroupsCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = WorkoutGroups
        fields = '__all__'


class WorkoutGroupsHasCompletedSerializer(serializers.ModelSerializer):
    completed = serializers.SerializerMethodField('has_completed')

    def has_completed(self, workout_group):
        print("Has completed: ", workout_group.id,  self.context)

        return CompletedWorkoutGroups.objects.filter(
            workout_group_id=workout_group.id,
            user_id=self.context["request"].user.id
        ).exists()

    class Meta:
        model = WorkoutGroups
        fields = '__all__'


class WorkoutGroupsAutoCompletedSerializer(serializers.ModelSerializer):
    '''
        If a user creates their own WorkoutGroup it should be considered completed.
    '''
    completed = serializers.SerializerMethodField('has_completed')

    def has_completed(self, workout_group):
        return str(self.context["request"].user.id) == str(workout_group.owner_id)

    class Meta:
        model = WorkoutGroups
        fields = '__all__'


class CombinedWorkoutGroupsSerializer(serializers.Serializer):
    created_workout_groups = WorkoutGroupsSerializer(many=True, required=False)
    completed_workout_groups = CompletedWorkoutGroupsSerializer(
        many=True, required=False)


class CombinedWorkoutsSerializer(serializers.Serializer):
    '''
        Goal is to return a single list of data w/ the keys:
        scheme_rounds,
        scheme_type,

        Front end will handle which items are there.
        workout_items -- OR --
        completed_workout_items
    '''


class CombinedWorkoutGroupsAsWorkoutGroupsSerializer(serializers.Serializer):
    '''
        Used to serialized all workouts for a user between their own created 
            and Completed workouts.
    '''
    workout_groups = serializers.SerializerMethodField()

    def get_workout_groups(self, instance):
        print("Instance: ", instance)
        print("Context: ", self.context)
        wgs = instance['created_workout_groups'].order_by('for_date')
        cwgs = instance['completed_workout_groups'].order_by('for_date')
        return serialize('json', list(chain(wgs, cwgs)))


class CombinedWorkoutGroupsSerializerNoWorkouts(serializers.Serializer):
    # created_workout_groups = WorkoutGroupsNoWorkoutsSerializer(
    #     many=True, required=False)
    created_workout_groups = serializers.SerializerMethodField()
    completed_workout_groups = serializers.SerializerMethodField()
    # created_workout_groups = WorkoutGroupsAutoCompletedSerializer(
    #     many=True, required=False)
    # completed_workout_groups = CompletedWorkoutGroupsNoWorkoutsSerializer(
    #     many=True, required=False)

    def get_created_workout_groups(self, instance):
        print("Instance: ", instance)
        print("Context: ", self.context)
        cwgs = instance['created_workout_groups'].order_by('for_date')
        print("This should be sorted by for_date", cwgs)

        return WorkoutGroupsAutoCompletedSerializer(cwgs, context=self.context,
                                                    many=True, required=False).data

    def get_completed_workout_groups(self, instance):
        wgs = instance['completed_workout_groups'].order_by('for_date')
        return CompletedWorkoutGroupsNoWorkoutsSerializer(wgs, context=self.context,
                                                          many=True, required=False).data


########################################################
#   ////////////////////////////////////////////////   #
########################################################


class GymClassSerializerWithWorkouts(serializers.ModelSerializer):
    ''' Serialize Class with its workouts.'''
    workout_groups = WorkoutGroupsCreateSerializer(
        source="workoutgroups_set", many=True, required=False)

    class Meta:
        model = GymClasses
        fields = '__all__'


class GymClassSerializerWithWorkoutsCompleted(serializers.ModelSerializer):
    ''' Serialize Class with its workouts and if the current user is an owner, coach or member.'''
    workout_groups = WorkoutGroupsHasCompletedSerializer(
        source="workoutgroups_set", many=True, required=False)

    class Meta:
        model = GymClasses
        fields = '__all__'


class CoachesSerializer(serializers.ModelSerializer):
    gym_class = GymClassSerializer(required=False)

    class Meta:
        model = Coaches
        fields = '__all__'


class CoachesCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Coaches
        fields = '__all__'


class ClassMembersSerializer(serializers.ModelSerializer):
    gym_class = GymClassSerializer(required=False)

    class Meta:
        model = ClassMembers
        fields = '__all__'


class ClassMembersCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ClassMembers
        fields = '__all__'


class GymClassFavoritesSerializer(serializers.ModelSerializer):
    gym_class = GymClassSerializer()

    class Meta:
        model = GymClassFavorites
        fields = '__all__'


class GymFavoritesSerializer(serializers.ModelSerializer):
    gym = GymSerializerWithoutClasses()

    class Meta:
        model = GymFavorites
        fields = '__all__'


class LikedWorkoutsSerializer(serializers.ModelSerializer):
    workout = WorkoutSerializer()

    class Meta:
        model = LikedWorkouts
        fields = '__all__'


class BodyMeasurementsSerializer(serializers.ModelSerializer):

    class Meta:
        model = BodyMeasurements
        fields = '__all__'


class UserSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.CharField(required=False)
    id = serializers.IntegerField()


class UserWithoutEmailSerializer(serializers.Serializer):
    username = serializers.CharField()
    id = serializers.IntegerField()


class ProfileWorkoutGroupsSerializer(serializers.Serializer):
    workout_groups = CombinedWorkoutGroupsSerializerNoWorkouts(required=False)


class ProfileGymFavoritesSerializer(serializers.Serializer):
    favorite_gyms = GymFavoritesSerializer(many=True, required=False)


class ProfileGymClassFavoritesSerializer(serializers.Serializer):
    favorite_gym_classes = GymClassFavoritesSerializer(
        many=True, required=False)


class ProfileSerializer(serializers.Serializer):
    user = UserSerializer()
    measurements = BodyMeasurementsSerializer(many=True, required=False)
