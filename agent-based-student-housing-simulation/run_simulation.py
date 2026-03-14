# run_simulation.py — scenario overlays + console behavior log + CSV saving
import argparse
import os
from copy import deepcopy
from datetime import datetime
import random
import numpy as np
import pandas as pd

import config  # baseline states & preferences
from environment import SharedHouse


# ---------- Scenario overlay helpers ----------
def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

def apply_scenario_overlay(base_states: dict, scenario: str):
    """
    Apply an in-memory overlay to baseline student_states.
    Does not modify config.py on disk.
    Assumes each state field is on 0–1 scale (agents.py scales them to 0–10/100 later).
    """
    states = deepcopy(base_states)
    if scenario in ("baseline", None):
        return states

    for name, s in states.items():
        exam_urgency   = float(s.get("exam_urgency", 0.0))
        task_done      = float(s.get("task_done", 1.0))
        time_available = float(s.get("time_available", 0.5))
        sleep_quality  = float(s.get("sleep_quality", 0.6))

        if scenario == "exam_moderate":
            exam_urgency   = _clip01(exam_urgency + 0.40)
            task_done      = _clip01(task_done - 0.30)
            time_available = _clip01(time_available - 0.50)
            sleep_quality  = _clip01(sleep_quality - 0.50)

        elif scenario == "exam_strong":
            exam_urgency   = _clip01(exam_urgency + 0.60)
            task_done      = _clip01(task_done - 0.50)
            time_available = _clip01(time_available - 0.80)
            sleep_quality  = _clip01(sleep_quality - 0.80)

        s["exam_urgency"]   = exam_urgency
        s["task_done"]      = task_done
        s["time_available"] = time_available
        s["sleep_quality"]  = sleep_quality

    return states


# ---------- Console printing ----------
def print_behavior_log_console(house):
    """
    Print a concise behavior log to console.
    Requires house.get_behavior_log_rows() -> [{'hour','name','action'}, ...]
    """
    rows = house.get_behavior_log_rows()
    print("\nBehavior Log:")
    for r in rows:
        hour = r.get("hour", r.get("Hour", "?"))
        name = r.get("name", r.get("Agent", ""))
        action = r.get("action", r.get("Behavior", ""))
        try:
            hour_str = f"{int(hour):02d}"
        except Exception:
            hour_str = str(hour)
        print(f"Hour {hour_str} | {name:<5} -> {action}")

# ---------- Logging helpers ----------
def ensure_logs_dir(path="logs"):
    os.makedirs(path, exist_ok=True)
    return path

def build_log_filename(experiment_type: str, scenario: str, timestamp: datetime):
    return f"behavior_log_{experiment_type}_{scenario}_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"

def save_behavior_log(house: SharedHouse, experiment_type: str, scenario: str, out_dir="logs"):
    ts = datetime.now()
    ensure_logs_dir(out_dir)
    rows = house.get_behavior_log_rows()
    df = pd.DataFrame(rows).rename(columns={
        "hour": "Hour",
        "name": "Agent",
        "action": "Behavior"
    })
    filename = build_log_filename(experiment_type, scenario, ts)
    path = os.path.join(out_dir, filename)
    df.to_csv(path, index=False)
    print(f"\nBehavior CSV saved: {path}")
    return path


# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(description="Run shared house simulation with scenario overlays.")
    parser.add_argument("experiment_type", type=str,
                        help="Experiment type key (must exist in config.experiment_settings)")
    parser.add_argument("--hours", type=int, default=24, help="Simulation hours (default: 24)")
    parser.add_argument("--seed", type=int, default=1, help="Random seed (default: 1)")
    parser.add_argument("--debug", action="store_true", help="Print per-hour debug info")
    parser.add_argument("--kitchen-cap", type=int, default=2, help="Kitchen capacity (default: 2)")
    parser.add_argument("--bathroom-cap", type=int, default=1, help="Bathroom capacity (default: 1)")
    parser.add_argument("--logs", type=str, default="logs", help="Output directory for logs (default: logs)")
    parser.add_argument("--scenario",
        choices=["baseline", "exam_moderate", "exam_strong"],
        default="baseline",
        help="Apply in-memory scenario overlay (does NOT modify config.py)."
    )

    args = parser.parse_args()
    long_horizon = (args.hours or 24) > 24

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    student_states_overlaid = apply_scenario_overlay(config.student_states, args.scenario)
    student_prefs_overlaid = None

    house = SharedHouse(
        experiment_type=args.experiment_type,
        debug=args.debug,
        hours=args.hours,
        kitchen_capacity=args.kitchen_cap,
        bathroom_capacity=args.bathroom_cap,
        student_states_override=student_states_overlaid,
        student_preferences_override=student_prefs_overlaid,
        long_horizon=long_horizon,
    )

    log_dir = args.logs
    if args.seed is not None:
        log_dir = os.path.join(log_dir, f"seed_{args.seed}")
    os.makedirs(log_dir, exist_ok=True)

    house.run_one_day(hours=args.hours, debug=args.debug)

    rows = house.get_behavior_log_rows()
    df_seed = pd.DataFrame(rows).rename(columns={
        "hour": "Hour",
        "name": "Agent",
        "action": "Behavior"
    })
    outfile = os.path.join(log_dir, f"results_seed{args.seed}.csv")
    df_seed.to_csv(outfile, index=False, encoding="utf-8")
    print(f"✅ Seed-level CSV saved: {outfile}")

    print_behavior_log_console(house)
    save_behavior_log(house, args.experiment_type, args.scenario, out_dir=log_dir)


if __name__ == "__main__":
    main()
