from django.urls import include, path
from rest_framework import routers
from gyms import views

router = routers.DefaultRouter()
router.register(r'gyms', views.GymViewSet)
router.register(r'gymClasses', views.GymClassViewSet)
router.register(r'workoutGroups', views.WorkoutGroupsViewSet)
router.register(r'workouts', views.WorkoutsViewSet)
router.register(r'workoutNames', views.WorkoutNamesViewSet)
router.register(r'workoutCategories', views.WorkoutCategoriesViewSet)
router.register(r'workoutItems', views.WorkoutItemsViewSet)
router.register(r'workoutDualItems', views.WorkoutDualItemsViewSet)
router.register(r'completedWorkoutGroups', views.CompletedWorkoutGroupsViewSet)
router.register(r'completedWorkouts', views.CompletedWorkoutsViewSet)
router.register(r'coaches', views.CoachesViewSet)
router.register(r'classMembers', views.ClassMembersViewSet)
router.register(r'profile', views.ProfileViewSet, basename='profile')
router.register(r'stats', views.StatsViewSet, basename='stats')
router.register(r'account', views.RemoveAccount, basename='account')
router.register(r'snapshot', views.SnapshotViewSet, basename='snapshot')
# router.register(r'bodyMeasurements', views.BodyMeasurementsViewSet)


# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
]
