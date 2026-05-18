"""
One-shot script to seed Lat Pulldown into WorkoutNames.

Run with:
  docker compose -f docker-compose_prod.yml exec -T instafitapiprod \
    python manage.py shell < gyms/seed_lat_pulldown.py
"""
import logging
from gyms.models import WorkoutNames, WorkoutCategories

logger = logging.getLogger(__name__)
DEADLIFT_CAT_ID = 2  # "Deadlift" category (rows/pulls)

name = "Lat Pulldown"
desc = "Cable machine exercise pulling a bar down to the upper chest, targeting the latissimus dorsi and biceps."

try:
    obj, created = WorkoutNames.objects.get_or_create(
        name=name,
        defaults={
            "desc": desc,
            "primary_id": DEADLIFT_CAT_ID,
            "secondary_id": DEADLIFT_CAT_ID,
        },
    )
    if created:
        obj.categories.set([DEADLIFT_CAT_ID])
        obj.save()
        logger.info("[OK] Created '%s' (id=%s)", name, obj.pk)
    else:
        logger.info("[SKIP] '%s' already exists (id=%s)", name, obj.pk)
except Exception as e:
    logger.exception("[ERROR] Failed to create '%s'", name)
