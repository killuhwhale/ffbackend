from gyms.models import WorkoutNames, WorkoutCategories

categories = [
    {'title': 'Squat'},         # all squat variations
    {'title': 'Deadlift'},      # all rowing/pulling movements
    {'title': 'Power Clean'},   # dynamic pulls (cleans, swings, snatches)
    {'title': 'Press'},         # all presses (bench, overhead, dips, etc.)
    {'title': 'Core'},          # abs, anti‑extension/rotation
    {'title': 'Cardio'},        # steady‑state/endurance machines & runs
    {'title': 'Sprinting'},     # fast‑twitch cardio (sprints, hill sprints)
    {'title': 'Gymnastics'},    # body‑weight skills (muscle‑ups, handstands, etc.)
    {'title': 'Plyometric'},    # jumps, hops, explosive lower‑body drills
    {'title': 'Grappling'},     # jiu‑jitsu & wrestling drills
    {'title': 'Striking'},      # boxing, kickboxing, striking drills
]

new_categories = {
    'Squat': 1,
    'Deadlift': 2,
    'Power Clean': 3,
    'Press': 4,
    'Core': 5,
    'Cardio': 6,
    'Sprinting': 7,
    'Gymnastics': 8,
    'Plyometric': 9,
    'Grappling': 10,
    'Striking': 11
}


for cat in categories:
    try:
        WorkoutCategories.objects.create(**cat)
    except Exception as e:
        print('Err creating categories ', e)


workout_names = [
{'name': 'Air Squat', 'desc': 'Bodyweight squat with arms extended.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Assault Bike', 'desc': 'High‑intensity cardio on an air bike for lower‑body and upper‑body endurance.', 'primary_id': 28, 'secondary_id': 28},
{'name': 'Atlas Stone Lift', 'desc': 'Lifting a heavy atlas stone from ground to lap or platform.', 'primary_id': 33, 'secondary_id': 33},
{'name': 'Back Extension', 'desc': 'Lower back strengthening exercise with hands behind the head or across the chest.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Back Take From Turtle Drill', 'desc': 'Drill transitioning from turtle to back control position.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Bar Hang', 'desc': 'Hanging from a bar with arms fully extended to improve grip strength and shoulder mobility.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Bar Muscle Up', 'desc': 'A gymnastics move where an athlete pulls their entire body over a bar and then back down.', 'primary_id': 30, 'secondary_id': 30},
{'name': 'Battle Ropes Slams', 'desc': 'Powerful overhead slams with battle ropes to build full‑body explosiveness.', 'primary_id': 33, 'secondary_id': 33},
{'name': 'Battle Ropes Waves', 'desc': 'Alternating or double‑arm waves with battle ropes for conditioning and upper‑body endurance.', 'primary_id': 33, 'secondary_id': 33},
{'name': 'BB Curl', 'desc': 'Weightlifting exercise targeting the biceps, using a barbell and an underhand grip.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'BB Lunge', 'desc': 'Lunge exercise that utilizes a barbell on the back of the shoulders.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'BB Row', 'desc': 'Weightlifting exercise where a barbell is pulled towards the chest while maintaining a flat back.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Bear Complex', 'desc': 'Barbell complex of clean + front squat + push press + back squat + push press for full‑body work.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Bear Crawl', 'desc': 'Quadruped movement drill that targets total body coordination, strength, and endurance.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Behind the Neck Press', 'desc': 'Should press starting from behind the neck.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Bench Press', 'desc': 'Weightlifting exercise performed lying down, targeting the chest, shoulders, and triceps.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Block Snatch', 'desc': 'Olympic weightlifting movement that involves pulling a barbell from the ground to overhead in one motion, with a pause just above the knees.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Box Jump Over', 'desc': 'Jump laterally or forwards over a box to build power and agility.', 'primary_id': 31, 'secondary_id': 31},
{'name': 'Box Jumps', 'desc': 'Plyometric exercise that involves jumping onto a box.', 'primary_id': 31, 'secondary_id': 31},
{'name': 'Box Squat', 'desc': 'Squat variation that involves sitting back onto a box, then standing up again.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Broad Jump', 'desc': 'Maximal horizontal jump to develop explosive lower‑body power.', 'primary_id': 31, 'secondary_id': 31},
{'name': 'Bulgarian Split Squat', 'desc': 'Lunge variation that involves placing the rear foot on a bench or elevated surface.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Bulgarian Split Squat', 'desc': 'Split squat variation with rear foot elevated on a bench, targeting quadriceps and glutes.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Burpee Box Jump Over', 'desc': 'Combination of burpee and box jump‑over for conditioning and plyometric power.', 'primary_id': 31, 'secondary_id': 31},
{'name': 'Burpees', 'desc': 'Full-body exercise that involves squatting, kicking the feet back into a plank, performing a push-up, then returning to a squat and jumping.', 'primary_id': 31, 'secondary_id': 31},
{'name': 'Butterfly Guard Drill', 'desc': 'Foot‑hook guard drill working sweeps and elevation from butterfly guard.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Butterfly Pull‑Up', 'desc': 'Continuous pull‑up movement using a full kip and circular motion for speed and volume.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Cable Crunch', 'desc': 'Abdominal crunch variation using a rope attachment on a cable stack.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Cable Face Pull', 'desc': 'Cable exercise pulling rope towards face to hit rear delts and upper back.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Cable Front Raise', 'desc': 'Shoulder exercise lifting a cable handle in front of you, targeting anterior deltoids.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Cable Lateral Raise', 'desc': 'Deltoid isolation exercise using a cable machine.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Cable Overhead Tricep Extension', 'desc': 'Tricep isolation using a high pulley and rope attachment, extending arms overhead.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Cable Pull-Through', 'desc': 'Hip‑hinge cable exercise pulling the handle through your legs to target glutes and hamstrings.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Cable SkiErg', 'desc': 'Simulated skiing motion on SkiErg machine to hit back, shoulders, and cardio systems.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Cable Upright Row', 'desc': 'Cable variation of upright row, lifting the handle to chin level to hit traps and delts.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Calf Raises', 'desc': 'Exercise targeting the soleus portion of the calf.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Chain Wrestling Drill', 'desc': 'Linking multiple takedowns and counters in a continuous flow.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Chest Supported Rows', 'desc': 'Row variation whie lying on a bench, targeting the back muscles.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Chest‑to‑Bar Pull‑Up', 'desc': 'Gymnastic pull‑up where chest touches the bar, targeting lats and mid‑back.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Chin-Up', 'desc': 'Pull-up variation with an underhand grip, targeting the biceps and back muscles.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Clean', 'desc': 'Olympic weightlifting movement that involves pulling a barbell from the ground to the shoulders.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Clean and Jerk', 'desc': 'Olympic weightlifting movement that involves pulling a barbell from the ground to the shoulders, then pushing it overhead.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Close-Grip Bench Press', 'desc': 'Bench Press variation with a narrower grip, targeting the triceps.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Collar Tie Drill', 'desc': 'Drill for controlling opponent’s head/neck grip to set up takedowns.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Collateral Tie Drill', 'desc': 'Drill establishing and controlling collar tie for stance and entries.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Crab Walk', 'desc': 'Bodyweight movement performed in a reverse bridge position, targeting shoulders, triceps, and glutes.', 'primary_id': 28, 'secondary_id': 28},
{'name': 'Crossface Drill', 'desc': 'Shoulder pressure drill to break posture and set up front headlock.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Crunch', 'desc': 'Abdominal exercise that involves curling the upper body towards the knees.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Cuban Press', 'desc': 'Rotational shoulder press that transitions from lateral raise to overhead press.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Cycling', 'desc': 'Cycling.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'DB Bench Press', 'desc': 'Bench press exercise performed with dumbbells instead of a barbell.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'DB Bent Over Row', 'desc': 'Self supported, bent forward dumbbell rows.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'DB Bent Over Row', 'desc': 'Self‑supported bent‑over dumbbell rows targeting the back muscles, particularly the lats.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'DB Chest Fly', 'desc': 'An exercise performed lying down on the back spreading the arms to the side with dumbells.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'DB Chest Press', 'desc': 'Chest Press exercise performed with dumbbells instead of a barbell.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'DB Curl', 'desc': 'Bicep curl exercise performed with dumbbells instead of a barbell.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'DB Decline Chest Press', 'desc': 'Bench Press performed on a decline bench with dumbbells instead of a barbell.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'DB Front Raise', 'desc': 'Shoulder exercise that involves lifting dumbbells in front of the body.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'DB Lateral Raise', 'desc': 'Side dumbbell raise to isolate the medial deltoids.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'DB Lunge', 'desc': 'Lunge exercise performed with dumbbells.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'DB Pullover', 'desc': 'Back exercise that involves lying on a bench and lowering a dumbbell behind the head.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'DB Rear Delt Row', 'desc': 'Shoulder exercise that involves lifting dumbbells to the sides of the body.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'DB Reverse Fly', 'desc': 'Bent‑over dumbbell fly to target rear delts and upper back.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'DB Romanian Deadlift', 'desc': 'Romanian deadlift with dumbbells, targeting the posterior chain muscles of the legs and glutes', 'primary_id': 24, 'secondary_id': 24},
{'name': 'DB Row', 'desc': 'Bent-over row with dumbbells, targeting the back muscles, particularly the lats', 'primary_id': 24, 'secondary_id': 24},
{'name': 'DB Shoulder Press', 'desc': 'Shoulder press or overhead press with dumbbells, targeting the shoulder muscles', 'primary_id': 26, 'secondary_id': 26},
{'name': 'DB Shrug', 'desc': 'Shrug movement with dumbbells, targeting the trapezius muscles of the upper back', 'primary_id': 24, 'secondary_id': 24},
{'name': 'DB Upright Row', 'desc': 'Dumbbell variation of upright row to work traps and shoulders.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'DB Zottman Curl', 'desc': 'Curl up with palms‑up, rotate at top, lower with palms‑down, targeting biceps and forearms.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Deadbugs', 'desc': 'Abdominal exercise that involves lying on the back and extending opposite arms and legs.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Deadlift', 'desc': 'Weightlifting exercise that targets the lower body and back muscles.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Decline Bench Press', 'desc': 'Bench Press performed on a decline bench, targeting the lower portion of the chest.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Decline Push-Up', 'desc': 'Push-up with feet elevated, targeting upper chest and shoulders more aggressively.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Deficit Deadlift', 'desc': 'Deadlift variation with the feet standing on a platform or weight plate to increase range of motion.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Devil Press', 'desc': 'Burpee into dumbbell snatch + overhead press, combining cardio and full‑body strength.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Dips', 'desc': 'Dips performed with the body leaning slightly forward to target the triceps and chest.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Double Unders', 'desc': 'Jump rope exercise that involves passing the rope twice under the feet during each jump.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Double‑Leg Takedown', 'desc': 'Classic wrestling takedown shooting in on both legs for a finish.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Double‑Under', 'desc': 'Jump rope exercise where rope passes twice under feet per jump, for coordination and cardio.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Duck Under Drill', 'desc': 'Wrestling drill used to train level changes and entries under the opponent’s arms.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Elliptical', 'desc': 'Carido machine.', 'primary_id': 28, 'secondary_id': 28},
{'name': 'Farmers Walk', 'desc': 'Walking while holding weights in each hand, targeting the grip and overall strength and endurance of the upper body and core', 'primary_id': 28, 'secondary_id': 28},
{'name': 'Fireman’s Carry', 'desc': 'Takedown lift over the shoulder, finishing in dominant control position.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Front Squat', 'desc': 'Squatting with the barbell resting on the front of the shoulders, targeting the quadriceps, hamstrings, and glutes', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Glute Bridge', 'desc': 'Hip‑thrust from ground position to isolate glutes and hamstrings.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Glute-Ham Raise', 'desc': 'Bodyweight machine exercise to strengthen hamstrings and glutes by curling torso up.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Goblet Squat', 'desc': 'Squatting with a kettlebell or dumbbell held at chest level, targeting the same muscles as the front squat', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Good Morning', 'desc': 'Hinging at the hips while holding a barbell, targeting the posterior chain muscles of the legs and glutes', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Granby Roll', 'desc': 'Grappling escape move rolling over the shoulder to escape bottom positions.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Guard Retention Drill', 'desc': 'Drill maintaining your guard against pass attempts using frames and hip escape.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Hack Squat', 'desc': 'Machine or bar‑behind‑legs squat variation isolating quads and glutes.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Hammer Curl', 'desc': 'Curling dumbbells with a neutral grip, targeting the biceps', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Hamstring Curl', 'desc': 'Machine, targeting the hamstrings', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Hand Release Push‑Up', 'desc': 'Push‑up variation where hands lift off the ground at the bottom to ensure full range and reset.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Handstand Push Up', 'desc': 'Pushing the body up while in a handstand position, targeting the shoulder muscles', 'primary_id': 30, 'secondary_id': 30},
{'name': 'Handstand Walk', 'desc': 'Walking on the hands while maintaining a handstand position, targeting the core and upper body strength and stability', 'primary_id': 28, 'secondary_id': 28},
{'name': 'Hang Clean', 'desc': 'Olympic weightlifting movement involving lifting the barbell from a hanging position, targeting the explosive power and strength of the legs and back', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Hang Power Clean', 'desc': 'Similar to the hang clean, but the movement ends with the barbell at shoulder height instead of the front rack position', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Hang Power Snatch', 'desc': 'Olympic weightlifting movement involving lifting the barbell from a hanging position overhead in one fluid motion, targeting the same muscles as the hang clean', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Hang Snatch', 'desc': 'A variation of the snatch starting off the floor.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Hanging Leg Raises', 'desc': 'Hanging from a bar and raising the legs up to the chest or higher, targeting the core muscles', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Heel Touch', 'desc': 'Lying on the back and touching the heels with the fingertips, targeting the abdominal muscles', 'primary_id': 25, 'secondary_id': 25},
{'name': 'High‑Crotch Takedown', 'desc': 'Takedown variant targeting one leg with a deep underhook for lift.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Hill Sprints', 'desc': 'Up hill sprints.', 'primary_id': 29, 'secondary_id': 29},
{'name': 'Hip Abduction', 'desc': 'Moving the legs away from the midline of the body while lying on the side, targeting the hip abductor muscles', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Hip Adduction', 'desc': 'Moving the legs toward the midline of the body while lying on the side, targeting the hip adductor muscles', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Hip Escape', 'desc': 'Core grappling movement to create space between you and your opponent.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Hip Thrust', 'desc': 'Hinging at the hips while the shoulders are elevated on a bench, targeting the glute muscles', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Incline Bench Press', 'desc': 'Bench press performed on an inclined bench, targeting the upper portion of the chest muscles', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Incline Dumbbell Press', 'desc': 'Dumbbell press performed on an inclined bench, targeting the same muscles as the incline bench press', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Incline Push-Up', 'desc': 'Push-up performed with hands elevated on a surface, easier variation for beginners or high-rep sets.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Jefferson Deadlift', 'desc': 'Stance‑straddling deadlift variation with asymmetric grip, targeting posterior chain.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Jogging', 'desc': 'Jogging', 'primary_id': 28, 'secondary_id': 28},
{'name': 'JuiJitsu', 'desc': 'Martial art involving grappling and submission holds, targeting overall strength, endurance, and flexibility', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Kettlebell Clean and Press', 'desc': 'Single‑arm clean into overhead press with kettlebell, for total‑body power.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Kettlebell Front Squat', 'desc': 'Front squat with two kettlebells.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Kettlebell Overhead Press', 'desc': 'Overhead press with two kettlebell.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Kettlebell Overhead Squat', 'desc': 'Overhead squat with two kettlebells.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Kettlebell Swing', 'desc': 'Swinging a kettlebell between the legs and up to shoulder height, targeting the posterior chain muscles of the legs and glutes', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Kipping Pull‑Up', 'desc': 'Pull‑up using hip‑drive kip to generate momentum and increase reps.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Knee Slice Pass Drill', 'desc': 'Guard pass drill slicing knee through opponent’s guard to establish side control.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Landmine', 'desc': 'Exercise involving a barbell anchored at one end and held at the other, targeting various muscle groups depending on the movement', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Landmine Press', 'desc': 'Single‑arm press with barbell anchored in landmine attachment, for shoulder stability.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Landmine Row', 'desc': 'Row variation using landmine barbell pivot, targeting lats and traps.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Landmine Squat', 'desc': 'Goblet‑style squat holding end of landmine barbell at chest level.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Leg Curl', 'desc': 'Curling the legs toward the buttocks while lying on the stomach, targeting the hamstrings muscles', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Leg Extension', 'desc': 'Extension movement of the legs while seated, targeting the quadriceps muscles', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Leg Press', 'desc': 'Pressing weight away with the legs while seated, targeting the same muscles as the squat', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Leg Raise', 'desc': 'Lying on the back and raising the legs up to the chest or higher, targeting the abdominal muscles', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Low Single‑Leg Takedown', 'desc': 'Underhook single‑leg entry aiming to lift and sweep the opponent’s leg.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Lunge', 'desc': 'Forward lunge stepping one leg forward and lowering hips until both knees are at 90°, targeting quads, hamstrings, and glutes.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Machine Shoulder Press', 'desc': 'Overhead pressing using a seated shoulder machine for stability.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Man Maker', 'desc': 'Renegade row + push‑up + squat + press in one dumbbell complex for total‑body conditioning.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Med Ball Side Toss', 'desc': 'Throw a medicine ball from the hip, across your body.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Med Ball Slam', 'desc': 'Slam mediine ball from overhead to the ground.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Mountain Climbers', 'desc': 'Alternating leg movement resembling climbing, targeting the core and cardiovascular endurance', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Neck Harness Extension', 'desc': 'Neck strengthening using a harness with weight, common in wrestling and MMA.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Overhead Squat', 'desc': 'Squatting with the barbell held overhead, targeting the same muscles as the front squat and shoulder muscles', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Overhead Walking Lunge', 'desc': 'Lunge while holding barbell or dumbbell overhead, challenging stability and core.', 'primary_id': 28, 'secondary_id': 28},
{'name': 'Overhook Pummel Drill', 'desc': 'Drill locking and pummeling for overhook control in clinch scenarios.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Paused Deadlift', 'desc': 'Deadlift movement with a pause at the mid-shin level', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Paused Squat', 'desc': 'A squat variation where the lifter pauses at the bottom of the squat for a predetermined amount of time before standing back up.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Pendlay Row', 'desc': 'A type of rowing exercise where the barbell is lifted off the ground for each repetition and then lowered back down in a controlled manner.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Penetration Step Drill', 'desc': 'Fundamental drill practicing deep level change and step to set up shots.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Pistol Squat', 'desc': 'Single-leg squat requiring balance and leg strength, commonly done in calisthenics.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Plank', 'desc': 'An isometric exercise where the body is held in a straight line from head to heels in a push-up position, with the elbows or hands on the ground.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Power Clean', 'desc': 'A weightlifting exercise where the barbell is explosively lifted from the ground to the shoulders in one motion.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Power Jerk', 'desc': 'A weightlifting exercise where the barbell is explosively lifted from the shoulders to overhead, with a slight dip of the legs before driving the barbell up with the arms and legs.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Power Snatch', 'desc': 'A weightlifting exercise where the barbell is explosively lifted from the ground to overhead in one motion.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Preacher Curl', 'desc': 'Biceps curl performed seated at a preacher bench to isolate the muscle.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Pull Up', 'desc': 'An upper body exercise where the body is lifted up towards a bar with the arms until the chin is above the bar.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Push Press', 'desc': 'A weightlifting exercise where the barbell is lifted from the shoulders to overhead with the assistance of the legs.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Push-Up', 'desc': 'An exercise where the body is lowered towards the ground and then pushed back up using the arms and chest muscles.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Reverse Flyes', 'desc': 'An exercise where the arms are lifted away from the body in a reverse motion, targeting the muscles of the upper back and shoulders.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Reverse Grip Bench Press', 'desc': 'Bench press with underhand grip to emphasize upper chest and triceps.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Reverse Hyper Ext', 'desc': 'An exercise machine where the lower body is suspended in the air while the upper body is held in place, targeting the lower back and glutes.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Reverse Lunge', 'desc': 'Lunge variation stepping backward instead of forward, often easier on the knees.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Ring Handstand Push Up', 'desc': 'An exercise where the body is held in a handstand position using gymnastic rings for support.', 'primary_id': 30, 'secondary_id': 30},
{'name': 'Ring Muscle Up', 'desc': 'A gymnastic exercise where the body is lifted up and over the rings, targeting the muscles of the upper body.', 'primary_id': 30, 'secondary_id': 30},
{'name': 'Rolling Sesh', 'desc': 'Bump n tap.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Romanian Deadlift', 'desc': 'A deadlift variation where the barbell is lowered to the shins and then lifted back up, targeting the muscles of the lower back and hamstrings.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Rope Climbing', 'desc': 'An exercise where the body is pulled up a rope using the arms and upper body strength.', 'primary_id': 33, 'secondary_id': 33},
{'name': 'Rowing', 'desc': 'A cardiovascular exercise where the body is propelled forward on a machine using a rowing motion.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Running', 'desc': 'A cardiovascular exercise where the body runs or jogs on a treadmill or outside.', 'primary_id': 28, 'secondary_id': 28},
{'name': 'Russian Twist', 'desc': 'Seated core exercise involving rotating the torso side to side, targeting the obliques.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Sandbag Clean and Press', 'desc': 'Floor clean into overhead press using a heavy sandbag for functional strength.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Sandbag Shoulder to Overhead', 'desc': 'Clean and push or press sandbag from shoulder to overhead for functional strength.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Seated Calf Raise', 'desc': 'Machine-based exercise targeting the soleus portion of the calf.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Shadow Grappling', 'desc': 'Dynamic solo movement mimicking offensive and defensive grappling flows.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Shoulder Press', 'desc': 'Shoulder press or overhead press with a barbell, targeting the shoulder muscles', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Side Plank', 'desc': 'An isometric exercise where the body is held in a straight line from head to heels in a side position, with one elbow or hand on the ground.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Single-Arm Landmine Press', 'desc': 'Unilateral landmine press variation to work one shoulder at a time.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Single-Leg Glute Bridge', 'desc': 'Unilateral hip bridge lifting one leg to isolate each glute separately.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Single-Leg Romanian Deadlift', 'desc': 'Standing on one leg, hinge at hip with dumbbell to target hamstrings and balance.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Single‑Arm Dumbbell Snatch', 'desc': 'Powerful one‑arm dumbbell snatch from ground to overhead to build explosive strength.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Single‑Leg Takedown', 'desc': 'Traditional shoot to one leg, finishing with lift or sweep.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Sit-Up', 'desc': 'An exercise where the body is lifted from a lying down position to a seated position using the abdominal muscles.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Sit‑Out Drill', 'desc': 'Hip escape drill moving from turtle to wrestler’s base for escapes.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Sled Pull', 'desc': 'Dragging a sled towards you for lower‑body and grip conditioning.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Sled Push', 'desc': 'Pushing a weighted sled away from you to build leg drive and total‑body power.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Sledgehammer Slams', 'desc': 'Swinging a sledgehammer onto a tire to build rotational power and conditioning.', 'primary_id': 33, 'secondary_id': 33},
{'name': 'Smith Machine Bench Press', 'desc': 'Bench press variation using a Smith machine for guided bar path.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Smith Machine Calf Raise', 'desc': 'Calf isolation under Smith bar, toes‑up/downs for gastrocnemius and soleus.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Smith Machine Hack Squat', 'desc': 'Hack squat performed on a Smith machine for guided path and safety.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Smith Machine Row', 'desc': 'Guided barbell row on a Smith machine to target lats and mid‑back.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Smith Machine Shoulder Press', 'desc': 'Overhead press on Smith machine to work deltoids with added stability.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'Smith Machine Squat', 'desc': 'Back squat variation on Smith machine to guide bar path and safety.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Snap Down to Front Headlock', 'desc': 'Drill snapping opponent’s head down then locking front head position.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Snatch', 'desc': 'A weightlifting exercise where the barbell is lifted from the ground to overhead in one motion.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Snatch Grip Behind the Neck Press', 'desc': 'A variation of the snatch exercise where the lifter uses a wider grip on the barbell.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Snatch Grip Deadlift', 'desc': 'A deadlift performed with a snatch grip.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Spinning Single‑Leg Takedown', 'desc': 'Advanced single‑leg variation spinning into opponent’s body for takedown.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Split Jerk', 'desc': 'A weightlifting exercise where the barbell is lifted from the shoulders to overhead with a split stance of the legs.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Sprawl and Brawl', 'desc': 'Drill sprawl defense on shots, then counter‑attack with takedown setups.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Sprawls', 'desc': 'Defensive wrestling move to counter takedowns by kicking the legs back and hips down.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Sprint', 'desc': 'A high intensity cardiovascular exercise where the body runs or sprints at a fast pace.', 'primary_id': 29, 'secondary_id': 29},
{'name': 'Squat', 'desc': 'An exercise where the body is lowered down into a sitting position and then lifted back up, targeting the muscles of the legs and glutes.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Squat Jerk', 'desc': 'A weightlifting exercise where the barbell is lifted from the shoulders to overhead with a squat stance of the legs.', 'primary_id': 23, 'secondary_id': 23},
{'name': 'Stairs', 'desc': 'Stairs/ stairmaster/ stairclimber.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Standing Calf Raise', 'desc': 'Calf isolation exercise using bodyweight or machines.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Step Up', 'desc': 'An exercise where the body steps up onto a platform or bench using the leg muscles.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Suitcase Carry', 'desc': 'One‑arm farmers‑walk holding a dumbbell at your side, bracing core and grip.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Suitcase Deadlift', 'desc': 'Deadlift from a single side load to challenge core anti‑lateral flexion.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Sumo Deadlift', 'desc': 'A deadlift variation where the feet are placed in a wider stance and the grip is between the legs, targeting the muscles of the inner thighs and lower back.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'T-Bar Row', 'desc': 'Back exercise using a barbell in a landmine-style base.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Technical Stand-Up', 'desc': 'Fundamental Jiu Jitsu movement to return to standing safely and in base.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Thruster', 'desc': 'A weightlifting exercise where the barbell is lifted from the shoulders to overhead with', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Toes-to-Bar', 'desc': 'Hanging leg raise variation bringing toes to bar to hit core and hip flexors.', 'primary_id': 30, 'secondary_id': 30},
{'name': 'Trap Bar Deadlift', 'desc': 'Deadlift variation using a hex bar for better biomechanics.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Tricep Extension', 'desc': 'Tricep extension is an isolation exercise that targets the triceps muscles. It is typically performed with a cable machine or dumbbell, and involves extending the arm at the elbow joint to activate the triceps.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'TRX Chest Press', 'desc': 'Suspension‑strap chest press to build pressing strength and core stability.', 'primary_id': 26, 'secondary_id': 26},
{'name': 'TRX Row', 'desc': 'Body‑weight inverted row on suspension straps to target mid‑back and biceps.', 'primary_id': 24, 'secondary_id': 24},
{'name': 'Turkish Get‑Up', 'desc': 'Complex full‑body movement transitioning from ground to standing while holding weight overhead.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Underhook Pummel Drill', 'desc': 'Hand‑fighting drill securing and switching underhooks against an opponent.', 'primary_id': 32, 'secondary_id': 32},
{'name': 'Walking', 'desc': 'Walking.', 'primary_id': 28, 'secondary_id': 28},
{'name': 'Wall Balls', 'desc': 'Wall balls are a functional fitness exercise that involves throwing a weighted ball against a wall and catching it as it comes back down. This exercise targets several muscle groups including the legs, hips, core, shoulders, and arms. It is often used in CrossFit and other high-intensity training programs.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Wall Handstand', 'desc': 'Holding a handstand position using a wall for support, developing shoulder and core strength.', 'primary_id': 30, 'secondary_id': 30},
{'name': 'Wall Sit', 'desc': 'Isometric lower body hold against a wall, targeting the quads.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Wall Walk', 'desc': 'Start in plank, walk feet up wall and hands closer to wall, then reverse to develop shoulder strength.', 'primary_id': 28, 'secondary_id': 28},
{'name': 'Windshield Wiper', 'desc': 'The windshield wiper exercise is a core strengthening exercise that targets the obliques and lower abs. It involves lying on the back with the legs raised and extended, and then moving the legs from side to side in a windshield wiper motion. This exercise is typically performed on a mat or bench, and can be modified to increase or decrease the difficulty level.', 'primary_id': 27, 'secondary_id': 27},
{'name': 'Wrestler’s Bridge', 'desc': 'Neck and back strength drill bridging from the top of the head.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Yoke Carry', 'desc': 'Carrying a loaded yoke across the shoulders for core stability and leg endurance.', 'primary_id': 25, 'secondary_id': 25},
{'name': 'Zercher Squat', 'desc': 'Squat variation holding the bar in the crooks of the elbows.', 'primary_id': 23, 'secondary_id': 23},
]




def classify_primary_id(name: str) -> int:
    """Return the category ID directly based on exercise name keywords."""
    lname = name.lower()
    # Squat movements
    if 'squat' in lname and 'overhead' not in lname:
        return new_categories['Squat']
    # Deadlift and pulling movements
    if any(k in lname for k in ('deadlift', 'row', 'pull', 'curl', 'shrug')):
        return new_categories['Deadlift']
    # Dynamic pulls
    if any(k in lname for k in ('clean', 'snatch', 'swing')):
        return new_categories['Power Clean']
    # Presses
    if any(k in lname for k in ('press', 'push-up', 'dip')):
        return new_categories['Press']
    # Core exercises
    if any(k in lname for k in ('plank', 'crunch', 'sit-up', 'raise', 'hanging', 'windshield', 'deadbug')):
        return new_categories['Core']
    # Slow cardio
    if any(k in lname for k in ('bike', 'run', 'elliptical', 'jog', 'walk', 'cardio')):
        return new_categories['Cardio']
    # Sprints
    if 'sprint' in lname:
        return new_categories['Sprinting']
    # Gymnastics skills
    if any(k in lname for k in ('muscle up', 'handstand', 'toes-to-bar', 'kipping', 'ring')):
        return new_categories['Gymnastics']
    # Plyometrics
    if any(k in lname for k in ('jump', 'burpee', 'hop', 'box')):
        return new_categories['Plyometric']
    # Grappling drills
    if any(k in lname for k in ('takedown', 'drill', 'sprawl', 'pummel', 'guard', 'clinch', 'escape')):
        return new_categories['Grappling']
    # Striking implements
    if any(k in lname for k in ('rope', 'battle', 'sledgehammer', 'atlas', 'assault')):
        return new_categories['Striking']
    # Fallback to total‑body power
    return new_categories['Power Clean']

updated = []
for w in workout_names:
    # print(w)
    primary_cat = classify_primary_id(w['name']) - 1
    w['primary_id'] = primary_cat
    w['categories'] = [ primary_cat ]
    # For simplicity set secondary same as primary
    w['secondary_id'] = primary_cat


    updated.append(w)



for wname in updated:
    cats = [cat + 1 + 22 for cat in wname['categories']]
    # cats = [cat for cat in wname['categories']]
    del wname['categories']
    wname['primary_id'] += 1 + 140
    wname['secondary_id'] += 1 + 140
    try:
        new_obj = WorkoutNames.objects.create(**wname)
        new_obj.categories.set(cats)
        new_obj.save
    except Exception as e:
        print('Error creating workout name', e)



for item in sorted(updated, key=lambda x: x['name'].lower()):
        print(item, end=",\n")

# for item in sorted(workout_names, key=lambda x: x['name'].lower()):
#         print(item['name'], end=",")