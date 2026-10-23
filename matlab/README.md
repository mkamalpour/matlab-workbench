# Native MATLAB workbench

In MATLAB, open this directory and run `workbench`. The four tabs preserve the MATLAB coursework independently of Python. A MATLAB release supporting `uifigure`, `uigridlayout` and `uiconfirm` is required (R2019a or newer intended; not executed here).

Standalone entry points:

```matlab
r = AudioNoiseCancellation(); % synthetic clean/noisy/reference demonstration
r = AudioNoiseCancellation(noisy, reference, fs, clean, struct('plots',false));
r = outlier_detection([1 2 3 4 5 6 7 100]);
[s, message] = transport_system();
[s, message] = transport_system(s, 'ADD-DRIVER ali (0,0) BIKE');
r = mpg_prediction(readtable('my-data.csv'));
```

Audio cancellation needs a reference correlated with the interfering noise. It cannot generally remove arbitrary noise from a single recording. Supply `[]` for unknown clean audio: MSE and SNR remain NaN. The reference and noisy signal must have exactly matching lengths and rates. No silent cropping or resampling occurs. Optional `options` fields are `taps`, `lms_step`, `nlms_step`, `forgetting`, `delta`, and `plots`. Input MAT files contain `noisy`, `reference`, `fs`, and optional `clean`. The WAV export asks before scaling amplitudes above one. Algorithms retain full numerical output in memory. The spectrum is a one-sided FFT periodogram, requiring no Signal Processing Toolbox. Plots open separately so each can be inspected and exported using MATLAB figure tools.

Outlier quartiles use a manual bubble sort and exclude the middle observation for odd-sized samples. NaN values are omitted but reported outlier indices refer to original rows. Infinity is rejected.

Transport accepts integer-coordinate commands:

```
ADD-DRIVER username (x,y) BIKE
CREATE-ORDER BIKE (startx,starty) (finishx,finishy)
RECEIVE-ORDER (startx,starty) (finishx,finishy) username
```

Categories: BIKE, VAN, TRUCK. The assignment's `RECIEVE-ORDER` spelling also works. Available matching drivers are selected by Manhattan distance with username tie breaking. Completion updates driver location. State is returned as a struct; nothing is written automatically. To retain your own state use MATLAB's `save` on an explicit file. Never load an untrusted MAT file. The native transport interface provides command entry and validated snapshot import/export; Python additionally provides guided driver and order forms.

MPG inputs are a table containing `MPG`, `Acceleration`, `Weight`. Missing target rows are omitted. Positive predictors are required; missing predictors are imputed with training-only means. The four features are Acceleration, Weight, InverseAcceleration and InverseWeight. Inverse features are normalized by their training means, then standardized with training sample standard deviations and fitted with an intercept using pseudoinverse OLS. Supply explicit training row indices for cross-language comparisons; MATLAB and NumPy random generators do not produce equivalent splits from the same seed. Default split is 80/20. Use `mpg_predict(model,newTable)` for batch prediction. Returned metadata supports inspection; the Python UI additionally offers direct batch prediction and model downloads.

Native MATLAB execution and GUI rendering were not verified because MATLAB/Octave were unavailable. No proprietary datasets or toolbox dependencies are bundled. This is an educational batch-processing workbench, not a real-time audio device or live transport service.

Run `transport_cli(existingPrivateDirectory)` for an interactive command session and explicit JSON plus three legacy text exports. Existing snapshots are strictly validated before resuming; legacy text files without a snapshot are protected from overwrite. JSON is the authoritative atomic snapshot; legacy text exports can be regenerated and are not jointly transactional. `outages_csv(path)` processes outage CSV timestamps or numeric Duration without redistributing original datasets.


`run_shared_fixtures` checks the same exported MAT/JSON vectors. Native and Python random demo generators differ despite matching amplitudes; use shared MAT inputs for numerical comparisons. MAT audio parameter fields are honored by the dashboard. The implementation stays compact rather than padding code to a line count. Native snapshot JSON import/export is available from the Transport tab; restoration requires explicit confirmation.

