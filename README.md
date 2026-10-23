# Matlab Workbench

Four numerical labs with a Python interface and separate native MATLAB implementations. Educational software; see the verification limits below.

## Run

Activate an existing Python/Conda environment with the requirements already available. Nothing is installed automatically.

```powershell
conda activate base
python -m streamlit run app.py --server.address 127.0.0.1
```

Dependencies are recorded in `requirements.txt`; review them before any optional installation. Heavy workloads and private datasets are not needed to explore the demos. `python workbench.py` is an alternative launcher.

## Layout

- `app.py`: small Streamlit entry point.
- `matlab_workbench/`: application logic and interface.
- `tests/`: focused regressions.
- `docs/`: detailed method, formats, comparisons and earlier verification.
- `matlab/` and `fixtures/`: native implementation and small shared synthetic test vectors.

## Verify

```powershell
python -m unittest discover -s tests -v
```

See [method and usage](docs/METHOD.md) for capabilities, original comparisons, privacy rules and material limitations. Tests use synthetic data; native MATLAB, full-size datasets and optional external models are not implied to be verified. No license has been selected.

Current lightweight check (Windows, existing Conda base / Python 3.13.5): **16 passed**. No dependency installs, model downloads, live publishing, or heavy datasets were used. Native MATLAB execution remains unverified.
