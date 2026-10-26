import numpy as np
import pytest
from matlab_workbench.analysis import demo_mpg, train_mpg


def test_baseline_uses_only_training_targets_on_identical_holdout():
    data = demo_mpg()
    result = train_mpg(data, train_indices=list(range(1, 41)))
    report = result['report']
    mean = data.MPG.iloc[:40].mean()
    np.testing.assert_allclose(report.baseline_prediction, mean)
    expected = np.sqrt(np.mean((report.actual - mean) ** 2))
    assert result['metrics']['baseline_rmse'] == pytest.approx(expected)
    assert result['metrics']['rmse_skill'] > 0
    data.loc[40:, 'MPG'] *= 10
    changed = train_mpg(data, train_indices=list(range(1, 41)))
    np.testing.assert_allclose(changed['report'].baseline_prediction, mean)
