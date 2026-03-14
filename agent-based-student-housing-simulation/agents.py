# -*- coding: utf-8 -*-
from typing import Dict, Any
from config import student_states, student_preferences
import random
from collections import deque

LABEL_ZH = {
    'sleep': '睡觉', 'study': '学习', 'cook': '做饭',
    'shower': '洗澡', 'clean': '打扫', 'lounge': '客厅', 'play': '娱乐'
}


class StudentAgent:
    def __init__(self, id: int, name: str, model_type: str,
                 init_state: Dict[str, float], preferences: Dict[str, float]):
        self.id = id
        self.name = name
        self.model_type = model_type  # 'fuzzy' | 'utility' | 'other'(rule-based)
        self.preferences = preferences

        self.hunger = init_state.get("hunger", 0.5)
        self.fatigue = init_state.get("fatigue", 0.5)
        self.stress = init_state.get("stress", 0.5)
        self.exam_urgency = init_state.get("exam_urgency", 0.5) * 10.0
        self.sleep_quality = init_state.get("sleep_quality", 0.5) * 10.0
        self.room_dirty = init_state.get("room_dirty", 0.5) * 100.0
        self.social_need = init_state.get("social_need", 0.5) * 100.0
        self.task_done = init_state.get("task_done", 0.5) * 10.0

        self.last_behavior = None
        self.cooldowns: Dict[str, int] = {}
        self.S = 0.0  # sleep_pressure
        self.sleep_debt = 0.0
        self.hours_since_shower = 0
        self.consecutive_lounge = 0
        self.hist_study  = deque(maxlen=24)
        self.hist_sleep  = deque(maxlen=24)
        self.hist_lounge = deque(maxlen=24)
        self.shower_gap  = 0
        self.long_horizon = False
        self.clean_gap = 0

    # Awake schedule predicate
    def is_awake(self, hour: int) -> bool:
        wake_up = self.preferences.get("wake_up_hour", 8)
        sleep_h = self.preferences.get("sleep_hour", 23)
        if wake_up <= sleep_h:
            return wake_up <= hour < sleep_h
        else:
            return hour >= wake_up or hour < sleep_h

    # Baseline natural drift per hour
    def base_drift(self, hour: int):
        self.hunger = min(1.0, self.hunger + 0.06)
        self.fatigue = min(1.0, self.fatigue + 0.03)
        self.stress = min(1.0, self.stress + 0.02)
        self.room_dirty = min(100.0, self.room_dirty + 1.0)

    # Compose full state for models
    def get_full_state(self, global_env: Dict[str, Any]) -> Dict[str, Any]:
        hour = int(global_env['time_hour'])
        awake = self.is_awake(hour)
        self.S = min(1.0, self.S + (0.06 if awake else -0.08))
        self.S = max(0.0, self.S)

        if 22 <= hour or hour <= 6:
            C = 0.8
        elif 7 <= hour <= 11:
            C = -0.2
        elif 12 <= hour <= 17:
            C = -0.1
        else:
            C = 0.2

        state = {
            # Internal states
            'hunger': self.hunger,
            'fatigue': self.fatigue,
            'stress': self.stress,
            'exam_urgency': self.exam_urgency,
            'sleep_quality': self.sleep_quality,
            'room_dirty': self.room_dirty,
            'social_need': self.social_need,
            'task_done': self.task_done,

            'energy': max(0.0, 1.0 - self.fatigue),
            'tiredness': self.fatigue,

            # External environment (original scaling preserved)
            'kitchen': global_env['kitchen'],
            'bathroom': global_env['bathroom'],
            'time_hour': hour,
            'flatmates': global_env['flatmates'],
            'complaints': global_env['complaints'],
            'complaints_prev': global_env.get('complaints_prev', 0),
            'time_available': global_env['time_available'],

            'sleep_pressure': self.S,
            'circadian': C,
            'cooldowns': dict(self.cooldowns),

            'sleep_debt': self.sleep_debt,
            'hours_since_shower': self.hours_since_shower,
            'consecutive_lounge': self.consecutive_lounge,

            'preferences': self.preferences,
            'agent_name': self.name,
        }

        # Optional extra fields from env
        for k in ('dirtiness',):
            if k in global_env:
                state[k] = global_env[k]
        return state

    def update_long_horizon_counters(self, action: str):
        """Roll 24h counters and shower/clean gaps."""
        a = (action or 'idle').lower()
        self.hist_study.append(1 if a == 'study'  else 0)
        self.hist_sleep.append(1 if a == 'sleep'  else 0)
        self.hist_lounge.append(1 if a == 'lounge' else 0)
        if a == 'shower':
            self.shower_gap = 0
        else:
            self.shower_gap += 1
        if not hasattr(self, 'clean_gap'):
            self.clean_gap = 0
        if a == 'clean':
            self.clean_gap = 0
        else:
            self.clean_gap += 1

    def apply_long_horizon_nudges(self, scores: Dict[str, float], time_hour: int, env: Dict[str, Any]):
        """Apply gentle corrections only when long_horizon=True (24h runs unaffected)."""
        if not getattr(self, "long_horizon", False):
            return scores

        s24  = sum(self.hist_study)
        sl24 = sum(self.hist_sleep)
        lg24 = sum(self.hist_lounge)
        gap  = int(getattr(self, "shower_gap", 999))
        cgap = int(getattr(self, "clean_gap", 999))

        bath = float(env.get('bathroom', 2.0))      # 0~3, larger means less crowded
        flatmates = int(env.get('flatmates', 0))
        complaints = int(env.get('complaints', 0))

        # 1) Shower minimum frequency; allow slightly crowded bathroom.
        if gap >= 12 and bath >= 0.5 and (
            (6 <= time_hour <= 8) or (18 <= time_hour <= 22) or time_hour <= 6 or time_hour >= 22
        ):
            scores['shower'] = max(0.0, float(scores.get('shower', 0.0)) + 0.6)

        # 2) Study rebalancing: dampen if already high; encourage if too low during daytime.
        if s24 > 3.0:
            scores['study'] = max(0.0, float(scores.get('study', 0.0)) - 0.4)
        elif s24 < 1.5 and 9 <= time_hour <= 21:
            scores['study'] = max(0.0, float(scores.get('study', 0.0)) + 0.3)

        # 3) Sleep rebalancing: suppress in daytime if already high; encourage at night if low.
        if sl24 > 9.5 and 9 <= time_hour <= 21:
            scores['sleep'] = max(0.0, float(scores.get('sleep', 0.0)) - 0.8)
        elif sl24 < 6.0 and (time_hour >= 23 or time_hour <= 7):
            scores['sleep'] = max(0.0, float(scores.get('sleep', 0.0)) + 0.4)

        # 4) Lounge minimum if almost none and someone is around.
        if lg24 < 1 and flatmates > 0:
            scores['lounge'] = max(0.0, float(scores.get('lounge', 0.0)) + 0.25)

        # 5) Clean trigger after long gap; slightly nudge down study/play to make room.
        if cgap >= 24 and 9 <= time_hour <= 21:
            bump = 0.6 + (0.2 if complaints >= 1 else 0.0)
            scores['clean'] = max(0.0, float(scores.get('clean', 0.0)) + bump)
            scores['study'] = max(0.0, float(scores.get('study', 0.0)) - 0.1)
            scores['play']  = max(0.0, float(scores.get('play', 0.0)) - 0.1)

        return scores

    # Pick behavior based on model type
    def decide_behavior(self, state):
        """
        Returns (action, scores_dict)
        - action: str
        - scores_dict: Dict[str, float] used for debugging/inspection
        """
        action = 'idle'
        scores = {}

        if self.model_type == 'fuzzy':
            from Fuzzy import fuzzy_decision
            res = fuzzy_decision(state, debug=False)
            if isinstance(res, tuple) and len(res) == 2:
                action, scores = res
            else:
                action = res
                scores = {}
        elif self.model_type == 'utility':
            from utility import utility_decision
            res = utility_decision(state, debug=True)
            if isinstance(res, tuple) and len(res) == 2:
                action, scores = res
            else:
                action = res
                scores = state.get("__utility_scores", {}) or {}
        elif self.model_type == 'rule':
            from RuleBased import rule_decision
            action = rule_decision(state, debug=True)
            scores = state.get("__rule_scores", {}) or {}
            scores = {k: float(v) for k, v in scores.items() if isinstance(v, (int, float))}
        else:
            action, scores = 'idle', {}

        # Cooldown & min-interval penalties after model scoring.
        cd = self.cooldowns or {}
        scores = {k: float(v) for k, v in (scores or {}).items() if isinstance(v, (int, float))}

        def penalize(act, factor=0.05, hard=False):
            """Scale score by factor; hard=True -> near-zero."""
            if act in scores:
                scores[act] = (-1e6 if hard else scores[act] * factor)

        # Shower: min interval 6h or active cooldown -> hard block
        if cd.get('shower', 0) > 0 or getattr(self, 'hours_since_shower', 99) < 6:
            penalize('shower', hard=True)

        # Lounge: break streaks (if consecutive >= 2)
        if getattr(self, 'consecutive_lounge', 0) >= 2:
            penalize('lounge', hard=True)

        # Cook: soft penalty during cooldown
        if cd.get('cook', 0) > 0:
            penalize('cook', factor=0.2, hard=False)

        # Clean: soft penalty during cooldown
        if cd.get('clean', 0) > 0:
            penalize('clean', factor=0.2, hard=False)

        # Long-horizon nudges (only when enabled; 24h runs unaffected)
        try:
            time_hour = int(state.get('time_hour', 0)) if isinstance(state, dict) else 0
            scores = self.apply_long_horizon_nudges(scores or {}, time_hour, state if isinstance(state, dict) else {})
        except Exception:
            pass

        # Re-pick action if hard-penalized choice became unrealistic.
        if action in scores:
            if scores[action] < -1e5:
                if scores:
                    action = max(scores.items(), key=lambda kv: kv[1])[0]
        else:
            # If no scores available and the chosen action is hard-blocked, switch to a simple fallback.
            if action in ('shower', 'lounge', 'cook', 'clean') and (
                (action == 'shower' and (cd.get('shower', 0) > 0 or getattr(self, 'hours_since_shower', 99) < 6)) or
                (action == 'lounge' and getattr(self, 'consecutive_lounge', 0) >= 2) or
                (action == 'cook' and cd.get('cook', 0) > 0) or
                (action == 'clean' and cd.get('clean', 0) > 0)
            ):
                action = 'study'  # simple fallback

        self.last_behavior = action
        return action, scores

    # Lightweight social influence example
    def influence_from_others(self, other_behaviors):
        if other_behaviors.count('cook') >= 2:
            self.hunger = min(1.0, self.hunger + 0.03)

    # Apply action effects and update internal counters
    def update_state(self, action: str, global_env: Dict[str, Any]):
        action = (action or 'idle').lower()
        # Decrement cooldowns
        self.cooldowns = {k: max(0, v - 1) for k, v in self.cooldowns.items()}

        if action == 'cook':
            self.hunger = max(0.0, self.hunger - 0.4)
            self.cooldowns['cook'] = 2
        elif action == 'shower':
            self.fatigue = max(0.0, self.fatigue - 0.2)
            self.hours_since_shower = 0
            self.cooldowns['shower'] = 2
        elif action == 'clean':
            self.room_dirty = max(0.0, self.room_dirty - 8.0)
            self.cooldowns['clean'] = 3
        elif action == 'study':
            self.stress = min(1.0, self.stress + 0.02)
            self.task_done = min(10.0, self.task_done + 0.4)
        elif action == 'play':
            self.stress = max(0.0, self.stress - 0.1)
        elif action == 'sleep':
            self.fatigue = max(0.0, self.fatigue - 0.35)
            self.sleep_debt = max(0.0, self.sleep_debt - 0.5)
        elif action == 'lounge':
            self.social_need = max(0.0, self.social_need - 6.0)
            self.cooldowns['lounge'] = 2  # 1-hour cooldown

        if action != 'shower':
            self.hours_since_shower += 1
        if action == 'lounge':
            self.consecutive_lounge += 1
        else:
            self.consecutive_lounge = 0
