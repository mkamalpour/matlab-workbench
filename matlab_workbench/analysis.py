"""Manual IQR statistics and leakage-safe MPG linear regression."""
from dataclasses import dataclass
import io
import numpy as np
import pandas as pd


def bubble_sort(values):
    result = list(values)
    for end in range(len(result) - 1, 0, -1):
        changed = False
        for index in range(end):
            if result[index] > result[index + 1]:
                result[index], result[index + 1] = result[index + 1], result[index]
                changed = True
        if not changed:
            break
    return result


def _middle(values):
    size = len(values)
    return values[size // 2] if size % 2 else values[size // 2 - 1] / 2 + values[size // 2] / 2


def compute_quartiles(values):
    """Tukey-style split halves, excluding the middle observation for odd n."""
    if not values:
        raise ValueError('At least one finite observation is required.')
    if len(values) == 1:
        return values[0], values[0]
    middle = len(values) // 2
    return _middle(values[:middle]), _middle(values[middle + len(values) % 2:])


def outliers(values):
    values = np.asarray(values, dtype=float)
    if values.ndim != 1:
        raise ValueError('Provide a one-dimensional list of observations.')
    if np.isinf(values).any():
        raise ValueError('Infinite observations are invalid; use blank/NaN for missing values.')
    valid = ~np.isnan(values)
    clean = values[valid]
    q1, q3 = compute_quartiles(bubble_sort(clean.tolist()))
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    if not np.isfinite([q1, q3, iqr, lower, upper]).all():
        raise ValueError('Observation magnitudes exceed the supported numerical range.')
    rows = [dict(row_index=index + 1, value=float(value)) for index, value in enumerate(values)
            if not np.isnan(value) and (value < lower or value > upper)]
    return dict(q1=q1, q3=q3, iqr=iqr, lower=lower, upper=upper,
                rows=rows, clean_values=clean, removed_count=int((~valid).sum()))


def durations_from_csv(data):
    try:
        frame = pd.read_csv(io.BytesIO(data))
    except (UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise ValueError('Upload a valid UTF-8 outages CSV.') from error
    if 'Duration' in frame:
        try:
            values = pd.to_numeric(frame.Duration, errors='raise').to_numpy(float)
        except (ValueError, TypeError) as error:
            raise ValueError('Duration must contain numeric hours or blanks.') from error
    elif {'OutageTime', 'RestorationTime'} <= set(frame):
        times = []
        for column in ('OutageTime', 'RestorationTime'):
            raw = frame[column]
            parsed = pd.to_datetime(raw, errors='coerce', format='mixed', utc=True)
            if (raw.notna() & parsed.isna()).any():
                raise ValueError(f'{column} contains an invalid date; use ISO timestamps or blanks.')
            times.append(parsed)
        values = (times[1] - times[0]).dt.total_seconds().to_numpy(float) / 3600
    else:
        raise ValueError('CSV needs Duration in hours, or OutageTime and RestorationTime.')
    if np.isinf(values).any() or (values < 0).any():
        raise ValueError('Outage durations must be finite nonnegative hours or missing.')
    return values


FEATURE_NAMES = ['Acceleration', 'Weight', 'InverseAcceleration', 'InverseWeight']


def _predictors(frame):
    if not {'Acceleration', 'Weight'} <= set(frame):
        raise ValueError('Provide Acceleration and Weight columns.')
    try:
        array = frame[['Acceleration', 'Weight']].apply(pd.to_numeric, errors='raise').to_numpy(float)
    except (TypeError, ValueError) as error:
        raise ValueError('Predictors must contain numbers or blanks.') from error
    if np.isinf(array).any() or (array <= 0).any():
        raise ValueError('Acceleration and Weight must be positive finite values or missing.')
    return array


@dataclass
class MPGModel:
    imputation: np.ndarray
    inverse_means: np.ndarray
    feature_means: np.ndarray
    feature_scales: np.ndarray
    coefficients: np.ndarray

    def _features(self, frame):
        values = _predictors(frame)
        values = np.where(np.isnan(values), self.imputation, values)
        return np.column_stack((values, 1 / values / self.inverse_means))

    def predict(self, frame):
        features = (self._features(frame) - self.feature_means) / self.feature_scales
        return np.column_stack((np.ones(len(features)), features)) @ self.coefficients

    def to_dict(self):
        return dict(version=1, feature_names=FEATURE_NAMES, imputation=self.imputation.tolist(),
                    inverse_means=self.inverse_means.tolist(), feature_means=self.feature_means.tolist(),
                    feature_scales=self.feature_scales.tolist(), coefficients=self.coefficients.tolist())


def train_mpg(frame, train_fraction=0.8, seed=42, train_indices=None):
    if 'MPG' not in frame:
        raise ValueError('Training data needs MPG, Acceleration and Weight columns.')
    if not 0 < train_fraction < 1:
        raise ValueError('Training fraction must lie strictly between zero and one.')
    data = frame.reset_index(drop=True).copy()
    try:
        target = pd.to_numeric(data.MPG, errors='raise').to_numpy(float)
    except (TypeError, ValueError) as error:
        raise ValueError('MPG must contain positive numbers or blanks.') from error
    if np.isinf(target).any() or (target <= 0).any():
        raise ValueError('Observed MPG must be positive and finite.')
    row_ids = np.flatnonzero(~np.isnan(target))
    data = data.iloc[row_ids].reset_index(drop=True)
    y = target[row_ids]
    if len(data) < 8:
        raise ValueError('At least eight rows with observed MPG are required.')
    values = _predictors(data)
    if train_indices is None:
        order = np.random.default_rng(seed).permutation(len(data))
        count = int(np.floor(len(data) * train_fraction + 0.5))
        train, test = order[:count], order[count:]
    else:
        requested = np.asarray(train_indices)
        if requested.ndim != 1 or not np.issubdtype(requested.dtype, np.integer):
            raise ValueError('Explicit training indices must be one-based integer original row indices.')
        if len(set(requested.tolist())) != len(requested) or not set(requested) <= set(row_ids + 1):
            raise ValueError('Training indices must be unique observed-MPG row indices.')
        lookup = {original + 1: offset for offset, original in enumerate(row_ids)}
        train = np.array([lookup[number] for number in requested], dtype=int)
        test = np.array([index for index in range(len(data)) if index not in set(train)], dtype=int)
    if len(train) < 5 or len(test) < 1:
        raise ValueError('Use at least five training rows and one test row.')
    for column in range(2):
        if np.isnan(values[train, column]).all():
            raise ValueError('Every predictor needs at least one observed training value.')
    imputation = np.nanmean(values[train], axis=0)
    filled = np.where(np.isnan(values), imputation, values)
    inverse_means = np.mean(1 / filled[train], axis=0)
    features = np.column_stack((filled, 1 / filled / inverse_means))
    if not np.isfinite(features).all():
        raise ValueError('Predictor magnitudes exceed the supported numerical range.')
    means = features[train].mean(axis=0)
    scales = features[train].std(axis=0, ddof=1)
    scales[scales == 0] = 1
    design = np.column_stack((np.ones(len(train)), (features[train] - means) / scales))
    coefficients = np.linalg.lstsq(design, y[train], rcond=None)[0]
    model = MPGModel(imputation, inverse_means, means, scales, coefficients)
    predictions = model.predict(data.iloc[test])
    residual = y[test] - predictions
    denominator = np.sum((y[test] - np.mean(y[test])) ** 2)
    r2 = float(1 - np.sum(residual ** 2) / denominator) if denominator > 0 else None
    report = pd.DataFrame(dict(row_index=row_ids[test] + 1, actual=y[test], predicted=predictions, residual=residual))
    return dict(model=model, metrics=dict(rmse=float(np.sqrt(np.mean(residual ** 2))), mae=float(np.mean(abs(residual))),
                                         r2=r2, train_count=len(train), test_count=len(test)), report=report,
                split=dict(train=(row_ids[train] + 1).tolist(), test=(row_ids[test] + 1).tolist()), feature_names=FEATURE_NAMES)


def demo_mpg():
    rng = np.random.default_rng(8)
    acceleration = rng.uniform(8, 23, 60)
    weight = rng.uniform(1700, 4800, 60)
    mpg = 48 - weight * .006 - acceleration * .25 + rng.normal(0, .8, 60)
    return pd.DataFrame(dict(MPG=mpg, Acceleration=acceleration, Weight=weight))
