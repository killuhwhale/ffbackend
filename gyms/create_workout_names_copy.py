from gyms.models import WorkoutNames, WorkoutCategories
categories = [
    {'title': 'Jiu jitsu',},  # 1
    {'title': 'Weightlifting',},  # 2
    {'title': 'Powerlifting',},  # 3
    {'title': 'Lower body',},  # 4
    {'title': 'Upper body',},  # 5
    {'title': 'Total body',},  # 6
    {'title': 'Boxing',},  # 7
    {'title': 'Running',},  # 8
    {'title': 'Sprinting',},  # 9
    {'title': 'Plyometric',},  # 10
    {'title': 'Jumping',},  # 11
    {'title': 'Gymnastics',},  # 12
    {'title': 'Arms',},  # 13
    {'title': 'Legs',},  # 14
    {'title': 'Squat',},  # 15 Variation of squat
    {'title': 'Deadlift',},  # 16
    {'title': 'Bench',},  # 17
    {'title': 'Clean',},  # 18
    {'title': 'Snatch',},  # 19
    {'title': 'Press',},  # 20
    {'title': 'Overhead press',},  # 21
    {'title': 'Back',},  # 22
    {'title': 'Core',},  # 23
    {'title': 'Shoulder',},  # 24
    {'title': 'Lunge',},  # 25
    {'title': 'Pullup',},  # 26
    {'title': 'Rowing',},  # 27
    # Muscle groups for body-builders
]
for cat in categories:
    try:
        WorkoutCategories.objects.create(**cat)
    except Exception as e:
        print("Err creating categories ", e)

workout_names = [
{'name': 'Air Squat', 'desc': 'Bodyweight squat with arms extended.', 'categories': [3, 4, 14, 15], 'primary_id': 15, 'secondary_id': 1},
{'name': 'Back Extension', 'desc': 'Lower back strengthening exercise with hands behind the head or across the chest.', 'categories': [22, 23], 'primary_id': 23, 'secondary_id': 1},
{'name': 'Bar Hang', 'desc': 'Hanging from a bar with arms fully extended to improve grip strength and shoulder mobility.', 'categories': [22], 'primary_id': 22, 'secondary_id': 1},
{'name': 'Bar Muscle Up', 'desc': 'A gymnastics move where an athlete pulls their entire body over a bar and then back down.', 'categories': [12], 'primary_id': 12, 'secondary_id': 1},
{'name': 'Barbell Curl', 'desc': 'Weightlifting exercise targeting the biceps, using a barbell and an underhand grip.', 'categories': [5, 13], 'primary_id': 13, 'secondary_id': 1},
{'name': 'Barbell Lunge', 'desc': 'Lunge exercise that utilizes a barbell on the back of the shoulders.', 'categories': [4, 25], 'primary_id': 25, 'secondary_id': 1},
{'name': 'Barbell Row', 'desc': 'Weightlifting exercise where a barbell is pulled towards the chest while maintaining a flat back.', 'categories': [22], 'primary_id': 22, 'secondary_id': 1},
{'name': 'Behind the Neck Press', 'desc': 'Should press starting from behind the neck.', 'categories': [24], 'primary_id': 24, 'secondary_id': 1},
{'name': 'Dips', 'desc': 'Dips performed with the body leaning slightly forward to target the triceps and chest.', 'categories': [13], 'primary_id': 1, 'secondary_id': 13},
{'name': 'Bench Press', 'desc': 'Weightlifting exercise performed lying down, targeting the chest, shoulders, and triceps.', 'categories': [13, 5, 20], 'primary_id': 17, 'secondary_id': 1},
{'name': 'Block Snatch', 'desc': 'Olympic weightlifting movement that involves pulling a barbell from the ground to overhead in one motion, with a pause just above the knees.', 'categories': [2, 4, 5, 19], 'primary_id': 19, 'secondary_id': 1},
{'name': 'Box Jumps', 'desc': 'Plyometric exercise that involves jumping onto a box.', 'categories': [4,11], 'primary_id': 1, 'secondary_id': 10},
{'name': 'Box Squat', 'desc': 'Squat variation that involves sitting back onto a box, then standing up again.', 'categories': [3, 4, 14, 15], 'primary_id': 15, 'secondary_id': 1},
{'name': 'Bulgarian Split Squat', 'desc': 'Lunge variation that involves placing the rear foot on a bench or elevated surface.', 'categories': [3, 4, 14, 15,25], 'primary_id': 25, 'secondary_id': 1},
{'name': 'Burpees', 'desc': 'Full-body exercise that involves squatting, kicking the feet back into a plank, performing a push-up, then returning to a squat and jumping.', 'categories': [10], 'primary_id': 6, 'secondary_id': 1},
{'name': 'Chin-Up', 'desc': 'Pull-up variation with an underhand grip, targeting the biceps and back muscles.', 'categories': [5,22,26], 'primary_id': 26, 'secondary_id': 1},
{'name': 'Clean', 'desc': 'Olympic weightlifting movement that involves pulling a barbell from the ground to the shoulders.', 'categories': [2, 4, 18], 'primary_id': 18, 'secondary_id': 1},
{'name': 'Clean and Jerk', 'desc': 'Olympic weightlifting movement that involves pulling a barbell from the ground to the shoulders, then pushing it overhead.', 'categories': [2, 4, 5,6, 18], 'primary_id': 18, 'secondary_id': 1},
{'name': 'Close-Grip Bench Press', 'desc': 'Bench Press variation with a narrower grip, targeting the triceps.', 'categories': [5, 13, 20], 'primary_id': 17, 'secondary_id': 1},
{'name': 'Crunch', 'desc': 'Abdominal exercise that involves curling the upper body towards the knees.', 'categories': [23], 'primary_id': 1, 'secondary_id': 23},
{'name': 'Deadbugs', 'desc': 'Abdominal exercise that involves lying on the back and extending opposite arms and legs.', 'categories': [23], 'primary_id': 23, 'secondary_id': 1},
{'name': 'Deadlift', 'desc': 'Weightlifting exercise that targets the lower body and back muscles.', 'categories': [3, 4, 14, 16], 'primary_id': 16, 'secondary_id': 1},
{'name': 'Decline Bench Press', 'desc': 'Bench Press performed on a decline bench, targeting the lower portion of the chest.', 'categories': [5, 13, 20], 'primary_id': 17, 'secondary_id': 1},
{'name': 'Deficit Deadlift', 'desc': 'Deadlift variation with the feet standing on a platform or weight plate to increase range of motion.', 'categories': [3, 4, 14, 16], 'primary_id': 16, 'secondary_id': 1},
{'name': 'Double Unders', 'desc': 'Jump rope exercise that involves passing the rope twice under the feet during each jump.', 'categories': [10], 'primary_id': 10, 'secondary_id': 1},
{'name': 'Dumbbell Chest Fly', 'desc': 'An exercise performed lying down on the back spreading the arms to the side with dumbells.', 'categories': [5, 13], 'primary_id': 5, 'secondary_id': 1},
{'name': 'Dumbbell Chest Press', 'desc': 'Chest Press exercise performed with dumbbells instead of a barbell.', 'categories': [5, 13], 'primary_id': 17, 'secondary_id': 1},
{'name': 'Dumbbell Curl', 'desc': 'Bicep curl exercise performed with dumbbells instead of a barbell.', 'categories': [5, 13], 'primary_id': 13, 'secondary_id': 1},
{'name': 'Dumbbell Decline Chest Press', 'desc': 'Bench Press performed on a decline bench with dumbbells instead of a barbell.', 'categories': [5, 13], 'primary_id': 17, 'secondary_id': 1},
{'name': 'Dumbbell Front Raise', 'desc': 'Shoulder exercise that involves lifting dumbbells in front of the body.', 'categories': [5, 13], 'primary_id': 13, 'secondary_id': 1},
{'name': 'Dumbbell Lunge', 'desc': 'Lunge exercise performed with dumbbells.', 'categories': [4, 14], 'primary_id': 25, 'secondary_id': 1},
{'name': 'Dumbbell Pullover', 'desc': 'Back exercise that involves lying on a bench and lowering a dumbbell behind the head.', 'categories': [5, 13, 22], 'primary_id': 22, 'secondary_id': 1},
{'name': 'Dumbbell Rear Delt Row', 'desc': 'Shoulder exercise that involves lifting dumbbells to the sides of the body.', 'categories': [5, 13], 'primary_id': 22, 'secondary_id': 1},
{'name': 'Dumbbell Romanian Deadlift', 'desc': 'Romanian deadlift with dumbbells, targeting the posterior chain muscles of the legs and glutes', 'categories': [3, 4, 14, 16], 'primary_id': 16, 'secondary_id': 1},
{'name': 'Dumbbell Row', 'desc': 'Bent-over row with dumbbells, targeting the back muscles, particularly the lats', 'categories': [5, 13, 22], 'primary_id': 22, 'secondary_id': 1},
{'name': 'Dumbbell Shoulder Press', 'desc': 'Shoulder press or overhead press with dumbbells, targeting the shoulder muscles', 'categories': [5, 13, 24], 'primary_id': 21, 'secondary_id': 1},
{'name': 'Dumbbell Shrug', 'desc': 'Shrug movement with dumbbells, targeting the trapezius muscles of the upper back', 'categories': [5, 13], 'primary_id': 5, 'secondary_id': 1},
{'name': 'Farmers Walk', 'desc': 'Walking while holding weights in each hand, targeting the grip and overall strength and endurance of the upper body and core', 'categories': [6], 'primary_id': 6, 'secondary_id': 1},
{'name': 'Front Squat', 'desc': 'Squatting with the barbell resting on the front of the shoulders, targeting the quadriceps, hamstrings, and glutes', 'categories': [4, 14, 15], 'primary_id': 15, 'secondary_id': 1},
{'name': 'Goblet Squat', 'desc': 'Squatting with a kettlebell or dumbbell held at chest level, targeting the same muscles as the front squat', 'categories': [4, 14, 15], 'primary_id': 15, 'secondary_id': 1},
{'name': 'Good Morning', 'desc': 'Hinging at the hips while holding a barbell, targeting the posterior chain muscles of the legs and glutes', 'categories': [4, 14], 'primary_id': 14, 'secondary_id': 1},
{'name': 'Hammer Curl', 'desc': 'Curling dumbbells with a neutral grip, targeting the biceps', 'categories': [5, 13], 'primary_id': 13, 'secondary_id': 1},
{'name': 'Handstand Push Up', 'desc': 'Pushing the body up while in a handstand position, targeting the shoulder muscles', 'categories': [5, 13, 24], 'primary_id': 24, 'secondary_id': 1},
{'name': 'Handstand Walk', 'desc': 'Walking on the hands while maintaining a handstand position, targeting the core and upper body strength and stability', 'categories': [5, 13, 24], 'primary_id': 24, 'secondary_id': 1},
{'name': 'Hang Clean', 'desc': 'Olympic weightlifting movement involving lifting the barbell from a hanging position, targeting the explosive power and strength of the legs and back', 'categories': [2, 5,13, 18], 'primary_id': 18, 'secondary_id': 1},
{'name': 'Hang Power Clean', 'desc': 'Similar to the hang clean, but the movement ends with the barbell at shoulder height instead of the front rack position', 'categories': [2, 4, 18], 'primary_id': 18, 'secondary_id': 1},
{'name': 'Hang Power Snatch', 'desc': 'Olympic weightlifting movement involving lifting the barbell from a hanging position overhead in one fluid motion, targeting the same muscles as the hang clean', 'categories': [2, 4, 5, 19], 'primary_id': 19, 'secondary_id': 1},
{'name': 'Hang Snatch', 'desc': 'A variation of the snatch starting off the floor.', 'categories': [2, 4, 5, 19], 'primary_id': 19, 'secondary_id': 1},
{'name': 'Hanging Leg Raises', 'desc': 'Hanging from a bar and raising the legs up to the chest or higher, targeting the core muscles', 'categories': [23], 'primary_id': 23, 'secondary_id': 1},
{'name': 'Heel Touch', 'desc': 'Lying on the back and touching the heels with the fingertips, targeting the abdominal muscles', 'categories': [23], 'primary_id': 23, 'secondary_id': 1},
{'name': 'Hip Abduction', 'desc': 'Moving the legs away from the midline of the body while lying on the side, targeting the hip abductor muscles', 'categories': [4, 14], 'primary_id': 14, 'secondary_id': 1},
{'name': 'Hip Adduction', 'desc': 'Moving the legs toward the midline of the body while lying on the side, targeting the hip adductor muscles', 'categories': [4,14], 'primary_id': 14, 'secondary_id': 1},
{'name': 'Hip Thrust', 'desc': 'Hinging at the hips while the shoulders are elevated on a bench, targeting the glute muscles', 'categories': [4, 14 ], 'primary_id': 14, 'secondary_id': 1},
{'name': 'Incline Bench Press', 'desc': 'Bench press performed on an inclined bench, targeting the upper portion of the chest muscles', 'categories': [5,13, 20], 'primary_id': 5, 'secondary_id': 1},
{'name': 'Incline Dumbbell Press', 'desc': 'Dumbbell press performed on an inclined bench, targeting the same muscles as the incline bench press', 'categories': [5,13], 'primary_id': 5, 'secondary_id': 1},
{'name': 'JuiJitsu', 'desc': 'Martial art involving grappling and submission holds, targeting overall strength, endurance, and flexibility', 'categories': [1], 'primary_id': 1, 'secondary_id': 1},
{'name': 'Kettlebell Swing', 'desc': 'Swinging a kettlebell between the legs and up to shoulder height, targeting the posterior chain muscles of the legs and glutes', 'categories': [6], 'primary_id': 6, 'secondary_id': 1},
{'name': 'Landmine', 'desc': 'Exercise involving a barbell anchored at one end and held at the other, targeting various muscle groups depending on the movement', 'categories': [23], 'primary_id': 23, 'secondary_id': 1},
{'name': 'Leg Extension', 'desc': 'Extension movement of the legs while seated, targeting the quadriceps muscles', 'categories': [4, 14], 'primary_id': 4, 'secondary_id': 1},
{'name': 'Leg Press', 'desc': 'Pressing weight away with the legs while seated, targeting the same muscles as the squat', 'categories': [4, 14], 'primary_id': 4, 'secondary_id': 1},
{'name': 'Leg Curl', 'desc': 'Curling the legs toward the buttocks while lying on the stomach, targeting the hamstrings muscles', 'categories': [4, 14], 'primary_id': 4, 'secondary_id': 1},
{'name': 'Leg Raise', 'desc': 'Lying on the back and raising the legs up to the chest or higher, targeting the abdominal muscles', 'categories': [4, 14], 'primary_id': 4, 'secondary_id': 1},
{'name': 'Mountain Climbers', 'desc': 'Alternating leg movement resembling climbing, targeting the core and cardiovascular endurance', 'categories': [23], 'primary_id': 23, 'secondary_id': 1},
{'name': 'Overhead Squat', 'desc': 'Squatting with the barbell held overhead, targeting the same muscles as the front squat and shoulder muscles', 'categories': [4, 14, 15, 24], 'primary_id': 15, 'secondary_id': 1},
{'name': 'Paused Deadlift', 'desc': 'Deadlift movement with a pause at the mid-shin level', 'categories': [3, 4, 14, 16], 'primary_id': 16, 'secondary_id': 1},
{'name': 'Paused Squat', 'desc': 'A squat variation where the lifter pauses at the bottom of the squat for a predetermined amount of time before standing back up.', 'categories': [3, 4, 14, 15], 'primary_id': 15, 'secondary_id': 1},
{'name': 'Pendlay Row', 'desc': 'A type of rowing exercise where the barbell is lifted off the ground for each repetition and then lowered back down in a controlled manner.', 'categories': [22, 4,5], 'primary_id': 22, 'secondary_id': 1},
{'name': 'Plank', 'desc': 'An isometric exercise where the body is held in a straight line from head to heels in a push-up position, with the elbows or hands on the ground.', 'categories': [23], 'primary_id': 23, 'secondary_id': 1},
{'name': 'Power Clean', 'desc': 'A weightlifting exercise where the barbell is explosively lifted from the ground to the shoulders in one motion.', 'categories': [2, 4, 18], 'primary_id': 18, 'secondary_id': 1},
{'name': 'Power Jerk', 'desc': 'A weightlifting exercise where the barbell is explosively lifted from the shoulders to overhead, with a slight dip of the legs before driving the barbell up with the arms and legs.', 'categories': [21, 24], 'primary_id': 21, 'secondary_id': 1},
{'name': 'Power Snatch', 'desc': 'A weightlifting exercise where the barbell is explosively lifted from the ground to overhead in one motion.', 'categories': [2, 4, 5, 19], 'primary_id': 19, 'secondary_id': 1},
{'name': 'Pull Up', 'desc': 'An upper body exercise where the body is lifted up towards a bar with the arms until the chin is above the bar.', 'categories': [5,22], 'primary_id': 26, 'secondary_id': 1},
{'name': 'Push Press', 'desc': 'A weightlifting exercise where the barbell is lifted from the shoulders to overhead with the assistance of the legs.', 'categories': [24, 5], 'primary_id': 21, 'secondary_id': 1},
{'name': 'Push-Up', 'desc': 'An exercise where the body is lowered towards the ground and then pushed back up using the arms and chest muscles.', 'categories': [5, 20], 'primary_id': 5, 'secondary_id': 1},
{'name': 'Reverse Flyes', 'desc': 'An exercise where the arms are lifted away from the body in a reverse motion, targeting the muscles of the upper back and shoulders.', 'categories': [22], 'primary_id': 22, 'secondary_id': 1},
{'name': 'Reverse Hyper Ext', 'desc': 'An exercise machine where the lower body is suspended in the air while the upper body is held in place, targeting the lower back and glutes.', 'categories': [23], 'primary_id': 23, 'secondary_id': 1},
{'name': 'Ring Handstand Push Up', 'desc': 'An exercise where the body is held in a handstand position using gymnastic rings for support.', 'categories': [24], 'primary_id': 24, 'secondary_id': 1},
{'name': 'Ring Muscle Up', 'desc': 'A gymnastic exercise where the body is lifted up and over the rings, targeting the muscles of the upper body.', 'categories': [5,22], 'primary_id': 22, 'secondary_id': 1},
{'name': 'Romanian Deadlift', 'desc': 'A deadlift variation where the barbell is lowered to the shins and then lifted back up, targeting the muscles of the lower back and hamstrings.', 'categories': [3, 4, 14, 16], 'primary_id': 16, 'secondary_id': 1},
{'name': 'Rope Climbing', 'desc': 'An exercise where the body is pulled up a rope using the arms and upper body strength.', 'categories': [22, 6], 'primary_id': 6, 'secondary_id': 1},
{'name': 'Rowing', 'desc': 'A cardiovascular exercise where the body is propelled forward on a machine using a rowing motion.', 'categories': [6, 22, 27], 'primary_id':22, 'secondary_id': 1},
{'name': 'Run', 'desc': 'A cardiovascular exercise where the body runs or jogs on a treadmill or outside.', 'categories': [8], 'primary_id': 8, 'secondary_id': 1},
{'name': 'Side Plank', 'desc': 'An isometric exercise where the body is held in a straight line from head to heels in a side position, with one elbow or hand on the ground.', 'categories': [23], 'primary_id': 23, 'secondary_id': 1},
{'name': 'Sit-Up', 'desc': 'An exercise where the body is lifted from a lying down position to a seated position using the abdominal muscles.', 'categories': [23], 'primary_id': 23, 'secondary_id': 1},
{'name': 'Snatch', 'desc': 'A weightlifting exercise where the barbell is lifted from the ground to overhead in one motion.', 'categories': [2, 4, 5, 19], 'primary_id': 19, 'secondary_id': 1},
{'name': 'Snatch Grip Behind the Neck Press', 'desc': 'A variation of the snatch exercise where the lifter uses a wider grip on the barbell.', 'categories': [2, 5, 19, 21], 'primary_id': 21, 'secondary_id': 1},
{'name': 'Snatch Grip Deadlift', 'desc': 'A deadlift performed with a snatch grip.', 'categories': [2,3, 4, 16, 19], 'primary_id': 16, 'secondary_id': 1},
{'name': 'Split Jerk', 'desc': 'A weightlifting exercise where the barbell is lifted from the shoulders to overhead with a split stance of the legs.', 'categories': [21, 24], 'primary_id': 21, 'secondary_id': 1},
{'name': 'Sprint', 'desc': 'A high intensity cardiovascular exercise where the body runs or sprints at a fast pace.', 'categories': [8, 9], 'primary_id': 9, 'secondary_id': 1},
{'name': 'Squat', 'desc': 'An exercise where the body is lowered down into a sitting position and then lifted back up, targeting the muscles of the legs and glutes.', 'categories': [3, 4, 14, 15], 'primary_id': 15, 'secondary_id': 1},
{'name': 'Squat Jerk', 'desc': 'A weightlifting exercise where the barbell is lifted from the shoulders to overhead with a squat stance of the legs.', 'categories': [4, 24, 21], 'primary_id': 21, 'secondary_id': 1},
{'name': 'Step Up', 'desc': 'An exercise where the body steps up onto a platform or bench using the leg muscles.', 'categories': [4], 'primary_id': 4, 'secondary_id': 1},
{'name': 'Sumo Deadlift', 'desc': 'A deadlift variation where the feet are placed in a wider stance and the grip is between the legs, targeting the muscles of the inner thighs and lower back.', 'categories': [3, 4, 14, 16], 'primary_id': 16, 'secondary_id': 1},
{'name': 'Thruster‘', 'desc': 'A weightlifting exercise where the barbell is lifted from the shoulders to overhead with', 'categories': [6,24,15, 21], 'primary_id': 6, 'secondary_id': 1},
{'name': 'Tricep Extension', 'desc': 'Tricep extension is an isolation exercise that targets the triceps muscles. It is typically performed with a cable machine or dumbbell, and involves extending the arm at the elbow joint to activate the triceps.', 'categories': [5,13], 'primary_id': 13, 'secondary_id': 1},
{'name': 'Wall Balls', 'desc': 'Wall balls are a functional fitness exercise that involves throwing a weighted ball against a wall and catching it as it comes back down. This exercise targets several muscle groups including the legs, hips, core, shoulders, and arms. It is often used in CrossFit and other high-intensity training programs.', 'categories': [6, 15, 24], 'primary_id': 6, 'secondary_id': 1},
{'name': 'Windshield Wiper', 'desc': 'The windshield wiper exercise is a core strengthening exercise that targets the obliques and lower abs. It involves lying on the back with the legs raised and extended, and then moving the legs from side to side in a "windshield wiper" motion. This exercise is typically performed on a mat or bench, and can be modified to increase or decrease the difficulty level.', 'categories': [23], 'primary_id': 23, 'secondary_id': 1},
]
for wname in workout_names:
    # cats = [cat + 23 for cat in wname['categories']]
    cats = [cat for cat in wname['categories']]
    del wname['categories']
    # wname['primary_id'] += 23
    # wname['secondary_id'] += 23
    try:
        new_obj = WorkoutNames.objects.create(**wname)
        new_obj.categories.set(cats)
        new_obj.save
    except Exception as e:
        print("Error creating workout name", e)




























































































