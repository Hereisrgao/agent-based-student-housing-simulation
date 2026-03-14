# -*- coding: utf-8 -*-
"""
Rule-based decision module

Provides:
- get_rule_based_scores(state) -> dict
- get_best_action_rule_based(state) -> str
- get_action_and_scores(state) -> (best_action, top3_dict, all_scores_sorted_dict)
"""

# ----------------- Rule-based scoring for each behavior -----------------

def rule_based_cook(hunger, kitchen):
    hunger = max(0, min(100, hunger))
    kitchen = max(0, min(3.0, kitchen))
    if hunger >= 80 and kitchen <= 1.0:
        return 10
    elif hunger >= 60 and kitchen <= 2.0:
        return 8
    elif hunger >= 40 and kitchen <= 2.5:
        return 5
    elif hunger >= 20 and kitchen <= 2.8:
        return 3
    else:
        return 1


def rule_based_shower(fatigue, time_hour, bathroom):
    fatigue = max(0, min(100, fatigue))
    time_hour = max(0, min(23, time_hour))
    bathroom = max(0, min(3.0, bathroom))
    if fatigue >= 70 and 20 <= time_hour <= 23 and bathroom <= 1.0:
        return 10
    elif fatigue >= 50 and 20 <= time_hour <= 23 and bathroom <= 2.0:
        return 7
    elif fatigue >= 30 and 15 <= time_hour <= 19 and bathroom <= 2.0:
        return 5
    elif 6 <= time_hour <= 11 and bathroom <= 1.5:
        return 4
    else:
        return 1


def rule_based_clean(room_dirty, energy, complaints):
    room_dirty = max(0, min(100, room_dirty))
    energy = max(0, min(100, energy))
    complaints = max(0, min(10, complaints))
    if room_dirty >= 80 and energy >= 60 and complaints >= 3:
        return 10
    elif room_dirty >= 60 and energy >= 40 and complaints >= 2:
        return 7
    elif room_dirty >= 40 and energy >= 30 and complaints >= 1:
        return 5
    elif room_dirty >= 20 and energy >= 20 and complaints >= 1:
        return 3
    else:
        return 1


def rule_based_study(energy, exam_urgency, time_available):
    energy = max(0, min(100, energy))
    exam_urgency = max(0, min(10, exam_urgency))
    time_available = max(0, min(10, time_available))
    if exam_urgency >= 8 and time_available >= 2 and energy >= 40:
        return 10
    elif exam_urgency >= 6 and time_available >= 1.5 and energy >= 30:
        return 7
    elif exam_urgency >= 4 and time_available >= 1:
        return 5
    elif exam_urgency >= 2:
        return 3
    else:
        return 1


def rule_based_play(stress, energy, task_done):
    stress = max(0, min(100, stress))
    energy = max(0, min(100, energy))
    task_done = max(0, min(10, task_done))
    if stress >= 70 and energy >= 50:
        return 9
    elif stress >= 50 and energy >= 40:
        return 7
    elif stress >= 30 and energy >= 30:
        return 5
    elif stress >= 20:
        return 3
    else:
        return 1


def rule_based_sleep(tiredness, time_hour, sleep_quality, exam_urgency):
    tiredness = max(0, min(100, tiredness))
    time_hour = max(0, min(23, time_hour))
    sleep_quality = max(0, min(10, sleep_quality))
    exam_urgency = max(0, min(10, exam_urgency))
    if tiredness >= 80:
        return 10
    elif tiredness >= 60 and (time_hour >= 22 or time_hour <= 6):
        return 8
    elif tiredness >= 50:
        return 6
    elif time_hour >= 23 or time_hour <= 5:
        return 5
    else:
        return 2


def rule_based_lounge(social_need, flatmates, time_hour):
    social_need = max(0, min(100, social_need))
    flatmates = max(0, min(5, flatmates))
    time_hour = max(0, min(23, time_hour))
    if social_need >= 70 and 1 <= flatmates <= 3 and 18 <= time_hour <= 22:
        return 10
    elif social_need >= 50 and 1 <= flatmates <= 4 and 17 <= time_hour <= 23:
        return 8
    elif social_need >= 40 and flatmates >= 1 and 13 <= time_hour <= 17:
        return 6
    elif social_need >= 30 and flatmates >= 1 and (9 <= time_hour <= 12 or 16 <= time_hour <= 18):
        return 4
    else:
        return 1


# ----------------- Aggregation interface -----------------

def get_rule_based_scores(state: dict) -> dict:
    """Return rule-based scores (0–10) for each behavior."""
    return {
        'cook':   rule_based_cook(state.get('hunger', 0), state.get('kitchen', 0.0)),
        'shower': rule_based_shower(state.get('fatigue', 0), state.get('time_hour', 0), state.get('bathroom', 0.0)),
        'clean':  rule_based_clean(state.get('room_dirty', 0), state.get('energy', 0), state.get('complaints', 0)),
        'study':  rule_based_study(state.get('energy', 0), state.get('exam_urgency', 0), state.get('time_available', 0)),
        'play':   rule_based_play(state.get('stress', 0), state.get('energy', 0), state.get('task_done', 0)),
        'sleep':  rule_based_sleep(state.get('tiredness', 0), state.get('time_hour', 0), state.get('sleep_quality', 0), state.get('exam_urgency', 0)),
        'lounge': rule_based_lounge(state.get('social_need', 0), state.get('flatmates', 0), state.get('time_hour', 0)),
    }


def get_best_action_rule_based(state: dict) -> str:
    scores = get_rule_based_scores(state)
    return max(scores, key=scores.get)


def get_action_and_scores(state: dict):
    """Return (best_action, top3_dict, all_scores_sorted_dict)."""
    scores = get_rule_based_scores(state)
    sorted_items = sorted(scores.items(), key=lambda kv: -kv[1])
    best = sorted_items[0][0]
    top3 = dict(sorted_items[:3])
    all_sorted = dict(sorted_items)
    return best, top3, all_sorted


# ========= Unified interface for Rule-based =========
def rule_decision(state: dict, debug: bool = False):
    """
    Unified interface for rule-based model:
    - Returns best action string (same style as utility_decision)
    - If debug=True, writes scores into state['__rule_scores']
    """
    scores = get_rule_based_scores(state)
    best_action = max(scores, key=scores.get) if scores else "lounge"
    if debug:
        state["__rule_scores"] = dict(scores)
    return best_action
