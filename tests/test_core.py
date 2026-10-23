import copy
import io
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from scipy.io import loadmat

from matlab_workbench import analysis
from matlab_workbench import audio
from matlab_workbench.transport import TransportSystem


class StatisticsTests(unittest.TestCase):
    def test_manual_quartiles_and_original_indices(self):
        result = analysis.outliers([np.nan, 1, 2, 3, 4, 5, 6, 7, 100])
        self.assertEqual(result['q1'], 2.5)
        self.assertEqual(result['q3'], 6.5)
        self.assertEqual(result['rows'], [dict(row_index=9, value=100.)])
        self.assertEqual(result['removed_count'], 1)
        self.assertEqual(analysis.outliers([7])['q1'], 7)
        self.assertEqual(analysis.outliers([1, 2, 3, 4, 100])['q3'], 52)

    def test_duration_inputs(self):
        values = analysis.durations_from_csv(b'OutageTime,RestorationTime\n2002-02-01 12:00,2002-02-01 16:30\n2002-02-01,\n')
        self.assertEqual(values[0], 4.5)
        self.assertTrue(np.isnan(values[1]))
        for data in [b'Duration\n-1', b'Duration\ninf', b'OutageTime,RestorationTime\ninvalid,date', b'Other\n1']:
            with self.assertRaises(ValueError):
                analysis.durations_from_csv(data)

    def test_invalid_statistics(self):
        for values in ([], [np.nan], [np.inf], [[1, 2]]):
            with self.assertRaises(ValueError):
                analysis.outliers(values)


class MPGTests(unittest.TestCase):
    def test_train_only_imputation_and_deterministic_split(self):
        data = analysis.demo_mpg().iloc[:10].copy()
        data.loc[0, 'Acceleration'] = np.nan
        data.loc[7:, 'Acceleration'] = 1000
        result = analysis.train_mpg(data, train_indices=[1, 2, 3, 4, 5, 6, 7])
        self.assertAlmostEqual(result['model'].imputation[0], data.loc[1:6, 'Acceleration'].mean())
        self.assertEqual(result['split']['test'], [8, 9, 10])
        a, b = analysis.train_mpg(data), analysis.train_mpg(data)
        self.assertEqual(a['split'], b['split'])
        np.testing.assert_allclose(a['report'].predicted, b['report'].predicted)

    def test_missing_target_preserves_original_rows(self):
        data = analysis.demo_mpg().iloc[:12].copy()
        data.loc[1, 'MPG'] = np.nan
        result = analysis.train_mpg(data, train_indices=[1, 3, 4, 5, 6, 7, 8])
        self.assertEqual(result['split']['test'], [9, 10, 11, 12])
        self.assertEqual(result['report'].row_index.tolist(), [9, 10, 11, 12])
        self.assertEqual(len(result['model'].coefficients), 5)

    def test_regression_recovers_exact_linear_target(self):
        frame = analysis.demo_mpg()
        frame.MPG = 50 - .005 * frame.Weight - .4 * frame.Acceleration
        result = analysis.train_mpg(frame)
        self.assertLess(result['metrics']['rmse'], 1e-10)
        self.assertAlmostEqual(result['metrics']['r2'], 1)
        json.dumps(result['model'].to_dict(), allow_nan=False)

    def test_invalid_predictors_and_splits(self):
        frame = analysis.demo_mpg()
        for invalid in (0, -1, float('inf')):
            candidate = frame.copy()
            candidate.loc[0, 'Weight'] = invalid
            with self.assertRaises(ValueError):
                analysis.train_mpg(candidate)
        for split in ([1, 1, 2], [0, 1, 2], [1., 2., 3.]):
            with self.assertRaises(ValueError):
                analysis.train_mpg(frame, train_indices=split)


class AudioTests(unittest.TestCase):
    def test_cancellation_and_true_input_snr(self):
        data = audio.synthetic_audio(duration=.4)
        self.assertAlmostEqual(audio.snr_db(data['clean'], data['noisy']), 5)
        result = audio.compare_filters(data['noisy'], data['reference'], data['fs'], data['clean'])
        for metric in result['metrics']:
            self.assertGreater(metric['snr_gain_db'], 2)
            self.assertGreaterEqual(metric['mse'], 0)

    def test_filter_is_causal_and_zero_reference_preserves_input(self):
        noisy = np.array([.2, .3, -.1, .4, .5])
        reference = np.array([.1, -.1, .3, .2, .1])
        for algorithm in ('LMS', 'NLMS', 'RLS'):
            first = audio.adaptive_filter(noisy, reference, algorithm, taps=2)
            changed = audio.adaptive_filter(np.r_[noisy[:3], 9, 8], reference, algorithm, taps=2)
            np.testing.assert_array_equal(first['cleaned'][:3], changed['cleaned'][:3])
            np.testing.assert_array_equal(audio.adaptive_filter(noisy, np.zeros(5), algorithm, taps=2)['cleaned'], noisy)

    def test_unknown_clean_never_fabricates_quality(self):
        data = audio.synthetic_audio(duration=.05)
        result = audio.compare_filters(data['noisy'], data['reference'], data['fs'], algorithms=('NLMS',))
        self.assertIsNone(result['input_snr_db'])
        self.assertIsNone(result['metrics'][0]['snr_gain_db'])

    def test_wav_roundtrip_and_validation(self):
        values = np.array([-.2, .4, 1.2])
        decoded, fs = audio.read_wav(audio.wav_bytes(values, 8000))
        np.testing.assert_allclose(decoded, values, atol=1e-7)
        self.assertEqual(fs, 8000)
        for options in [dict(taps=0), dict(step=2), dict(forgetting=0), dict(delta=0)]:
            with self.assertRaises(ValueError):
                audio.adaptive_filter(np.ones(8), np.ones(8), **options)
        with self.assertRaises(ValueError):
            audio.read_wav(b'not wav')
        with self.assertRaises(ValueError):
            audio.simulate_noise(np.zeros(20), 8000)


class TransportTests(unittest.TestCase):
    def test_nearest_available_driver_and_completion(self):
        system = TransportSystem()
        system.execute('ADD-DRIVER z (1,0) BIKE')
        system.execute('ADD-DRIVER a (-1,0) BIKE')
        first = system.execute('CREATE-ORDER BIKE (0,0) (5,6)')['order']
        self.assertEqual(first['username'], 'a')
        self.assertEqual(system.execute('CREATE-ORDER BIKE (0,0) (3,4)')['order']['username'], 'z')
        system.execute('RECIEVE-ORDER (0,0) (5,6) a')
        self.assertEqual((system.drivers['a']['x'], system.drivers['a']['y']), (5, 6))
        self.assertEqual(len(system.completed), 1)
        self.assertEqual(TransportSystem.from_snapshot(system.snapshot()).snapshot(), system.snapshot())
        self.assertIn('BIKE (0,0) (5,6) a', system.export_text_files()['order.txt'])

    def test_invalid_commands_are_atomic(self):
        system = TransportSystem()
        system.execute('ADD-DRIVER kamal (1, 2) VAN')
        before = system.snapshot()
        for command in ['ADD-DRIVER kamal (0,0) VAN', 'ADD-DRIVER x (1+2,0) BIKE', 'CREATE-ORDER CAR (0,0) (1,1)', 'RECEIVE-ORDER (0,0) (1,1) kamal', 'CREATE-ORDER VAN (99999999999,0) (1,1)']:
            with self.assertRaises(ValueError):
                system.execute(command)
            self.assertEqual(system.snapshot(), before)

    def test_snapshot_relationships_and_detachment(self):
        system = TransportSystem()
        system.execute('ADD-DRIVER a (0,0) TRUCK')
        system.execute('CREATE-ORDER TRUCK (0,0) (2,2)')
        snapshot = system.snapshot()
        detached = copy.deepcopy(snapshot)
        detached['active'].append(dict(detached['active'][0], order_id=2))
        detached['next_order_id'] = 3
        with self.assertRaises(ValueError):
            TransportSystem.from_snapshot(detached)
        detached = copy.deepcopy(snapshot)
        detached['active'][0]['username'] = 'unknown'
        with self.assertRaises(ValueError):
            TransportSystem.from_snapshot(detached)
        snapshot['drivers'][0]['x'] = 999
        self.assertEqual(system.drivers['a']['x'], 0)


class SharedFixtures(unittest.TestCase):
    def test_expected_cross_language_vectors(self):
        root = Path(__file__).resolve().parents[1] / 'fixtures'
        if not (root / 'shared.json').exists():
            self.skipTest('Fixtures not generated yet.')
        fixture = json.loads((root / 'shared.json').read_text())
        result = analysis.outliers([np.nan if x is None else x for x in fixture['outliers']['values']])
        self.assertEqual(result['rows'], fixture['outliers']['expected']['rows'])
        for key in ('q1', 'q3', 'iqr', 'lower', 'upper'):
            self.assertAlmostEqual(result[key], fixture['outliers']['expected'][key])
        state = TransportSystem()
        for command in fixture['transport']['commands']:
            state.execute(command)
        self.assertEqual(state.snapshot(), fixture['transport']['expected'])
        data = loadmat(root / 'audio.mat', squeeze_me=True)
        for algorithm in ('LMS', 'NLMS', 'RLS'):
            result = audio.adaptive_filter(data['noisy'], data['reference'], algorithm, taps=4, step=.01 if algorithm == 'LMS' else .2)
            np.testing.assert_allclose(result['cleaned'], data['cleaned_' + algorithm], atol=1e-10)
        result = analysis.train_mpg(pd.read_csv(root / 'mpg.csv'), train_indices=fixture['mpg']['train_indices'])
        np.testing.assert_allclose(result['report'].predicted, fixture['mpg']['expected_predictions'], atol=1e-9)


if __name__ == '__main__':
    unittest.main()
