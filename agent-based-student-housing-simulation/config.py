# Initial state values for each student (0~1 scale)
student_states = {
    "Bruce": {
        "hunger": 0.5,
        "fatigue": 0.4,
        "stress": 0.5,
        "exam_urgency": 0.6,
        "sleep_quality": 0.5,
        "room_dirty": 0.3,
        "social_need": 0.2,
        "task_done": 0.4,
    },
    "Clark": {
        "hunger": 0.6,
        "fatigue": 0.3,
        "stress": 0.3,
        "exam_urgency": 0.4,
        "sleep_quality": 0.7,
        "room_dirty": 0.5,
        "social_need": 0.7,
        "task_done": 0.3,
    },
    "Diana": {
        "hunger": 0.4,
        "fatigue": 0.5,
        "stress": 0.6,
        "exam_urgency": 0.7,
        "sleep_quality": 0.4,
        "room_dirty": 0.4,
        "social_need": 0.5,
        "task_done": 0.4,
    },
    "Barry": {
        "hunger": 0.7,
        "fatigue": 0.3,
        "stress": 0.4,
        "exam_urgency": 0.5,
        "sleep_quality": 0.6,
        "room_dirty": 0.6,
        "social_need": 0.8,
        "task_done": 0.2,
    },
    "Lex": {
        "hunger": 0.5,
        "fatigue": 0.3,
        "stress": 0.4,
        "exam_urgency": 0.6,
        "sleep_quality": 0.5,
        "room_dirty": 0.5,
        "social_need": 0.3,
        "task_done": 0.5,
    },
}

# Individual preferences for each student (wake/sleep hours, cleanliness tolerance, etc.)
student_preferences = {
    "Bruce": {
        "wake_up_hour": 10,
        "sleep_hour": 2,
        "cleanliness_tolerance": 0.2,
        "cooking_enjoyment": 0.6,
        "social_sensitivity": 0.3
    },
    "Clark": {
        "wake_up_hour": 7,
        "sleep_hour": 23,
        "cleanliness_tolerance": 0.5,
        "cooking_enjoyment": 0.9,
        "social_sensitivity": 0.6
    },
    "Diana": {
        "wake_up_hour": 8,
        "sleep_hour": 0,
        "cleanliness_tolerance": 0.4,
        "cooking_enjoyment": 0.5,
        "social_sensitivity": 0.5
    },
    "Barry": {
        "wake_up_hour": 9,
        "sleep_hour": 1,
        "cleanliness_tolerance": 0.3,
        "cooking_enjoyment": 0.4,
        "social_sensitivity": 0.8
    },
    "Lex": {
        "wake_up_hour": 8,
        "sleep_hour": 23,
        "cleanliness_tolerance": 0.7,
        "cooking_enjoyment": 0.3,
        "social_sensitivity": 0.2
    },
}

# Model assignment for different experiment setups (fuzzy-only, utility-only, hybrid)
experiment_settings = {
    "fuzzy_only": {
        "Bruce": "fuzzy",
        "Clark": "fuzzy",
        "Diana": "fuzzy",
        "Barry": "fuzzy",
        "Lex": "fuzzy"
    },
    "utility_only": {
        "Bruce": "utility",
        "Clark": "utility",
        "Diana": "utility",
        "Barry": "utility",
        "Lex": "utility"
    },
    "hybrid": {
        "Bruce": "fuzzy",
        "Clark": "fuzzy",
        "Diana": "utility",
        "Barry": "utility",
        "Lex": "other"  # rule-based agent
    }
}
