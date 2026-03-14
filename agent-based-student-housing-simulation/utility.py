# -*- coding: utf-8 -*-
import math
import random

ACTIONS = ["sleep", "study", "cook", "shower", "clean", "lounge", "play"]

PARAMS = {
    "stickiness_bonus": 0.06,     # bonus for repeating same behavior
    "epsilon": 0.15,              # ε-greedy exploration probability
    "softmax_temp": 0.22,         # softmax temperature (lower = greedier)
    "cooldown_penalty_scale": 0.18,
    "crowd_penalty_per_extra": 0.08,
    "kitchen_capacity": 2,
    "bathroom_capacity": 1,
    "kitchen_avail_threshold": 0.6,
    "bathroom_avail_threshold": 0.8,
    "weights": {
        "sleep":  {"sleep_pressure": 0.38, "fatigue": 0.20, "low_sleep_q": 0.18, "stress": 0.08, "circadian": 0.08},
        "study":  {"exam_urgency": 0.30, "undone": 0.22, "energy": 0.15, "low_hunger": 0.06, "moderate_stress": 0.05},
        "cook":   {"hunger": 0.95, "time_ok": 0.22, "energy": 0.10},
        "shower": {"stress": 0.75, "low_sleep_q": 0.35, "fatigue": 0.18},
        "clean":  {"room_dirty": 0.60, "complaints": 0.25, "energy": 0.10},
        "lounge": {"social_need": 0.60, "evening": 0.24, "flatmates": 0.24, "stress": 0.10},
        "play":   {"high_stress": 0.50, "energy": 0.22, "time_ok": 0.18},
    },
    "base_floor": -0.20,
}

SCALE_MAP_DEFAULT = {
    "hunger":        1.0,
    "fatigue":       1.0,
    "energy":        1.0,
    "stress":        1.0,
    "room_dirty":    100.0,
    "social_need":   100.0,
    "exam_urgency":  10.0,
    "sleep_quality": 10.0,
    "time_available":10.0,
    "complaints":    10.0,
    "task_done":     10.0,
    "flatmates":     3.5,
}
PARAMS.setdefault("scales", {})
for k, v in SCALE_MAP_DEFAULT.items():
    PARAMS["scales"].setdefault(k, v)

def _to_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)

def _clip01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def _normalize_state_for_utility(state: dict) -> dict:
    """Normalize whitelisted keys to 0–1; keep others unchanged."""
    ns = dict(state)
    scales = PARAMS.get("scales", {})
    for key, denom in scales.items():
        if key in state:
            val = _to_float(state.get(key, 0.0))
            if denom and denom != 1.0:
                ns[key] = _clip01(val / float(denom))
            else:
                ns[key] = _clip01(val)
    return ns

def _get(state, key, default=0.0):
    """Safe getter: returns float if possible."""
    v = state.get(key, default)
    if isinstance(v, str):
        try:
            return float(v)
        except:
            return default
    return v if v is not None else default

def _sigmoid(x): return 1 / (1 + math.exp(-x))
def _evening_bonus(hour): return 1.0 if 18 <= hour <= 22 else 0.0

def _softmax_sample(scores, temp, rng):
    if temp <= 1e-6:
        return max(scores.items(), key=lambda kv: kv[1])[0]
    mx = max(scores.values()) if scores else 0.0
    exps = {a: math.exp((s - mx) / temp) for a, s in scores.items()}
    Z = sum(exps.values())
    if Z <= 0:
        return max(scores.items(), key=lambda kv: kv[1])[0]
    r = rng.random()
    acc = 0.0
    for a, e in exps.items():
        acc += e / Z
        if r <= acc:
            return a
    return max(scores.items(), key=lambda kv: kv[1])[0]

# ---------- Behavior scorers ----------
def score_sleep(st, w):
    sp = _clip01(_get(st, "sleep_pressure", 0.5))
    fatigue = _clip01(_get(st, "fatigue", 0.5))
    low_sq = _clip01(1.0 - _get(st, "sleep_quality", 0.5))
    stress = _clip01(_get(st, "stress", 0.3))
    C = _get(st, "circadian", 0.0)
    score = (
        w["sleep_pressure"] * sp +
        w["fatigue"] * fatigue +
        w["low_sleep_q"] * low_sq +
        w["stress"] * stress +
        w["circadian"] * max(0.0, C)
    )
    hour = int(_get(st, "time_hour", 0))
    sleep_pressure = _clip01(_get(st, "sleep_pressure", 0.0))
    fatigue = _clip01(_get(st, "fatigue", 0.0))
    exam_urgency = _clip01(_get(st, "exam_urgency", 0.0))
    if hour < 21 and max(sleep_pressure, fatigue) < 0.75:
        score -= 0.04
    if hour < 22:
        tired = max(sleep_pressure, fatigue)
        if tired < 0.70 and exam_urgency >= 0.35:
            score -= 0.16
        elif tired < 0.70:
            score -= 0.10
    last_b = st.get("last_behavior", None) or st.get("last_action", None)
    if hour < 22 and last_b == "sleep":
        score -= 0.08
    return score

def score_study(st, w):
    exam = _clip01(_get(st, "exam_urgency", 0.4))
    undone = _clip01(1.0 - _get(st, "task_done", 0.2))
    energy = _clip01(_get(st, "energy", 0.5))
    low_hunger = _clip01(1.0 - _get(st, "hunger", 0.3))
    stress = _clip01(_get(st, "stress", 0.3))
    stress_gain = 1.0 - abs(stress - 0.5) * 2.0
    score = (
        w["exam_urgency"] * exam +
        w["undone"] * undone +
        w["energy"] * energy +
        w["low_hunger"] * low_hunger +
        w["moderate_stress"] * stress_gain
    )
    return score

def score_cook(st, w):
    hunger = _clip01(_get(st, "hunger", 0.3))
    time_ok = _clip01(_get(st, "time_available", 1.0) / 2.0)
    energy = _clip01(_get(st, "energy", 0.5))
    score = w["hunger"] * hunger + w["time_ok"] * time_ok + w["energy"] * energy
    hour = int(_get(st, "time_hour", 12))
    if 7 <= hour <= 9: score += 0.08
    elif 12 <= hour <= 13: score += 0.10
    elif 18 <= hour <= 19: score += 0.12
    kitchen = _get(st, "kitchen", 1.0)
    if hunger < 0.65 and kitchen < PARAMS["kitchen_avail_threshold"]:
        score -= 0.10 * (PARAMS["kitchen_avail_threshold"] - kitchen + 1.0)
    return score

def score_shower(st, w):
    stress = _clip01(_get(st, "stress", 0.3))
    low_sq = _clip01(1.0 - _get(st, "sleep_quality", 0.5))
    fatigue = _clip01(_get(st, "fatigue", 0.4))
    score = w["stress"] * stress + w["low_sleep_q"] * low_sq + w["fatigue"] * fatigue
    hour = int(_get(st, "time_hour", 12))
    if 7 <= hour <= 9 or 21 <= hour <= 23:
        score += 0.06
    bathroom = _get(st, "bathroom", 1.0)
    if bathroom < PARAMS["bathroom_avail_threshold"]:
        score -= 0.10 * (PARAMS["bathroom_avail_threshold"] - bathroom + 1.0)
    return score

def score_clean(st, w):
    room_dirty = _clip01(_get(st, "room_dirty", 0.4))
    complaints = _clip01(_get(st, "complaints", 0.0))
    energy = _clip01(_get(st, "energy", 0.5))
    return w["room_dirty"] * room_dirty + w["complaints"] * complaints + w["energy"] * energy

def score_lounge(st, w):
    hour = int(_get(st, "time_hour", 12))
    social = _clip01(_get(st, "social_need", 0.3))
    stress = _clip01(_get(st, "stress", 0.3))
    flatmates = max(0.0, _get(st, "flatmates", 0.0))
    score = (
        w["social_need"] * social +
        w["evening"] * _evening_bonus(hour) +
        w["flatmates"] * _clip01(flatmates / 3.0) +
        w["stress"] * _clip01(stress) * 0.8
    )
    comp_prev = _clip01(_get(st, "complaints_prev", 0.0))
    if comp_prev > 0.0:
        score -= 0.06 * (1.0 + comp_prev)
    if 18 <= hour <= 21:
        score += 0.08 * _clip01(flatmates / 2.0)
    return score

def score_play(st, w):
    stress = _clip01(_get(st, "stress", 0.3))
    energy = _clip01(_get(st, "energy", 0.5))
    time_ok = _clip01(_get(st, "time_available", 1.0) / 2.0)
    score = w["high_stress"] * stress + w["energy"] * energy + w["time_ok"] * time_ok
    comp_prev = _clip01(_get(st, "complaints_prev", 0.0))
    if comp_prev > 0.0:
        score -= 0.05 * (1.0 + comp_prev)
    if 18 <= int(_get(st, "time_hour", 0)) <= 21:
        score += 0.08 * _clip01(_get(st, "flatmates", 0.0) / 2.0)
    return score

SCORERS = {
    "sleep":  score_sleep,
    "study":  score_study,
    "cook":   score_cook,
    "shower": score_shower,
    "clean":  score_clean,
    "lounge": score_lounge,
    "play":   score_play,
}

def _apply_cooldown_and_stickiness(raw_scores, st):
    """Apply cooldown penalties and stickiness bonus."""
    scores = dict(raw_scores)
    cooldowns = st.get("cooldowns", {}) or {}
    if isinstance(cooldowns, dict):
        max_cd = max([1] + list(cooldowns.values()))
        for act, cd_left in cooldowns.items():
            if act in scores and cd_left > 0:
                frac = cd_left / max_cd
                scores[act] -= PARAMS["cooldown_penalty_scale"] * frac
    last_b = st.get("last_behavior", None) or st.get("last_action", None)
    if last_b in scores:
        scores[last_b] += PARAMS["stickiness_bonus"]
    return scores

def _apply_dynamic_crowd(scores, st):
    """Apply crowd penalty based on hourly_counts if available."""
    hourly = st.get("hourly_counts", None)
    if not isinstance(hourly, dict):
        return scores
    out = dict(scores)
    kcap = max(1, int(st.get("kitchen_cap", PARAMS["kitchen_capacity"])))
    bcap = max(1, int(st.get("bathroom_cap", PARAMS["bathroom_capacity"])))
    per_p = PARAMS["crowd_penalty_per_extra"]
    n_cook = max(0, int(hourly.get("cook", 0)))
    if n_cook > kcap and "cook" in out:
        out["cook"] -= per_p * (n_cook - kcap)
    n_sh = max(0, int(hourly.get("shower", 0)))
    if n_sh > bcap and "shower" in out:
        out["shower"] -= per_p * (n_sh - bcap)
    n_lg = max(0, int(hourly.get("lounge", 0)))
    if n_lg > 2 and "lounge" in out:
        out["lounge"] -= per_p * 0.5 * (n_lg - 2)
    n_py = max(0, int(hourly.get("play", 0)))
    if n_py > 1 and "play" in out:
        out["play"] -= per_p * 0.5 * (n_py - 1)
    return out

def _regularize(scores):
    """Clamp extreme negatives for softmax stability."""
    floor = PARAMS["base_floor"]
    return {a: max(floor, s) for a, s in scores.items()}

def utility_decision(state, rng=None, debug=False):
    """
    Compute utility for each action -> sample/select -> return action name.

    Args:
        state: dict (see module docstring)
        rng:   optional random.Random instance for reproducibility
        debug: if True, attach '__utility_scores' into state (for inspection)

    Returns:
        str: chosen action
    """
    rng = rng or random
    weights = PARAMS["weights"]
    u_state = _normalize_state_for_utility(state)
    raw_scores = {act: SCORERS[act](u_state, weights[act]) for act in ACTIONS}
    scores = _apply_cooldown_and_stickiness(raw_scores, state)
    scores = _apply_dynamic_crowd(scores, state)
    scores = _regularize(scores)
    if debug:
        state["__utility_scores"] = dict(sorted(scores.items(), key=lambda kv: -kv[1]))
    if rng.random() < PARAMS["epsilon"]:
        action = _softmax_sample(scores, PARAMS["softmax_temp"], rng)
    else:
        action = max(scores.items(), key=lambda kv: kv[1])[0]
    return action
