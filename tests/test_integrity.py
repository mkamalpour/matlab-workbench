import unittest
import numpy as np
import pandas as pd

from matlab_workbench.analysis import demo_mpg, train_mpg
from matlab_workbench.transport import TransportSystem


class IntegrityTests(unittest.TestCase):
    def test_tuple_snapshot_coordinates_can_complete_order(self):
        system = TransportSystem()
        system.execute('ADD-DRIVER alex (0,0) BIKE')
        system.execute('CREATE-ORDER BIKE (0,0) (3,4)')
        snapshot = system.snapshot()
        snapshot['active'][0]['start'] = (0, 0)
        snapshot['active'][0]['finish'] = (3, 4)
        restored = TransportSystem.from_snapshot(snapshot)
        restored.execute('RECEIVE-ORDER (0,0) (3,4) alex')
        self.assertEqual(restored.drivers['alex']['x'], 3)
        self.assertEqual(len(restored.completed), 1)
        self.assertEqual(snapshot['active'][0]['start'], (0, 0))

    def test_prediction_rejects_reciprocal_overflow(self):
        model = train_mpg(demo_mpg())['model']
        with self.assertRaisesRegex(ValueError, 'numerical range'):
            model.predict(pd.DataFrame({'Acceleration': [np.nextafter(0., 1.)], 'Weight': [2000.]}))
        self.assertTrue(np.isfinite(model.predict(demo_mpg())).all())

    def test_prediction_rejects_standardization_overflow(self):
        model = train_mpg(demo_mpg())['model']
        model.feature_scales[:] = np.nextafter(0., 1.)
        with self.assertRaisesRegex(ValueError, 'numerical range'):
            model.predict(demo_mpg())
