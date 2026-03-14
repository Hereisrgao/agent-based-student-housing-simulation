# environment.py — Dynamic global inputs + labeled debug output

from typing import Dict, List, Tuple, Any
from agents import StudentAgent
from config import student_states, student_preferences, experiment_settings


MODEL_TAG = {
    'fuzzy':   'Fuzzy',
    'utility': 'Utility',
    'rule':    'Rule',
    'other':   'Rule'
}


class SharedHouse:
    def __init__(self, experiment_type: str, **kwargs):
        self.debug = bool(kwargs.get('debug', False))
        self.default_hours = int(kwargs.get('hours', 24))
        # CLI capacity parameters (defaults: kitchen=2, bathroom=1)
        self.kitchen_cap = int(kwargs.get('kitchen_capacity', 2))
        self.bathroom_cap = int(kwargs.get('bathroom_capacity', 1))
        
        student_states_override = kwargs.get('student_states_override', None)
        student_prefs_override  = kwargs.get('student_preferences_override', None)

        self.agents: List[StudentAgent] = []
        self.time_hour: int = 0
        self.experiment_type = experiment_type
        # hour, name, action, model, score, awake
        self.behavior_log: List[Tuple[int, str, str]] = []
        self._complaints: int = 0
        self._complaints_prev: int = 0

        from config import student_states as _base_states
        from config import student_preferences as _base_prefs

        STATES = student_states_override if isinstance(student_states_override, dict) else _base_states
        PREFS  = student_prefs_override  if isinstance(student_prefs_override, dict)  else _base_prefs

        required_names = ["Bruce", "Clark", "Diana", "Barry", "Lex"]
        missing = [n for n in required_names if n not in STATES or n not in PREFS]
        if missing:
            raise ValueError(f"Missing initial state or preferences for: {missing}")

        from config import experiment_settings
        if experiment_type not in experiment_settings:
            raise ValueError(f"experiment_settings does not include: {experiment_type}")

        for idx, name in enumerate(required_names):
            model_type = experiment_settings[experiment_type].get(name, 'utility')
            if model_type == 'other':      
                model_type = 'rule'
            state = STATES[name]
            pref = PREFS[name]
            self.agents.append(
                StudentAgent(id=idx, name=name, model_type=model_type,
                            init_state=state, preferences=pref)
            )
        self.long_horizon = bool(kwargs.get('long_horizon', False))

        from collections import deque
        for a in self.agents:
            setattr(a, "long_horizon", self.long_horizon)
            if not hasattr(a, "hist_study"):  a.hist_study  = deque(maxlen=24)
            if not hasattr(a, "hist_sleep"):  a.hist_sleep  = deque(maxlen=24)
            if not hasattr(a, "hist_lounge"): a.hist_lounge = deque(maxlen=24)
            if not hasattr(a, "shower_gap"):  a.shower_gap  = 0
            if not hasattr(a, "clean_gap"):   a.clean_gap   = 0

    def _build_global_inputs(self, prev_behaviors: List[Tuple[str, str]], hour: int) -> Dict[str, Any]:
        kitchen = 0.5
        bathroom = 2.5
        flatmates = 0
        complaints = int(getattr(self, "_complaints", 0))
        time_available = 3.5

        if prev_behaviors:
            cooks   = sum(1 for _, b in prev_behaviors if b == 'cook')
            showers = sum(1 for _, b in prev_behaviors if b == 'shower')
            lounges = sum(1 for _, b in prev_behaviors if b == 'lounge')
            cleans  = sum(1 for _, b in prev_behaviors if b == 'clean')
            studies = sum(1 for _, b in prev_behaviors if b == 'study')

            kitchen   = min(3.0, 0.5 + 0.9 * cooks)
            bathroom  = max(0.5, 3.0 - 0.8 * showers)
            flatmates = min(4, lounges)
            base = 3.5
            time_available = max(0.5, base - 0.2 * (cooks + showers + cleans + studies))

        return {
            'kitchen': float(f"{kitchen:.2f}"),
            'bathroom': float(f"{bathroom:.2f}"),
            'time_hour': hour,
            'flatmates': flatmates,
            'complaints': complaints,
            'time_available': float(f"{time_available:.2f}"),
            'hourly_counts': {
                'cook':   sum(1 for _, b in prev_behaviors if b == 'cook'),
                'shower': sum(1 for _, b in prev_behaviors if b == 'shower'),
                'lounge': sum(1 for _, b in prev_behaviors if b == 'lounge'),
                'play':   sum(1 for _, b in prev_behaviors if b == 'play'),
            },
            'complaints_prev': int(getattr(self, '_complaints_prev', 0)),
            'kitchen_cap': int(getattr(self, 'kitchen_cap', 2)),
            'bathroom_cap': int(getattr(self, 'bathroom_cap', 1)),
        }

    def _apply_capacity_limits(self, hour_alloc: List[Dict[str, Any]], caps: Dict[str, int]):
        from collections import Counter
        counts = Counter([x['action'] for x in hour_alloc])
        def reduce_action(action_name: str, cap: int):
            if counts.get(action_name, 0) <= cap:
                return
            candidates = [x for x in hour_alloc if x['action'] == action_name]
            for c in candidates:
                sc = c.get('scores', {})
                c['_this_score'] = float(sc.get(action_name, 0.0))
            candidates.sort(key=lambda x: x.get('_this_score', 0.0))

            while counts.get(action_name, 0) > cap and candidates:
                i_chosen = candidates.pop(0)
                counts[action_name] -= 1
                sorted_items = list((i_chosen.get('scores') or {}).items())
                sorted_items.sort(key=lambda kv: -kv[1])
                new_action = 'idle'
                for k, _v in sorted_items:
                    if k != action_name:
                        new_action = k
                        break
                i_chosen['action'] = new_action
                counts[new_action] = counts.get(new_action, 0) + 1

        if 'shower' in caps:
            reduce_action('shower', caps['shower'])
        if 'cook' in caps:
            reduce_action('cook', caps['cook'])

    @staticmethod
    def _score_label(model_type: str) -> str:
        if model_type == 'utility':
            return "Utility 0–1"
        if model_type == 'fuzzy':
            return "Fuzzy 0–10"
        if model_type in ('rule', 'other'):
            return "Rule 0–10"
        return "Scores"

    def _format_top3(self, scores: dict) -> str:
        if not scores:
            return ""
        items = []
        for k, v in scores.items():
            try:
                items.append((k, float(v)))
            except Exception:
                continue
        items.sort(key=lambda kv: -kv[1])
        items = items[:3]
        return ", ".join(f"{k}:{v:.2f}" for k, v in items)

    def run_one_day(self, hours: int = None, total_hours: int = None, debug: bool = None, **kwargs):
        """
        Ensure per-hour per-agent logging (even if agent is not awake -> 'sleep').
        """
        if hours is None and total_hours is not None:
            hours = total_hours
        if hours is None:
            hours = getattr(self, 'default_hours', 24)
        if debug is None:
            debug = getattr(self, 'debug', False)

        hard_caps = {
            'cook':   getattr(self, 'kitchen_cap', 2),
            'shower': getattr(self, 'bathroom_cap', 1),
        }
        prev_behaviors: List[Tuple[str, str]] = []

        for hour in range(hours):
            self.time_hour = hour

            awake_flags = {a.name: a.is_awake(hour) for a in self.agents}
            for a in self.agents:
                if awake_flags[a.name] and hasattr(a, "base_drift"):
                    a.base_drift(hour)

            self._complaints = 0
            global_inputs = self._build_global_inputs(prev_behaviors, hour)

            if debug:
                print(f"\n⏰ Hour {hour:02d}")
                prev_str = ", ".join([f"{n}:{b}" for n, b in prev_behaviors]) if prev_behaviors else "[]"
                awake_str = ", ".join([n for n, aw in awake_flags.items() if aw]) or "None"
                g_disp = {k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in global_inputs.items()}
                print(f"Prev hour: {prev_str}")
                print(f"Awake agent: {awake_str}")
                print(f"Global state: {g_disp}")
                print("Agent decision (model | action | Top-3 scores):")

            hour_alloc: List[Dict[str, Any]] = []
            for agent in self.agents:
                is_awake = bool(awake_flags[agent.name])
                chosen_action = 'sleep' if not is_awake else 'idle'
                all_scores: Dict[str, float] = {}

                if is_awake:
                    try:
                        state = agent.get_full_state(global_inputs)
                        decision = agent.decide_behavior(state)
                        if isinstance(decision, tuple) and len(decision) == 2:
                            chosen_action = str(decision[0]).lower().strip()
                            ut = decision[1] or {}
                            all_scores = {k: float(v) for k, v in ut.items() if isinstance(v, (int, float))}
                        else:
                            chosen_action = str(decision).lower().strip()
                            if not all_scores:
                                fallback_scores = state.get("__utility_scores") or state.get("__rule_scores") or {}
                                if isinstance(fallback_scores, dict):
                                    all_scores = {k: float(v) for k, v in fallback_scores.items() if isinstance(v, (int, float))}
                    except Exception as e:
                        chosen_action = 'idle'
                        if debug:
                            print(f"  ⚠️ {agent.name} decision error: {e} -> idle")

                chosen_score = float(all_scores.get(chosen_action, 0.0)) if all_scores else 0.0

                hour_alloc.append({
                    'name': agent.name,
                    'model': agent.model_type,
                    'action': chosen_action,
                    'scores': all_scores,
                    'score': chosen_score,
                    'awake': 1 if is_awake else 0,
                })

                if debug and is_awake:
                    tag = MODEL_TAG.get(agent.model_type, agent.model_type)
                    top3 = self._format_top3(all_scores)
                    label = self._score_label(agent.model_type)
                    if top3:
                        print(f"  {agent.name:6s} [{tag:6s}] ➜ {chosen_action:<7s} | {label}: {top3}")
                    else:
                        print(f"  {agent.name:6s} [{tag:6s}] ➜ {chosen_action}")

            self._apply_capacity_limits(hour_alloc, hard_caps)

            hour_behaviors: List[Tuple[str, str]] = []
            for x in hour_alloc:
                hour_behaviors.append((x['name'], x['action']))
                self.behavior_log.append((hour, x['name'], x['action'], x['model'], x.get('score', 0.0), x.get('awake', 0)))

            for agent in self.agents:
                if not awake_flags[agent.name]:
                    continue
                try:
                    other_behaviors = [b for n, b in hour_behaviors if n != agent.name]
                    agent.influence_from_others(other_behaviors)
                except Exception:
                    pass

            for agent in self.agents:
                if not awake_flags[agent.name]:
                    continue
                try:
                    act = next((a for n, a in hour_behaviors if n == agent.name), 'idle')
                    agent.update_state(act, global_inputs)
                except Exception:
                    pass

            try:
                lounges_now = sum(1 for _, act in hour_behaviors if act == 'lounge')
                self._complaints = max(0, lounges_now - 3)
            except Exception:
                self._complaints = 0
            self._complaints_prev = self._complaints
            if debug:
                print(f"  End-of-hour {hour:02d} ▶ lounges:{lounges_now}  complaints:{self._complaints}")

            prev_behaviors = hour_behaviors[:]
            
            if getattr(self, "long_horizon", False):
                name2act = {n: a for (n, a) in hour_behaviors}
                for agent in self.agents:
                    act = name2act.get(agent.name, 'idle')
                    try:
                        agent.update_long_horizon_counters(act)
                    except Exception:
                        pass

    def get_behavior_log_rows(self):
        """
        Always returns rows with: hour, name, action, model, score, awake.
        Compatible with both 3-tuple and 6-tuple behavior logs.
        """
        rows = []
        for tpl in getattr(self, "behavior_log", []):
            if isinstance(tpl, (list, tuple)):
                if len(tpl) >= 6:
                    h, n, a, m, s, aw = tpl[:6]
                elif len(tpl) == 3:
                    h, n, a = tpl
                    m, s, aw = "", 0.0, 0
                else:
                    continue
            else:
                continue

            try:
                h = int(h)
            except Exception:
                pass
            try:
                s = float(s)
            except Exception:
                s = 0.0
            try:
                aw = int(aw)
            except Exception:
                aw = 0

            mm = str(m).lower()
            if mm in ("other", "rule_based"):
                mm = "rule"
            rows.append({
                "hour": h,
                "name": str(n),
                "action": str(a),
                "model": mm,
                "score": s,
                "awake": aw,
            })
        return rows
