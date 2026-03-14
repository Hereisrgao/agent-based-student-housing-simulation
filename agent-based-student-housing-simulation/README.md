# Shared Student Housing — Agent-Based Simulation

*A minimal, reproducible package for the dissertation.*

---

## 1) Requirements

* **Python** 3.9–3.12 (Windows/macOS/Linux)
* Packages: `numpy`, `pandas`, `matplotlib`, `scikit-fuzzy`

---

## 2) Project Location (absolute paths used below)

* **Windows example path:** `C:\Users\YourName\SharedHousingSim\`
* **macOS/Linux example path:** `/Users/yourname/SharedHousingSim/`

Replace with your actual path if different.

---

## 3) Environment Setup

### Windows (PowerShell)

```powershell
# create & activate venv
python -m venv C:\Users\YourName\SharedHousingSim\venv
C:\Users\YourName\SharedHousingSim\venv\Scripts\Activate.ps1

# install deps
C:\Users\YourName\SharedHousingSim\venv\Scripts\python.exe -m pip install --upgrade pip
C:\Users\YourName\SharedHousingSim\venv\Scripts\python.exe -m pip install numpy pandas matplotlib scikit-fuzzy
```

### macOS / Linux

```bash
python3 -m venv /Users/yourname/SharedHousingSim/venv
source /Users/yourname/SharedHousingSim/venv/bin/activate

/Users/yourname/SharedHousingSim/venv/bin/python -m pip install --upgrade pip
/Users/yourname/SharedHousingSim/venv/bin/python -m pip install numpy pandas matplotlib scikit-fuzzy
```

---

## 4) How to Run (absolute-path commands)

### 4.1 Fuzzy-only (baseline, 24h)

**Windows**

```powershell
C:\Users\YourName\SharedHousingSim\venv\Scripts\python.exe `
  C:\Users\YourName\SharedHousingSim\run_simulation.py `
  fuzzy_only `
  --hours 24 `
  --seed 42 `
  --scenario baseline `
  --kitchen-cap 2 `
  --bathroom-cap 1 `
  --debug
```

**macOS/Linux**

```bash
/Users/yourname/SharedHousingSim/venv/bin/python \
  /Users/yourname/SharedHousingSim/run_simulation.py \
  fuzzy_only \
  --hours 24 \
  --seed 42 \
  --scenario baseline \
  --kitchen-cap 2 \
  --bathroom-cap 1 \
  --debug
```

### 4.2 Utility-only (exam moderate, 24h)

```powershell
C:\Users\YourName\SharedHousingSim\venv\Scripts\python.exe `
  C:\Users\YourName\SharedHousingSim\run_simulation.py `
  utility_only `
  --hours 24 `
  --seed 42 `
  --scenario exam_moderate `
  --kitchen-cap 2 `
  --bathroom-cap 1
```

### 4.3 Hybrid (exam strong, 24h)

```powershell
C:\Users\YourName\SharedHousingSim\venv\Scripts\python.exe `
  C:\Users\YourName\SharedHousingSim\run_simulation.py `
  hybrid `
  --hours 24 `
  --seed 42 `
  --scenario exam_strong `
  --kitchen-cap 2 `
  --bathroom-cap 1
```

### 4.4 “Disturbance” condition (capacity-reduced)

> There is **no** `--scenario disturbance`. Disturbance is created by **lowering capacities**.

```powershell
C:\Users\YourName\SharedHousingSim\venv\Scripts\python.exe `
  C:\Users\YourName\SharedHousingSim\run_simulation.py `
  hybrid `
  --hours 24 `
  --seed 42 `
  --scenario baseline `
  --kitchen-cap 1 `
  --bathroom-cap 1
```

---

## 5) Output Files

Each run produces:

* Per-seed results (hourly behaviors):
  `C:\Users\YourName\SharedHousingSim\logs\seed_42\results_seed42.csv`
* Timestamped master log (in the chosen `--logs` dir or default):
  `behavior_log_{EXPERIMENT}_{SCENARIO}_{YYYYMMDD_HHMMSS}.csv`
  Example: `behavior_log_hybrid_baseline_20250912_142310.csv`

Change base directory with:

```powershell
--logs C:\Users\YourName\SharedHousingSim\results
```

---

## 6) File Map

* `run_simulation.py` — entry point; runs experiments and writes CSVs
* `environment.py` — shared-house environment & hourly loop
* `agents.py` — agent state, decision calls, updates
* `Fuzzy.py` — fuzzy scorers + aggregator
* `utility.py` — utility scorer + ε-greedy/softmax sampler
* `RuleBased.py` — rule/threshold baseline

---

## 7) Notes

* `--scenario` accepts: `baseline`, `exam_moderate`, `exam_strong`
* Disturbance is **operationalised** via `--kitchen-cap` / `--bathroom-cap`
* Runs longer than 24h automatically enable long-horizon nudges

---

## 8) Troubleshooting

* `ModuleNotFoundError: skfuzzy`

  ```powershell
  C:\Users\YourName\SharedHousingSim\venv\Scripts\python.exe -m pip install scikit-fuzzy
  ```
* No CSVs saved → ensure the `logs/` path exists or set a writable absolute `--logs` path
* Version conflicts → recreate venv and reinstall packages

---

## 9) Citation

If referenced, cite as:
**Shared Student Housing — Agent-Based Simulation (code archive), version YYYY-MM-DD.**
