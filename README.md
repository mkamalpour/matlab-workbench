# MATLAB Workbench

Four university experiments, with **independent MATLAB implementations** and a Python browser interface. MATLAB remains the coursework version; Python makes data loading, parameter exploration, playback, plots and downloads easier. No MATLAB Engine, paid service or external AI is needed for Python.

## Python setup

Verified environment: Windows, Python **3.13.5**. From this directory:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python workbench.py
```

Open the localhost address printed in the terminal. Stop the app with Ctrl+C. The server binds to `127.0.0.1`. On other operating systems use `.venv/bin/python`; those platforms are not verified. `requirements.txt` pins the direct dependencies; `requirements-lock.txt` records the complete verified environment.

## MATLAB setup

From MATLAB, change to this repository's directory:

```matlab
addpath('matlab');
workbench;             % Native four-tab dashboard
smoke_test;            % Native algorithm smoke checks
run_shared_fixtures;   % Compare shared vectors with Python reference outputs
```

MATLAB and Octave were unavailable during development. Native code is provided and inspected, but **MATLAB execution and cross-language numerical parity are unverified**. The UI uses modern MATLAB desktop components. See [matlab/README.md](matlab/README.md) for individual entry points, requirements and native-interface limitations. Algorithms do not rely on a prepared indexing, statistics or adaptive-filter package.

## Workspaces

| Workspace | Behavior | Your inputs |
|---|---|---|
| Audio cancellation | LMS, NLMS, RLS; waveform/PSD/error plots; runtime and known-target SNR/MSE; playback and WAV/MAT/report downloads | Synthetic demo, clean WAV plus simulated noise, or noisy WAV plus noise-reference WAV |
| Outlier detection | Manual bubble sort, split-half quartiles, IQR fences and original row indices | Pasted hours or outages CSV |
| Transport | Driver registration, nearest available category match, completion/location updates, snapshots and assignment text exports | Forms or assignment commands; optional JSON restore |
| MPG prediction | Held-out linear regression with four features, training-only imputation/normalization, residuals and batch prediction | Synthetic example, CSV, or numeric MATLAB MAT arrays |

The Overview tab explains where to start. Run actions are explicit. Input/configuration changes hide outdated audio and MPG results. Invalid operations preserve previously valid state. Transport is an educational simulation; it performs no real dispatch or transaction. Sessions are in memory: download results/snapshots before closing the app or server. Unsaved session data is not automatically written to disk.

### Audio

Adaptive cancellation needs a reference channel **correlated with the interfering noise**, not another copy of the speech. A single noisy recording alone is insufficient. Clean audio is used only for evaluation; it never trains the adaptive filter. When the clean target is unknown, SNR and reconstruction MSE are unavailable rather than guessed.

Signals must have the same sample rate and length. Stereo WAV is averaged to mono. No resampling or silent cropping occurs. Python accepts PCM/floating-point WAV and exports float WAV without amplitude normalization; playback may clip when peaks exceed one, which the UI reports. MATLAB WAV export asks before scaling. Python's upload-processing bound is 160,000 samples per clip and UI filter length is at most 128 taps. Long clips must be explicitly shortened outside the app. Computation is batch processing, not live microphone cancellation; use Streamlit Stop to interrupt a run.

The synthetic noise is a causal FIR transform `[0.8,0.3,-0.2]` of the reference. Defaults: LMS step 0.01, NLMS step 0.2, RLS forgetting 0.995, delta 1, and 16 taps. All filters estimate noise before updating their weights. `SNR = 10 log10(mean(clean^2)/mean((clean-estimate)^2))`. Learning plots show reconstruction error only when a clean target exists. Filter stability and recovery depend on reference quality, amplitude, filter length and parameters; no universal improvement is promised.

The MAT download carries the same input arrays and parameter settings for native comparison. MATLAB and NumPy seeded random generators differ; use this file or the shared fixtures for equal-input comparisons.

### Outliers

CSV accepts numeric `Duration` hours, or `OutageTime,RestorationTime` timestamps. Missing durations are omitted; original one-based data-row indices are retained (the header is not counted). Invalid timestamps, negative durations and infinity are rejected. Generic pasted observations may be negative. Quartiles are medians of the lower and upper halves; for odd sample counts the middle value is excluded. Singleton quartiles equal that observation. Fences are `Q1 - 1.5*IQR` and `Q3 + 1.5*IQR`; only strictly outside values are outliers. Manual sorting is intentionally quadratic for coursework; the Python UI caps analysis at 20,000 observations.

### Transport

```text
ADD-DRIVER kamal (0,0) BIKE
CREATE-ORDER BIKE (1,1) (4,5)
RECEIVE-ORDER (1,1) (4,5) kamal
Exit
```

Categories: BIKE, VAN, TRUCK. The original `RECIEVE-ORDER` typo is accepted as an alias. Coordinates are signed integers. A matching available driver is selected by Manhattan distance; equal-distance ties resolve by username. A driver cannot have two active orders. Completion must match driver/start/destination, then moves the order to history and updates the driver's position. Failed commands make no changes.

Python snapshots are strictly validated before replacing simulator state. JSON is the complete interchange format, retaining IDs and history; the ZIP contains `driver.txt`, `new_order.txt`, `order.txt` in the assignment format. Native `transport_cli(directory)` explicitly saves/resumes a validated snapshot in your chosen directory and exports the three text files. These text views are derived from an authoritative atomic JSON snapshot; the three exports are not a jointly atomic transaction.

### MPG

CSV/MAT columns: `MPG`, `Acceleration`, `Weight`. MAT arrays must be numeric vectors of equal lengths. If MATLAB's `carbig` example is installed, export without bundling it into the repository:

```matlab
load carbig;
save('my-carbig.mat','MPG','Acceleration','Weight');
```

Only rows missing MPG are dropped. Other missing values use training-column means. Observed MPG and predictors must be positive and finite. The features are Acceleration, Weight, inverse Acceleration divided by its training inverse mean, and inverse Weight divided by its training inverse mean. All four are standardized using training means and sample standard deviations; zero scales become one. An intercept and ordinary least squares fit the target. Python uses `lstsq`; MATLAB uses a pseudoinverse. Constant-target test R2 is undefined, not claimed to be a meaningful score.

The same integer seed does not imply the same MATLAB/NumPy split. Export and reuse explicit **original one-based training row IDs** for comparison. At least eight observed-target rows, five training rows and one held-out row are required. Synthetic results demonstrate the pipeline, not real-world model quality.

## Verification

```powershell
.venv\Scripts\python -m unittest discover -v
.venv\Scripts\python -m pip check
```

[COMPARISON.md](COMPARISON.md) records original behavior, confirmed fixes and measured results. [fixtures/](fixtures/) contains only small original synthetic vectors, not coursework datasets. `generate_fixtures.py` regenerates Python reference outputs; this is not a substitute for running MATLAB's checker.

## Structure and publication boundaries

- `matlab/`: native dashboard, four algorithms, helpers and MATLAB checks.
- `app.py`, `.streamlit/`: Python interface/theme.
- `audio.py`, `analysis.py`, `transport.py`: independent Python logic.
- `test_*.py`: numerical, validation and interface checks.
- `workbench.py`: localhost launcher.
- `fixtures/`, `generate_fixtures.py`: cross-language inputs/reference outputs.

Original project/assignment folders remain untouched beside this repository. Lecture videos, slide PDFs, reports, archives, original datasets and private/generated state are excluded. No license has been added or replaced. This is educational software; native execution, cross-platform behavior, arbitrary audio recovery and production suitability are not claimed as verified.
