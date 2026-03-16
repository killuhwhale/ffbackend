🏗️ Project Overview
This project is a comprehensive fitness and gym management platform. It serves both individual users tracking their personal fitness journeys and gym owners/coaches managing classes and member programming.
Core Domains:
Gym Management: Gyms, Classes, Coaches, and Members.
Workout Programming: A deeply nested hierarchy consisting of Workout Groups $\rightarrow$ Workouts $\rightarrow$ Workout Items / Dual Items.
User Tracking: Completed workouts, body measurements, user 1RM (one-rep max) tracking, and history.
AI Coach: An LLM-powered workout generator that utilizes user maxes, past workouts, and goals to build custom JSON-structured workout plans.
🧱 Architecture
Backend: Python / Django / Django REST Framework (DRF).
Frontend: React Native / TypeScript (Mobile App).
Database: PostgreSQL (with TrigramSimilarity for search).
Storage: AWS S3 (Custom s3Client for media).
⚙️ Backend Guidelines (Django / DRF)1. Architectural Patterns
ViewSets: We heavily utilize DRF ModelViewSets and ViewSets. Custom actions are denoted using the @action decorator.
Custom Mixins/Decorators: Be aware of legacy constraints, such as DestroyWithPayloadMixin (React Native requires payloads on deletion) and custom overrides (e.g., blocking default DRF routes to enforce bulk creation).
Transactions: Use @transaction.atomic for complex deletions or bulk creations (e.g., delete_user_data, duplicate workout groups) to prevent orphaned data.
2. Permission & Access Control
Permissions are highly granular and role-based. Always apply the correct custom permission class rather than generic DRF permissions.
GymPermission / GymClassPermission: Restricted to Gym Owners.
CoachPermission / MemberPermission: Allows actions by Owners or assigned Coaches.
WorkoutPermission / WorkoutGroupsPermission: Users can manage their own workouts; Owners/Coaches can manage class workouts.
SelfActionPermission: For user-specific actions (e.g., updating 1RMs, liking workouts).
3. The Workout Hierarchy (CRITICAL)
When creating or modifying workout logic, strictly adhere to this hierarchy:
WorkoutGroups: The top-level container (can be assigned to a user or a class). Can act as a "Template."
Workouts: The individual workout session within a group. Contains a scheme_type.
WorkoutItems / WorkoutDualItems: The specific movements. If scheme_type <= 2, use WorkoutItems. Otherwise, use WorkoutDualItems.
Completed Equivalents: When a user finishes a workout, the data is duplicated into CompletedWorkoutGroups, CompletedWorkouts, and CompletedWorkoutItems to freeze the state.
4. AI & LLM Integrations
The AIViewSet handles dynamic workout generation.
We support fallback/routing between OpenAI, Anthropic (Claude), and Google Gemini.
Tool Calling: The LLMs are strictly instructed to output structured JSON matching our create_workout_schema.json. Never instruct the AI to return raw text for these endpoints.
Token Quotas: Monitored via the TokenQuota model. Always check remaining tokens before hitting external APIs.
5. Media Handling
All media (Gym logos, Workout videos/images) is handled via s3_client.upload() and s3_client.remove().
Media paths follow strict bucket key structures: [file_kind]/[parent_id]/[file_name].Django Project - BackEnd for Mobile App that allows users to create and track their workouts.



isntafit - Core Django app 
Gyms - dajngo app: Handles creating Gyms and everythign related 
users - django app: Handles users

Runs in docker. 
