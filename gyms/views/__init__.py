from .helpers import delete_media, FILES_KINDS
from .gyms import GymViewSet, GymClassViewSet
from .workouts import WorkoutGroupsViewSet, WorkoutsViewSet
from .workout_items import (
    WorkoutItemsViewSet,
    WorkoutDualItemsViewSet,
    WorkoutNamesViewSet,
    WorkoutCategoriesViewSet,
)
from .completed import CompletedWorkoutGroupsViewSet, CompletedWorkoutsViewSet
from .members import CoachesViewSet, ClassMembersViewSet
from .user import ProfileViewSet, WorkoutMaxViewSet, BodyMeasurementsViewSet, RemoveAccount
from .ai import AIViewSet
from .bulk import BulkTemplateViewSet
from .stats import StatsViewSet, SnapshotViewSet, AppControlViewSet
