import json
from django.core.management.base import BaseCommand
from django.utils import timezone

from gyms.models import Workouts, WorkoutItems, WorkoutNames

# map your integer scheme_type → text
SCHEME_TYPE_MAP = {
    0: "Standard",
    1: "Reps",
    2: "Rounds",
    2: "Creative",
}

class Command(BaseCommand):
    help = "Export existing workouts into JSONL for fine‑tuning"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            "-o",
            type=str,
            default="workout_finetune.jsonl",
            help="Path to write the JSONL file",
        )

    def handle(self, *args, **options):
        out_path = options["output"]
        count = 0

        with open(out_path, "w", encoding="utf-8") as fp:
            for w in Workouts.objects.all():
                # build prompt
                scheme_text = SCHEME_TYPE_MAP.get(w.scheme_type, "Unknown")
                prompt = (
                    f"### System:\n"
                    f"You are a strength coach. Always return a JSON array under the key \"workout\"\n"
                    f"without markdown. Keys: name (string), sets (int), reps (int or [int]), "
                    f"weights (optional [int]), duration (optional int), distance (optional int).\n"
                    f"### User:\n"
                    f"Title: {w.title}\n"
                    f"Description: {w.desc}\n"
                    f"Scheme: {scheme_text}\n"
                    f"Rounds/Rep Scheme: {w.scheme_rounds}\n\n"
                )

                # gather items
                items_qs = (
                    WorkoutItems.objects.filter(workout=w)
                    .select_related("name")
                    .order_by("order")
                )
                items_list = []
                for it in items_qs:
                    items_list.append({
                        "name":        it.name.name,
                        "sets":        it.sets,
                        # parse the stored JSON strings
                        "reps":        json.loads(it.reps),
                        "weights":     json.loads(it.weights),
                        "duration":    json.loads(it.duration),
                        "distance":    json.loads(it.distance),
                        "pause":       it.pause_duration,
                        "rest":        it.rest_duration,
                        "percent_of":  it.percent_of or None,
                        "ssid":        it.ssid,
                    })

                completion = json.dumps({"workout": items_list}, separators=(",", ":"))

                # write JSONL line
                record = {"prompt": prompt, "completion": completion}
                fp.write(json.dumps(record) + "\n")
                count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Exported {count} workouts to {out_path}"
        ))
