# Baseline Ideal Day Template & Life Preferences
USER_LIFE_PROFILE = {
    "name": "Ujwal",
    "ideal_wake_time": "07:30",
    "target_sleep_time": "23:30",
    "minimum_lunch_duration_mins": 30,
    "minimum_workout_duration_mins": 35,
    "max_continuous_deep_work_mins": 90,
    
    # Priority hierarchy when time gets squeezed
    "priority_order": [
        "fixed_commitments",  # Classes, client meetings, exams
        "high_stakes_deadlines",  # Proposals due within 24h
        "physical_health",    # Food, minimum workout
        "deep_coding_study",  # Project progression
        "admin_and_chores"    # Inbox, cleaning, desk organizing
    ],
    
    # Default ideal routine blocks
    "baseline_routine": [
        {"time": "07:30-08:15", "title": "Morning Routine & Breakfast", "type": "routine"},
        {"time": "08:15-09:30", "title": "Gym / Workout", "type": "routine"},
        {"time": "10:00-13:00", "title": "Deep Focus Work", "type": "deep_work"},
        {"time": "13:00-14:00", "title": "Lunch & Rest", "type": "recharge"},
        {"time": "14:00-17:00", "title": "Collab / Classes / Tasks", "type": "quick_task"},
        {"time": "17:00-18:00", "title": "Buffer & Unwind", "type": "buffer"},
        {"time": "18:00-20:30", "title": "Evening Project Sprint", "type": "deep_work"},
        {"time": "20:30-21:30", "title": "Dinner", "type": "recharge"},
        {"time": "21:30-23:00", "title": "Review & Free Time", "type": "buffer"},
        {"time": "23:30", "title": "Sleep", "type": "recharge"}
    ]
}