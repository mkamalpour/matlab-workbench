# Verification and original comparison

The original MATLAB project and assignments remain untouched. Native MATLAB entry points and a Python interface cover all four tasks.

- Outliers: manual sorting and split-half quartiles retained; original row IDs now survive missing-value removal.
- Transport: safe numeric parsing replaces expression evaluation; nearest available matching driver, completion, validated snapshots and assignment text exports are available.
- MPG: four predictors retained; imputation and feature normalization fit training rows only, avoiding leakage. Explicit original row IDs allow equal-split comparisons.
- Audio: the original LMS interface is extended with NLMS and RLS, known-target metrics, signal/spectrum/error plots, playback and exports. Unknown clean targets never produce invented quality metrics.

Python tests exercise algorithms, validation, causal filtering, state transitions, fixtures and actual Streamlit actions. The 0.4-second synthetic audio test at input 5 dB produced output SNR approximately LMS 7.76, NLMS 9.18 and RLS 12.89 dB; these are synthetic-example measurements, not general recovery guarantees.

MATLAB/Octave were unavailable. Native execution, rendering and cross-language numerical equality remain unverified; shared fixtures and MATLAB checks are provided for that purpose. Python fixture agreement alone is not MATLAB validation. No original datasets, videos, reports or personal state are published.
