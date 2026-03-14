# -*- coding: utf-8 -*-
# =========================================================
# Main.py — Demo runner for Fuzzy / Utility / Rule-based
# =========================================================

from __future__ import annotations

# ---- Fuzzy modules
from Fuzzy import (
    get_cook_score,   # get_cook_score(hunger_val, kitchen_val)
    get_shower_score, # get_shower_score(fatigue_val, time_val, bathroom_val)
    get_clean_score,  # get_clean_score(room_dirty_val, energy_val, complaints_val)
    get_study_score,  # get_study_score(energy_val, exam_urgency_val, time_available_val)
    get_play_score,   # get_play_score(stress_val, energy_val, task_done_val)
    get_sleep_score,  # get_sleep_score(tiredness_val, time_hour_val, sleep_quality_val, exam_urgency_val)
    get_lounge_score  # get_lounge_score(social_need_val, flatmates_val, time_hour_val)
)

# ---- Utility modules (robust import + graceful fallback)
utility_compute = None
try:
    # Prefer compute_utilities if provided in utility.py
    from utility import compute_utilities as utility_compute  # type: ignore
except Exception:
    utility_compute = None

from utility import utility_decision  # always available as fallback

# ---- Rule-based modules
from RuleBased import get_rule_based_scores, get_best_action_rule_based


# ========== Demo agent state (natural scales) ==========
# This is a single snapshot of environment/agent variables for demo.
state = {
    # Cooking
    "hunger": 80,          # 0~100
    "kitchen": 1.5,        # 0~3 (larger = more crowded / less available)

    # Shower
    "fatigue": 60,         # 0~100
    "time_hour": 21,       # 0~23
    "bathroom": 1.2,       # 0~3 (larger = more crowded)

    # Cleaning
    "room_dirty": 55,      # 0~100
    "energy": 65,          # 0~100
    "complaints": 1,       # 0~10

    # Study
    "exam_urgency": 7,     # 0~10
    "time_available": 3.5, # 0~10

    # Play & Lounge
    "stress": 45,          # 0~100
    "task_done": 0.4,      # 0~1 (share of tasks completed; demo only)
    "social_need": 70,     # 0~100
    "flatmates": 2,        # 0~10

    # Optional: cooldowns / last behavior (used by utility; can be omitted)
    # "last_behavior": "study",
    # "cooldowns": {"shower": 1},
    # "hourly_counts": {"cook": 0, "shower": 0, "lounge": 0, "play": 0},
}


# ---------- Helpers (normalize to 0~1 or keep native) ----------
def _01(x, denom):
    """Normalize x to 0~1 by denom with clipping."""
    x = float(x) / float(denom)
    return max(0.0, min(1.0, x))

def _kitchen01(k):   # 0~3 → 0~1
    return _01(k, 3.0)

def _bathroom01(b):  # 0~3 → 0~1
    return _01(b, 3.0)


# ========== Compute Fuzzy scores (0~10) ==========
fuzzy_scores = {
    "cook":   round(get_cook_score(_01(state["hunger"], 100), state["kitchen"]), 2),
    # get_shower_score(fatigue_val, time_val, bathroom_val)
    "shower": round(get_shower_score(_01(state["fatigue"], 100), state["time_hour"], state["bathroom"]), 2),
    # get_clean_score(room_dirty_val, energy_val, complaints_val)
    "clean":  round(get_clean_score(_01(state["room_dirty"], 100), _01(state["energy"], 100), _01(state["complaints"], 10)), 2),
    # get_study_score(energy_val, exam_urgency_val, time_available_val)
    "study":  round(get_study_score(_01(state["energy"], 100), _01(state["exam_urgency"], 10), _01(state["time_available"], 10)), 2),
    # get_play_score(stress_val, energy_val, task_done_val)
    "play":   round(get_play_score(_01(state["stress"], 100), _01(state["energy"], 100), float(state.get("task_done", 0.0))), 2),
    # get_sleep_score(tiredness_val, time_hour_val, sleep_quality_val, exam_urgency_val)
    # Here, fatigue stands in for tiredness; assume sleep_quality = 0.6 (adjust as needed)
    "sleep":  round(get_sleep_score(_01(state["fatigue"], 100), state["time_hour"], 0.6, _01(state["exam_urgency"], 10)), 2),
    # get_lounge_score(social_need_val, flatmates_val, time_hour_val)
    "lounge": round(get_lounge_score(_01(state["social_need"], 100), _01(state["flatmates"], 10), state["time_hour"]), 2),
}
fuzzy_best = max(fuzzy_scores, key=fuzzy_scores.get)

# ========== Compute Utility scores (×10 for display alignment) ==========
def _get_utility_scores_via_fallback(st: dict) -> dict:
    """If compute_utilities is unavailable, fall back to utility_decision(debug=True) to fill scores."""
    st2 = dict(st)  # avoid mutating original state
    _ = utility_decision(st2, debug=True)
    scores = st2.get("__utility_scores", {})
    return dict(scores)

if utility_compute is not None:
    try:
        utility_scores = dict(utility_compute(state))
    except Exception:
        utility_scores = _get_utility_scores_via_fallback(state)
else:
    utility_scores = _get_utility_scores_via_fallback(state)

# Display-only rescaling: map 0~1 to 0~10 to align with Fuzzy/Rule (no logic impact)
utility_scores_rescaled = {k: round(v * 10.0, 2) for k, v in utility_scores.items()}
utility_best = max(utility_scores_rescaled, key=utility_scores_rescaled.get) if utility_scores_rescaled else "N/A"

# ========== Compute Rule-based scores ==========
rule_scores = get_rule_based_scores(state)
rule_best = get_best_action_rule_based(state)

# ========== Pretty printing ==========
def _top3(d: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(d.items(), key=lambda kv: -kv[1])[:3]

print("\n📊 推荐分数（Recommendation Scores）")
print("Fuzzy:   ", fuzzy_scores)
print("Utility: ", utility_scores_rescaled)  # aligned to 0–10 for display
print("Rule:    ", rule_scores)

print("\n🏆 最佳行为（Best Action）")
print(f"Fuzzy:    {fuzzy_best}   | Top-3: {_top3(fuzzy_scores)}")
print(f"Utility:  {utility_best} | Top-3: {_top3(utility_scores_rescaled)}")
print(f"Rule:     {rule_best}    | Top-3: {_top3(rule_scores)}")

print("\nℹ️ 说明 Notes")
print("- Fuzzy inputs are normalized here (0–100→0–1; kitchen/bathroom 0–3→0–1).")
print("- Utility display ×10 to align with 0–10 scale (no impact on logic or choice).")
print("- Utility prefers compute_utilities; if unavailable, uses utility_decision(debug=True) to backfill.")
print("- Rule-based uses thresholds as defined in RuleBased.py.")
