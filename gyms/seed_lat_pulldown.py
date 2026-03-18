"""
One-shot script to seed Lat Pulldown into WorkoutNames.

Run with:
  docker compose -f docker-compose_prod.yml exec -T instafitapiprod \
    python manage.py shell < gyms/seed_lat_pulldown.py
"""
from gyms.models import WorkoutNames, WorkoutCategories

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
        print(f"[OK] Created '{name}' (id={obj.pk})")
    else:
        print(f"[SKIP] '{name}' already exists (id={obj.pk})")
except Exception as e:
    print(f"[ERROR] Failed to create '{name}': {e}")
