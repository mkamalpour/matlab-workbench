# Numerical Lab

**[Explore the interactive project presentation](docs/overview.html)** — open locally in your browser; works offline.

Four university labs, with the original MATLAB implementations and a Python interface for trying them without MATLAB: remove correlated noise from audio, find outliers, dispatch vehicles, and predict fuel economy.

## Try it first

Open **Audio cancellation**, keep **Synthetic example** and the default NLMS filter, then click **Run audio comparison**. Listen to the output and compare the plots. Each of the other tabs has its own inputs; MATLAB runs separately from the Python interface.

## Run

Activate an existing Python/Conda environment with the requirements already available. Nothing is installed automatically.

```powershell
conda activate base
python -m streamlit run app.py --server.address 127.0.0.1
```

Dependencies are recorded in `requirements.txt`; review them before any optional installation. Heavy workloads and private datasets are not needed to explore the demos. `python workbench.py` is an alternative launcher.

On Windows, `run.bat --check` checks the active environment without opening the app. Run `run.bat` to start, or `run.bat --server.port 8502` if another app is using the default port. The launcher works from any working directory and installs nothing.

## Layout

- `app.py`: small Streamlit entry point.
- `matlab_workbench/`: application logic and interface.
- `tests/`: focused regressions.
- `docs/`: detailed method, formats, comparisons and earlier verification.
- `matlab/` and `fixtures/`: native implementation and small shared synthetic test vectors.

## Lab index

| Lab | Coursework behavior |
|---|---|
| Audio cancellation | LMS, NLMS, and RLS filtering with a correlated noise reference |
| Outlier detection | Manual sorting, split-half quartiles, and IQR fences |
| Transport simulation | Register drivers, assign nearest available vehicles, and save state |
| MPG regression | Four-feature regression with training-only preprocessing and holdout evaluation |

Python entry point: `python workbench.py`. Native entry points and limits: [MATLAB guide](matlab/README.md). Detailed workflows: [method](docs/METHOD.md).

## Verify

```powershell
python -m unittest discover -s tests -v
```

See [method and usage](docs/METHOD.md) for capabilities, original comparisons, privacy rules and material limitations. Tests use synthetic data; native MATLAB execution and large custom datasets are not implied to be verified.

Checked on Windows with Python 3.13.5 (Conda base): **19 tests passed**. Native MATLAB execution remains unverified.

Restored transport coordinates are normalized consistently, and MPG prediction rejects numerical overflow rather than returning nonfinite results.
