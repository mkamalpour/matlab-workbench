"""Causal adaptive noise cancellation. Clean targets are used only for evaluation."""
import io
from time import perf_counter
import numpy as np
from scipy.io import wavfile
from scipy.signal import lfilter


def _signal(values, name):
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or not len(array) or not np.isfinite(array).all():
        raise ValueError(f'{name} must be a nonempty finite mono signal.')
    return array


def read_wav(data):
    try:
        fs, samples = wavfile.read(io.BytesIO(data))
    except (ValueError, OSError, EOFError) as error:
        raise ValueError('Upload an uncompressed PCM or floating-point WAV file.') from error
    if samples.dtype.kind == 'u':
        midpoint = 2 ** (samples.dtype.itemsize * 8 - 1)
        values = (samples.astype(float) - midpoint) / midpoint
    elif samples.dtype.kind == 'i':
        values = samples.astype(float) / (2 ** (samples.dtype.itemsize * 8 - 1))
    elif samples.dtype.kind == 'f':
        values = samples.astype(float)
    else:
        raise ValueError('Unsupported WAV sample encoding.')
    if values.ndim == 2:
        values = values.mean(axis=1)
    if not isinstance(fs, int) or fs <= 0:
        raise ValueError('WAV sample rate must be positive.')
    return _signal(values, 'WAV audio'), fs


def wav_bytes(signal, fs):
    values = _signal(signal, 'Output audio')
    if not isinstance(fs, (int, np.integer)) or fs <= 0:
        raise ValueError('Sample rate must be a positive integer.')
    buffer = io.BytesIO()
    wavfile.write(buffer, int(fs), values.astype(np.float32))
    return buffer.getvalue()


def simulate_noise(clean, fs, snr_db=5, seed=42):
    clean = _signal(clean, 'Clean audio')
    if not np.isfinite(snr_db) or not -40 <= snr_db <= 80:
        raise ValueError('Target SNR must be between -40 and 80 dB.')
    if not isinstance(fs, (int, np.integer)) or fs <= 0:
        raise ValueError('Sample rate must be a positive integer.')
    power = np.mean(clean ** 2)
    if power <= 0:
        raise ValueError('A silent clean signal cannot define an SNR.')
    reference = np.random.default_rng(seed).normal(size=len(clean))
    noise = lfilter([.8, .3, -.2], [1], reference)
    scale = np.sqrt(power / (np.mean(noise ** 2) * 10 ** (snr_db / 10)))
    reference *= scale
    return dict(clean=clean.copy(), noisy=clean + noise * scale, reference=reference, fs=int(fs))


def synthetic_audio(fs=8000, duration=1., snr_db=5., seed=42):
    if not isinstance(fs, (int, np.integer)) or fs < 2000 or not np.isfinite(duration) or not 0 < duration <= 30:
        raise ValueError('Use a sample rate of at least 2000 Hz and duration in (0,30] seconds.')
    t = np.arange(int(round(fs * duration))) / fs
    clean = .3 * np.sin(2 * np.pi * 440 * t) + .15 * np.sin(2 * np.pi * 880 * t)
    return simulate_noise(clean, fs, snr_db, seed)


def snr_db(clean, estimate):
    clean, estimate = _signal(clean, 'Clean signal'), _signal(estimate, 'Estimated signal')
    if clean.shape != estimate.shape:
        raise ValueError('Signals must have equal lengths.')
    power, error = np.mean(clean ** 2), np.mean((clean - estimate) ** 2)
    if not power:
        raise ValueError('SNR is undefined for a silent clean signal.')
    return float(10 * np.log10(power / error)) if error else float('inf')


def adaptive_filter(noisy, reference, algorithm='NLMS', taps=16, step=.2, forgetting=.995, delta=1.):
    noisy, reference = _signal(noisy, 'Noisy audio'), _signal(reference, 'Reference noise')
    if noisy.shape != reference.shape:
        raise ValueError('Noisy and reference signals must have equal lengths.')
    algorithm = algorithm.upper()
    if algorithm not in ('LMS', 'NLMS', 'RLS'):
        raise ValueError('Choose LMS, NLMS or RLS.')
    if not isinstance(taps, (int, np.integer)) or not 1 <= taps <= min(256, len(noisy)):
        raise ValueError('Filter taps must be between 1 and min(256, sample count).')
    if not np.isfinite(step) or step <= 0 or (algorithm == 'NLMS' and step >= 2):
        raise ValueError('Step must be positive; NLMS requires a step below 2.')
    if not np.isfinite(forgetting) or not 0 < forgetting <= 1 or not np.isfinite(delta) or delta <= 0:
        raise ValueError('RLS requires forgetting in (0,1] and positive delta.')
    start = perf_counter()
    weights = np.zeros(taps)
    delay = np.zeros(taps)
    inverse_covariance = np.eye(taps) / delta if algorithm == 'RLS' else None
    cleaned = np.empty(len(noisy))
    estimated = np.empty(len(noisy))
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        for index in range(len(noisy)):
            delay[1:] = delay[:-1]
            delay[0] = reference[index]
            estimated[index] = weights @ delay
            cleaned[index] = noisy[index] - estimated[index]
            if algorithm == 'RLS':
                projected = inverse_covariance @ delay
                denominator = forgetting + delay @ projected
                if denominator <= 0 or not np.isfinite(denominator):
                    raise ValueError('RLS became unstable. Increase delta or forgetting, or reduce filter length.')
                gain = projected / denominator
                weights += gain * cleaned[index]
                inverse_covariance = (inverse_covariance - np.outer(gain, delay @ inverse_covariance)) / forgetting
                inverse_covariance = (inverse_covariance + inverse_covariance.T) / 2
            else:
                rate = step if algorithm == 'LMS' else step / (1e-12 + delay @ delay)
                weights += rate * cleaned[index] * delay
            if not np.isfinite(cleaned[index]) or not np.isfinite(weights).all() or np.max(abs(weights)) > 1e12:
                raise ValueError(f'{algorithm} diverged; reduce step size or adjust reference amplitude.')
    return dict(cleaned=cleaned, estimated_noise=estimated, weights=weights, seconds=perf_counter() - start)


def compare_filters(noisy, reference, fs, clean=None, algorithms=('LMS', 'NLMS', 'RLS'), taps=16,
                    lms_step=.01, nlms_step=.2, forgetting=.995, delta=1.):
    noisy, reference = _signal(noisy, 'Noisy audio'), _signal(reference, 'Reference noise')
    if noisy.shape != reference.shape:
        raise ValueError('Signals must have equal sample counts and sample rates.')
    if not isinstance(fs, (int, np.integer)) or fs <= 0:
        raise ValueError('Sample rate must be positive.')
    if not algorithms:
        raise ValueError('Select at least one algorithm.')
    baseline = snr_db(clean, noisy) if clean is not None else None
    outputs, metrics = {}, []
    for algorithm in algorithms:
        result = adaptive_filter(noisy, reference, algorithm, taps, lms_step if algorithm.upper() == 'LMS' else nlms_step, forgetting, delta)
        quality = snr_db(clean, result['cleaned']) if clean is not None else None
        outputs[algorithm] = result
        metrics.append(dict(algorithm=algorithm, seconds=result['seconds'],
                            mse=float(np.mean((np.asarray(clean) - result['cleaned']) ** 2)) if clean is not None else None,
                            snr_db=quality, snr_gain_db=quality - baseline if clean is not None else None))
    return dict(outputs=outputs, metrics=metrics, input_snr_db=baseline)
