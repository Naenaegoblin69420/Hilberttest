"""Hilbert envelope under realistic lab-acquisition conditions.

Emulates measuring the circuit's Vout(t) with a real probe + oscilloscope and
loading the capture into Python/MATLAB, then extracts the amplitude envelope
with the analytic (Hilbert) signal:

  ADS waveform
    -> de-dup timestamps        (a scope's fixed clock never repeats a time)
    -> resample to uniform fs    (the scope sample clock)
    -> band-limit to scope BW    (probe + front-end analog bandwidth)
    -> add Gaussian noise (SNR)  (thermal / probe / quantization-adjacent noise)
    -> quantize to N-bit ADC     (vertical resolution)
    -> band-pass around carrier  (reject harmonics + out-of-band noise)
    -> |Hilbert| envelope        (reflection-padded)

The band-pass stage is what lets the Hilbert envelope shed the carrier's
harmonics and edge sharpness: the envelope is a baseband quantity, so once the
harmonics and out-of-band noise are gone the recovered envelope is smooth and
tracks the true amplitude.
"""

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, sosfiltfilt

from hilbert_envelope import DEFAULT_CSV, hilbert_envelope, load_csv


def carrier_freq(v: np.ndarray, fs: float) -> float:
    """Dominant (non-DC) spectral line — the oscillation carrier."""
    spec = np.abs(np.fft.rfft(v - v.mean()))
    freqs = np.fft.rfftfreq(v.size, 1.0 / fs)
    return float(freqs[1 + np.argmax(spec[1:])])


def acquire(t, v, fs, scope_bw, snr_db, bits, seed=0):
    """Turn an ideal waveform into a realistic scope capture on a uniform grid."""
    rng = np.random.default_rng(seed)

    t_u = np.arange(t[0], t[-1], 1.0 / fs)
    v_u = np.interp(t_u, t, v)

    if scope_bw and scope_bw < fs / 2:
        v_u = sosfiltfilt(butter(4, scope_bw, fs=fs, output="sos"), v_u)

    if snr_db is not None:
        rms = np.sqrt(np.mean(v_u**2))
        v_u = v_u + rng.normal(0.0, rms / 10 ** (snr_db / 20), v_u.size)

    if bits:
        full_scale = 1.2 * np.max(np.abs(v_u))
        lsb = 2 * full_scale / (2**bits)
        v_u = np.round(v_u / lsb) * lsb

    return t_u, v_u


def bandpass(v, fs, f_lo, f_hi):
    return sosfiltfilt(butter(4, [f_lo, f_hi], btype="band", fs=fs, output="sos"), v)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", default=DEFAULT_CSV)
    p.add_argument("--fs", type=float, default=10e9, help="scope sample rate (Sa/s)")
    p.add_argument("--scope-bw", type=float, default=2e9, help="analog bandwidth (Hz)")
    p.add_argument("--snr", type=float, default=30.0, help="additive-noise SNR (dB)")
    p.add_argument("--bits", type=int, default=8, help="ADC vertical resolution")
    p.add_argument("--bp-lo", type=float, default=0.5, help="band-pass low edge (xf0)")
    p.add_argument("--bp-hi", type=float, default=1.5, help="band-pass high edge (xf0)")
    p.add_argument("--save", default="lab_pipeline.png")
    args = p.parse_args()

    t, v = load_csv(args.csv)

    # Reference: "true" envelope from the ideal waveform on the same uniform grid.
    t_u = np.arange(t[0], t[-1], 1.0 / args.fs)
    v_ideal = np.interp(t_u, t, v)
    f0 = carrier_freq(v_ideal, args.fs)
    f_lo, f_hi = args.bp_lo * f0, args.bp_hi * f0
    env_true = hilbert_envelope(bandpass(v_ideal, args.fs, f_lo, f_hi))

    # Realistic capture, then two envelope recoveries.
    t_a, v_a = acquire(t, v, args.fs, args.scope_bw, args.snr, args.bits)
    env_raw = hilbert_envelope(v_a)                                  # no harmonic/noise rejection
    env_bp = hilbert_envelope(bandpass(v_a, args.fs, f_lo, f_hi))    # harmonics + OOB noise filtered

    settled = t_a > t_a[0] + 0.15 * (t_a[-1] - t_a[0])
    err = np.sqrt(np.mean((env_bp[settled] - env_true[settled]) ** 2))
    print(f"carrier f0 = {f0/1e6:.1f} MHz, band-pass = {f_lo/1e6:.0f}-{f_hi/1e6:.0f} MHz")
    print(f"capture: fs={args.fs/1e9:g} GSa/s, BW={args.scope_bw/1e9:g} GHz, "
          f"SNR={args.snr:g} dB, {args.bits}-bit")
    print(f"recovered-vs-true envelope RMS error (settled) = {err*1e3:.2f} mV "
          f"({100*err/np.ptp(env_true):.2f}% of envelope span)")

    t_ns = t_a * 1e9
    fig = plt.figure(figsize=(14, 8))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.1, 1])

    ax0 = fig.add_subplot(gs[0, :])
    ax0.plot(t_ns, v_a, color="#1f77b4", lw=0.5, alpha=0.6, label="Scope capture (noisy)")
    ax0.plot(t_ns, env_bp, color="#d62728", lw=1.6, label="Recovered envelope (band-pass + Hilbert)")
    ax0.plot(t_ns, -env_bp, color="#d62728", lw=1.6, ls="--")
    ax0.plot(t_ns, env_true, color="#2ca02c", lw=1.2, ls=":", label="True envelope (ideal)")
    ax0.plot(t_ns, -env_true, color="#2ca02c", lw=1.2, ls=":")
    ax0.set_title(f"Emulated scope capture + Hilbert envelope  "
                  f"(fs={args.fs/1e9:g} GSa/s, {args.bits}-bit, SNR={args.snr:g} dB)")
    ax0.set_xlabel("Time (ns)"); ax0.set_ylabel("Voltage (V)")
    ax0.grid(True, alpha=0.3); ax0.legend(loc="upper right", fontsize=8)

    # Zoom: show the carrier's edge sharpness vs the smooth envelope.
    mid = t_a[0] + 0.45 * (t_a[-1] - t_a[0])
    win = (t_a >= mid) & (t_a <= mid + 25e-9)
    ax1 = fig.add_subplot(gs[1, 0])
    ax1.plot(t_ns[win], v_a[win], color="#1f77b4", lw=0.7, alpha=0.7, label="Capture")
    ax1.plot(t_ns[win], env_raw[win], color="#ff7f0e", lw=1.3, label="|Hilbert| raw (harmonics+noise)")
    ax1.plot(t_ns[win], env_bp[win], color="#d62728", lw=1.6, label="|Hilbert| band-passed")
    ax1.set_title("Zoom: band-pass removes edge sharpness")
    ax1.set_xlabel("Time (ns)"); ax1.set_ylabel("Voltage (V)")
    ax1.grid(True, alpha=0.3); ax1.legend(loc="upper right", fontsize=8)

    # Spectrum: what the band-pass keeps vs rejects.
    spec = np.abs(np.fft.rfft(v_a - v_a.mean()))
    freqs = np.fft.rfftfreq(v_a.size, 1.0 / args.fs)
    spec_db = 20 * np.log10(spec / spec.max() + 1e-12)
    ax2 = fig.add_subplot(gs[1, 1])
    ax2.plot(freqs / 1e6, spec_db, color="#1f77b4", lw=0.8)
    ax2.axvspan(f_lo / 1e6, f_hi / 1e6, color="#2ca02c", alpha=0.15, label="band-pass window")
    for h in range(2, 6):
        if f0 * h < args.fs / 2:
            ax2.axvline(f0 * h / 1e6, color="#ff7f0e", lw=0.8, ls="--", alpha=0.7)
    ax2.axvline(f0 / 1e6, color="#d62728", lw=1.0, label=f"f0 = {f0/1e6:.0f} MHz")
    ax2.set_xlim(0, min(args.fs / 2, f0 * 7) / 1e6)
    ax2.set_ylim(-90, 5)
    ax2.set_title("Spectrum: harmonics (dashed) filtered out")
    ax2.set_xlabel("Frequency (MHz)"); ax2.set_ylabel("Magnitude (dB)")
    ax2.grid(True, alpha=0.3); ax2.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    fig.savefig(args.save, dpi=130)
    print(f"Saved {args.save}")


if __name__ == "__main__":
    main()
