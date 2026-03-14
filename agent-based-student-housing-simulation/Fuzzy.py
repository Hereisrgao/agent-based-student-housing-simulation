# =============================================
# Fuzzy.py — sharper membership + S×C sleep + cooldown aware
# =============================================

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# ---------- Utility helpers ----------
def _clip(x, lo, hi):
    return float(min(max(x, lo), hi))

def _safe_compute(sim, output_key, default=4.2):
    """Compute safely; fall back to a neutral-ish default if NaN/Inf/error."""
    try:
        sim.compute()
        val = float(sim.output[output_key])
        if np.isnan(val) or np.isinf(val):
            return float(default)
        return float(val)
    except Exception:
        return float(default)

def _tri_01(var):
    var['low']  = fuzz.trapmf(var.universe, [0.0, 0.0, 0.18, 0.35])
    var['mid']  = fuzz.trimf(var.universe, [0.40, 0.50, 0.60])
    var['high'] = fuzz.trapmf(var.universe, [0.55, 0.75, 1.00, 1.00])

def _out_010(out):
    out['low']  = fuzz.trapmf(out.universe, [0.0, 0.0, 1.8, 3.0])
    out['mid']  = fuzz.trimf(out.universe, [3.2, 4.6, 6.6])
    out['high'] = fuzz.trapmf(out.universe, [8.6, 9.3, 10.0, 10.0])

def _time4(var):
    var['night']     = fuzz.trapmf(var.universe, [0, 0, 5, 6])
    var['morning']   = fuzz.trapmf(var.universe, [5, 7, 10, 12])
    var['afternoon'] = fuzz.trapmf(var.universe, [11, 13, 16, 18])
    var['evening']   = fuzz.trapmf(var.universe, [17, 19, 23, 23])


# ========== 1) Cook ==========
def get_cook_score(hunger_val, kitchen_val):
    hung = ctrl.Antecedent(np.linspace(0,1,101), 'hung')
    kit  = ctrl.Antecedent(np.linspace(0,1,101), 'kit')  # 0..3 scaled to 0..1
    out  = ctrl.Consequent(np.linspace(0,10,101), 'cook_reco', defuzzify_method='mom')
    _tri_01(hung); _tri_01(kit); _out_010(out)

    rules = []
    rules += [ctrl.Rule(hung['high'] & (kit['high'] | kit['mid']), out['high'])]
    rules += [ctrl.Rule(hung['high'] & kit['low'], out['mid'])]
    rules += [ctrl.Rule(hung['mid'] & kit['high'], out['high'])]
    rules += [ctrl.Rule(hung['mid'] & kit['mid'],  out['mid'])]
    rules += [ctrl.Rule(hung['mid'] & kit['low'],  out['low'])]
    rules += [ctrl.Rule(hung['low'], out['low'])]

    system = ctrl.ControlSystem(rules)
    sim = ctrl.ControlSystemSimulation(system)
    sim.input['hung'] = _clip(hunger_val, 0, 1)
    sim.input['kit']  = _clip(kitchen_val/3.0, 0, 1)
    return round(_safe_compute(sim, 'cook_reco'), 2)


# ========== 2) Shower ==========
def get_shower_score(fatigue_val, time_val, bathroom_val):
    fat  = ctrl.Antecedent(np.linspace(0,1,101), 'fat')
    hour = ctrl.Antecedent(np.arange(0,24,1), 'hour')
    bath = ctrl.Antecedent(np.linspace(0,1,101), 'bath')
    out  = ctrl.Consequent(np.linspace(0,10,101), 'shower_reco', defuzzify_method='mom')
    _tri_01(fat); _time4(hour); _tri_01(bath); _out_010(out)

    rules = []
    rules += [ctrl.Rule(bath['low'], out['low'])]
    rules += [ctrl.Rule((hour['morning'] | hour['evening']) & bath['high'] & (fat['mid'] | fat['high']), out['high'])]
    rules += [ctrl.Rule((hour['morning'] | hour['evening']) & bath['mid']  & (fat['mid'] | fat['high']), out['mid'])]
    rules += [ctrl.Rule(hour['night'] & bath['high'] & fat['mid'], out['mid'])]
    rules += [ctrl.Rule(fat['low'], out['low'])]
    rules += [ctrl.Rule(hour['afternoon'] & bath['high'] & fat['mid'], out['mid'])]

    system = ctrl.ControlSystem(rules)
    sim = ctrl.ControlSystemSimulation(system)
    sim.input['fat']  = _clip(fatigue_val, 0, 1)
    sim.input['hour'] = int(_clip(time_val, 0, 23))
    sim.input['bath'] = _clip(bathroom_val/3.0, 0, 1)
    return round(_safe_compute(sim, 'shower_reco', default=4.4), 2)


# ========== 3) Clean ==========
def get_clean_score(room_dirty_val, energy_val, complaints_val):
    dirt = ctrl.Antecedent(np.linspace(0,1,101), 'dirt')
    ener = ctrl.Antecedent(np.linspace(0,1,101), 'ener')
    comp = ctrl.Antecedent(np.linspace(0,1,101), 'comp')
    out  = ctrl.Consequent(np.linspace(0,10,101), 'clean_reco', defuzzify_method='mom')
    _tri_01(dirt); _tri_01(ener); _tri_01(comp); _out_010(out)

    rules = []
    rules += [ctrl.Rule(comp['low'], out['low'])]
    rules += [ctrl.Rule(dirt['low'], out['low'])]
    rules += [ctrl.Rule(dirt['high'] & (comp['mid'] | comp['high']) & ener['high'], out['high'])]
    rules += [ctrl.Rule(dirt['high'] & (comp['mid'] | comp['high']) & ener['mid'],  out['mid'])]
    rules += [ctrl.Rule(dirt['mid'] & comp['high'] & ener['high'], out['mid'])]
    rules += [ctrl.Rule(~(dirt['high'] & (comp['mid'] | comp['high'])), out['low'])]

    system = ctrl.ControlSystem(rules)
    sim = ctrl.ControlSystemSimulation(system)
    sim.input['dirt'] = _clip(room_dirty_val, 0, 1)
    sim.input['ener'] = _clip(energy_val, 0, 1)
    sim.input['comp'] = _clip(complaints_val/10.0, 0, 1)
    return round(_safe_compute(sim, 'clean_reco'), 2)


# ========== 4) Study ==========
def get_study_score(energy_val, exam_urgency_val, time_available_val):
    ene  = ctrl.Antecedent(np.linspace(0,1,101), 'ene')
    exm  = ctrl.Antecedent(np.linspace(0,1,101), 'exm')
    time = ctrl.Antecedent(np.linspace(0,5,101), 'time')
    out  = ctrl.Consequent(np.linspace(0,10,101), 'study_reco', defuzzify_method='mom')

    _tri_01(ene); _tri_01(exm)
    time['short'] = fuzz.trapmf(time.universe, [0,0,1,2])
    time['mid']   = fuzz.trimf(time.universe, [1.6,2.5,3.4])
    time['long']  = fuzz.trapmf(time.universe, [3.0,4.0,5.0,5.0])
    _out_010(out)

    rules = []
    rules += [ctrl.Rule(exm['high'] & time['mid'] & (ene['mid'] | ene['high']), out['mid'])]
    rules += [ctrl.Rule(exm['high'] & time['long'] & ene['high'], out['high'])]
    rules += [ctrl.Rule(exm['high'] & time['short'], out['mid'])]
    rules += [ctrl.Rule(exm['mid'] & time['long'] & ene['high'], out['high'])]
    rules += [ctrl.Rule(exm['mid'] & time['mid'], out['mid'])]
    rules += [ctrl.Rule(exm['mid'] & time['short'], out['low'])]
    rules += [ctrl.Rule(exm['low'] & time['long'] & ene['high'], out['mid'])]
    rules += [ctrl.Rule(exm['low'] & (time['mid'] | time['short']), out['low'])]
    rules += [ctrl.Rule(ene['low'] & (exm['high'] | exm['mid']), out['mid'])]
    rules += [ctrl.Rule(time['short'] & (ene['low'] | exm['low']), out['low'])]
    rules += [ctrl.Rule(ene['low'] & (time['short'] | time['mid']) & exm['low'], out['low'])]
    rules += [ctrl.Rule((ene['low']|ene['mid']|ene['high']) &
                        (exm['low']|exm['mid']|exm['high']) &
                        (time['short']|time['mid']|time['long']), out['low'])]

    system = ctrl.ControlSystem(rules)
    sim = ctrl.ControlSystemSimulation(system)
    sim.input['ene']  = _clip(energy_val, 0, 1)
    sim.input['exm']  = _clip(exam_urgency_val, 0, 1)
    sim.input['time'] = _clip(time_available_val, 0, 5)
    return round(_safe_compute(sim, 'study_reco'), 2)


# ========== 5) Play ==========
def get_play_score(stress_val, energy_val, task_done_val):
    strv = ctrl.Antecedent(np.linspace(0,1,101), 'strv')
    ene  = ctrl.Antecedent(np.linspace(0,1,101), 'ene')
    task = ctrl.Antecedent(np.linspace(0,1,101), 'task')
    out  = ctrl.Consequent(np.linspace(0,10,101), 'play_reco', defuzzify_method='mom')
    _tri_01(strv); _tri_01(ene); _tri_01(task); _out_010(out)

    rules = []
    rules += [ctrl.Rule(strv['high'] & (ene['mid'] | ene['high']) & (task['mid'] | task['high']), out['high'])]
    rules += [ctrl.Rule(strv['high'] & ene['low'], out['mid'])]
    rules += [ctrl.Rule(task['low'] & (strv['mid'] | strv['low']), out['low'])]
    rules += [ctrl.Rule(strv['low'], out['low'])]
    rules += [ctrl.Rule(strv['mid'] & ene['high'] & task['high'], out['mid'])]
    rules += [ctrl.Rule((strv['low']|strv['mid']|strv['high']) &
                        (ene['low']|ene['mid']|ene['high']) &
                        (task['low']|task['mid']|task['high']), out['low'])]

    system = ctrl.ControlSystem(rules)
    sim = ctrl.ControlSystemSimulation(system)
    sim.input['strv'] = _clip(stress_val, 0, 1)
    sim.input['ene']  = _clip(energy_val, 0, 1)
    sim.input['task'] = _clip(task_done_val, 0, 1)
    return round(_safe_compute(sim, 'play_reco', default=4.5), 2)


# ========== 6) Sleep ==========
def get_sleep_score(tiredness_val, time_hour_val, sleep_quality_val, exam_urgency_val,
                    sleep_pressure=0.5, circadian=0.0):
    tired = ctrl.Antecedent(np.linspace(0,1,101), 'tired')
    S     = ctrl.Antecedent(np.linspace(0,1,101), 'S')
    C     = ctrl.Antecedent(np.linspace(-1,1,101), 'C')
    exam  = ctrl.Antecedent(np.linspace(0,1,101), 'exam')
    out  = ctrl.Consequent(np.linspace(0,10,101), 'sleep_reco', defuzzify_method='mom')

    _tri_01(tired); _tri_01(S); _tri_01(exam); _out_010(out)
    C['inhibit'] = fuzz.trapmf(C.universe, [-1.0, -1.0, -0.4, -0.1])
    C['neutral'] = fuzz.trimf(C.universe, [-0.2, 0.0, 0.2])
    C['promote'] = fuzz.trapmf(C.universe, [0.0, 0.3, 1.0, 1.0])

    rules = []
    rules += [ctrl.Rule((S['high'] | tired['high']) & C['promote'] & (exam['low'] | exam['mid']), out['high'])]
    rules += [ctrl.Rule(S['mid'] & C['neutral'] & exam['low'], out['mid'])]
    rules += [ctrl.Rule(exam['high'] & (C['inhibit'] | S['low']), out['low'])]
    rules += [ctrl.Rule((S['mid'] | tired['mid']) & C['promote'] & (exam['low'] | exam['mid']), out['mid'])]
    rules += [ctrl.Rule(exam['high'] & (S['high'] | tired['high']) & C['promote'], out['mid'])]
    rules += [ctrl.Rule(tired['low'] & S['low'] & C['inhibit'], out['low'])]
    rules += [ctrl.Rule((tired['low']|tired['mid']|tired['high']) &
                        (S['low']|S['mid']|S['high']) &
                        (C['inhibit']|C['neutral']|C['promote']) &
                        (exam['low']|exam['mid']|exam['high']), out['low'])]

    system = ctrl.ControlSystem(rules)
    sim = ctrl.ControlSystemSimulation(system)
    sim.input['tired'] = _clip(tiredness_val, 0, 1)
    sim.input['S']     = _clip(sleep_pressure, 0, 1)
    sim.input['C']     = _clip(circadian, -1, 1)
    sim.input['exam']  = _clip(exam_urgency_val, 0, 1)
    return round(_safe_compute(sim, 'sleep_reco', default=4.6), 2)


# ========== 7) Lounge ==========
def get_lounge_score(social_need_val, flatmates_val, time_hour_val,
                     complaints_prev=0, consecutive_lounge=0):
    """Base fuzzy score + penalties for complaints and consecutive lounge streaks."""
    soc  = ctrl.Antecedent(np.linspace(0,1,101), 'soc')
    ppl  = ctrl.Antecedent(np.linspace(0,1,101), 'ppl')  # 0..~3.5 scaled to 0..1
    hour = ctrl.Antecedent(np.arange(0,24,1), 'hour')
    out  = ctrl.Consequent(np.linspace(0,10,101), 'lounge_reco', defuzzify_method='mom')

    _tri_01(soc)
    ppl['few']   = fuzz.trapmf(ppl.universe, [0.0, 0.0, 0.25, 0.40])
    ppl['mid']   = fuzz.trimf(ppl.universe, [0.25, 0.50, 0.75])
    ppl['crowd'] = fuzz.trapmf(ppl.universe, [0.60, 0.80, 1.0, 1.0])
    _time4(hour)
    _out_010(out)

    rules = []
    rules += [ctrl.Rule(soc['high'] & hour['evening'] & (ppl['mid'] | ppl['crowd']), out['high'])]
    rules += [ctrl.Rule(soc['high'] & (hour['evening'] | hour['afternoon']) & ppl['few'], out['mid'])]
    rules += [ctrl.Rule(soc['high'] & ppl['crowd'], out['mid'])]
    rules += [ctrl.Rule(soc['mid'] & hour['evening'] & ppl['mid'], out['mid'])]
    rules += [ctrl.Rule(hour['evening'] & soc['mid'], out['mid'])]
    rules += [ctrl.Rule((hour['morning'] | hour['afternoon']) & ppl['few'] & soc['low'], out['low'])]
    rules += [ctrl.Rule((hour['morning'] | hour['afternoon']) & soc['mid'] & ppl['mid'], out['mid'])]
    rules += [ctrl.Rule(hour['night'] & ppl['few'], out['low'])]
    rules += [ctrl.Rule(soc['low'] & ppl['few'], out['low'])]

    system = ctrl.ControlSystem(rules)
    sim = ctrl.ControlSystemSimulation(system)

    sim.input['soc']  = _clip(social_need_val, 0, 1)
    sim.input['ppl']  = _clip(flatmates_val/3.5, 0, 1)
    sim.input['hour'] = int(_clip(time_hour_val, 0, 23))
    
    base = _safe_compute(sim, 'lounge_reco')

    # Penalties
    cp = int(complaints_prev) if complaints_prev is not None else 0
    penalty = 1.0 - min(0.15 * cp, 0.45)

    cl = int(consecutive_lounge) if consecutive_lounge is not None else 0
    if cl >= 3:
        penalty *= 0.45
    elif cl >= 2:
        penalty *= 0.65

    try:
        fm = float(flatmates_val or 0)
    except Exception:
        fm = 0.0
    penalty *= max(0.50, 1.0 - 0.10 * fm)

    if 19 <= int(time_hour_val) <= 22:
        penalty *= 0.85

    return round(float(base) * float(penalty), 2)


# ========== Aggregation ==========
LABEL_ZH = {'cook':'做饭','shower':'洗澡','clean':'打扫','study':'学习','play':'娱乐','sleep':'睡觉','lounge':'客厅'}

def fuzzy_decision(state, debug=False):
    """
    Returns (best_action, scores_dict)
    - best_action: str
    - scores_dict: e.g., {'cook': 4.95, 'study': 5.00, ...}
    """
    hunger = _clip(state.get('hunger', 0.0), 0, 1)
    fatigue = _clip(state.get('fatigue', 0.0), 0, 1)
    energy = _clip(state.get('energy', max(0.0, 1.0-fatigue)), 0, 1)
    stress = _clip(state.get('stress', 0.0), 0, 1)
    exam_urgency = _clip(state.get('exam_urgency', 0.0), 0, 1)
    sleep_quality = _clip(state.get('sleep_quality', 0.5), 0, 1)
    room_dirty = _clip(state.get('room_dirty', 0.0), 0, 1)
    social_need = _clip(state.get('social_need', 0.0), 0, 1)
    task_done = _clip(state.get('task_done', 0.0), 0, 1)
    time_hour = int(_clip(state.get('time_hour', 0), 0, 23))
    kitchen = float(_clip(state.get('kitchen', 0.0), 0, 3))
    bathroom = float(_clip(state.get('bathroom', 0.0), 0, 3))
    time_available = float(_clip(state.get('time_available', 2.5), 0, 5))
    flatmates = int(_clip(state.get('flatmates', 0), 0, 4))
    complaints_prev = int(_clip(state.get('complaints_prev', 0), 0, 10))
    consecutive_lounge = int(state.get('consecutive_lounge', 0) or 0)
    sleep_pressure = _clip(state.get('sleep_pressure', 0.5), 0, 1)
    circadian = float(_clip(state.get('circadian', 0.0), -1, 1))
    cooldowns = state.get('cooldowns', {})

    scores = {
        'cook':   get_cook_score(hunger, kitchen),
        'shower': get_shower_score(fatigue, time_hour, bathroom),
        'clean':  get_clean_score(room_dirty, energy, complaints_prev),
        'study':  get_study_score(energy, exam_urgency, time_available),
        'play':   get_play_score(stress, energy, task_done),
        'sleep':  get_sleep_score(fatigue, time_hour, sleep_quality, exam_urgency,
                                  sleep_pressure=sleep_pressure, circadian=circadian),
        'lounge': get_lounge_score(social_need, flatmates, time_hour,
                                   complaints_prev=complaints_prev,
                                   consecutive_lounge=consecutive_lounge),
    }

    # Cooldown down-weighting
    for a, left in cooldowns.items():
        if a in scores and left > 0:
            scores[a] *= 0.45

    # Light daily rhythm nudges
    if 7 <= time_hour <= 11:
        scores['study']  += 0.15
    elif 18 <= time_hour <= 22:
        scores['sleep']  += 0.15
    if time_hour >= 22 or time_hour <= 6:
        scores['sleep']  += 0.10

    # Mealtime adjustments
    if time_hour in (11, 12):
        scores['cook'] = max(0.0, scores.get('cook', 0.0) + 0.85)
        scores['study'] = max(0.0, scores.get('study', 0.0) - 0.20)
        scores['play']  = max(0.0, scores.get('play',  0.0) - 0.15)
    elif 18 <= time_hour <= 20:
        scores['cook'] = max(0.0, scores.get('cook', 0.0) + 0.95)
        scores['study'] = max(0.0, scores.get('study', 0.0) - 0.20)
        scores['play']  = max(0.0, scores.get('play',  0.0) - 0.20)

    # Avoid negative
    if scores['cook'] < 0:
        scores['cook'] = 0.0

    # Tie-break
    PRIORITY = ['study', 'cook', 'shower', 'clean', 'lounge', 'play', 'sleep']
    mx = max(scores.values())
    cands = [a for a, s in scores.items() if mx - s <= 0.15]
    if len(cands) > 1:
        cands.sort(key=lambda a: PRIORITY.index(a))
        best = cands[0]
    else:
        best = max(scores, key=scores.get)

    if debug:
        try:
            print("\n🔷 Fuzzy Logic-based Recommendation（模糊逻辑推荐）:")
            for k in ['cook','shower','clean','study','play','sleep','lounge']:
                print(f"{LABEL_ZH.get(k,k):<4} ({k:<7}): {scores[k]:.2f}")
            print(f"\n✅ 最推荐的行为是：{LABEL_ZH.get(best,best)} ({best})（推荐程度：{scores[best]:.2f}）\n")
        except Exception:
            pass

    return best, scores
