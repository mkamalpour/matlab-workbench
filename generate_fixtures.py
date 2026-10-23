"""Regenerate synthetic cross-language vectors; no user data is accessed."""
import json
from pathlib import Path
import numpy as np
from scipy.io import savemat
import analysis
import audio
from transport import TransportSystem


def main():
    root = Path(__file__).parent / 'fixtures'
    root.mkdir(exist_ok=True)
    values = [None, 1, 2, 3, 4, 5, 6, 7, 100]
    report = analysis.outliers([np.nan if value is None else value for value in values])
    expected = {key: report[key] for key in ['q1', 'q3', 'iqr', 'lower', 'upper', 'rows']}
    commands = ['ADD-DRIVER z (1,0) BIKE', 'ADD-DRIVER a (-1,0) BIKE', 'CREATE-ORDER BIKE (0,0) (5,6)',
                'CREATE-ORDER BIKE (0,0) (3,4)', 'RECIEVE-ORDER (0,0) (5,6) a']
    system = TransportSystem()
    for command in commands:
        system.execute(command)
    # Analytic, deterministic vectors avoid RNG differences between MATLAB and NumPy.
    time = np.arange(64) / 8000
    reference = .1 * np.sin(np.arange(64) * 1.7) + .03 * np.cos(np.arange(64) * .9)
    clean = .2 * np.sin(2 * np.pi * 440 * time)
    noise = np.convolve(reference, [.8, .3, -.2])[:64]
    data = dict(noisy=clean + noise, reference=reference, clean=clean, fs=8000)
    for name in ['LMS', 'NLMS', 'RLS']:
        result = audio.adaptive_filter(data['noisy'], reference, name, taps=4, step=.01 if name == 'LMS' else .2)
        data['cleaned_' + name], data['weights_' + name] = result['cleaned'], result['weights']
    savemat(root / 'audio.mat', data, oned_as='column')
    frame = analysis.demo_mpg().iloc[:16].copy()
    frame.loc[1, 'MPG'] = np.nan
    frame.loc[3, 'Acceleration'] = np.nan
    frame.loc[11, 'Weight'] = np.nan
    frame.to_csv(root / 'mpg.csv', index=False)
    training = [1, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    model = analysis.train_mpg(frame, train_indices=training)
    fixture = dict(outliers=dict(values=values, expected=expected), transport=dict(commands=commands, expected=system.snapshot()),
                   mpg=dict(train_indices=training, expected_predictions=model['report'].predicted.tolist(),
                            expected_test_indices=model['split']['test'], model=model['model'].to_dict()))
    (root / 'shared.json').write_text(json.dumps(fixture, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print('Synthetic MATLAB/Python fixtures written; MATLAB execution is a separate check.')


if __name__ == '__main__':
    main()
