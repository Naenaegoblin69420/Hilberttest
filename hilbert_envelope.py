"""Compute and plot the Hilbert envelope of a time-domain CSV."""

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import hilbert

DEFAULT_CSV = r"C:\Users\angel\OneDrive\Code\ADS workspaces\SharpTestbenchV2\S02L120.csv"

TIME_UNITS = {
    "": 1.0, "s": 1.0, "sec": 1.0,
    "ms": 1e-3, "msec": 1e-3,
    "us": 1e-6, "usec": 1e-6, "µs": 1e-6, "µsec": 1e-6,
    "ns": 1e-9, "nsec": 1e-9,
    "ps": 1e-12, "psec": 1e-12,
    "fs": 1e-15, "fsec": 1e-15,
}

VOLT_UNITS = {
    "": 1.0, "V": 1.0,
    "mV": 1e-3,
    "uV": 1e-6, "µV": 1e-6,
    "nV": 1e-9,
    "kV": 1e3,
}

NUM_PATTERN = re.compile(
    r"^\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([A-Za-zµ]*)\s*$"
)


def parse_value(text: str, units: dict) -> float:
    m = NUM_PATTERN.match(text)
    if not m:
        raise ValueError(f"Cannot parse value: {text!r}")
    value = float(m.group(1))
    unit = m.group(2)
    if unit not in units:
        raise ValueError(f"Unknown unit {unit!r} in {text!r}")
    return value * units[unit]


def hilbert_envelope(v: np.ndarray, pad_frac: float = 0.25) -> np.ndarray:
    """|analytic signal| with reflection padding at both ends.

    scipy.signal.hilbert is FFT-based and treats the signal as periodic, so a
    discontinuity between v[0] and v[-1] produces a Gibbs-style envelope spike
    at the boundaries. Padding with mirrored copies of the signal makes the
    extended sequence smooth at the wrap-around and removes the artifact.
    """
    n = len(v)
    p = int(n * pad_frac)
    padded = np.concatenate([v[1:p + 1][::-1], v, v[-p - 1:-1][::-1]])
    return np.abs(hilbert(padded))[p:p + n]


def load_csv(path: str) -> tuple[np.ndarray, np.ndarray]:
    """Load an ADS-style time-domain CSV.

    ADS exports prepend a multi-line quoted metadata block (References,
    Dependency, Num. Points, Matrix Size, Type) and embed unit suffixes in
    every cell (e.g. '1.563 psec', '-1.012  V'), so a plain pandas.read_csv
    plus numeric-column selection won't work — we skip non-numeric lines and
    parse the suffix on each value.
    """
    time_vals, vout_vals = [], []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if "," not in line:
            continue
        first, _, second = line.partition(",")
        if not NUM_PATTERN.match(first):
            continue
        time_vals.append(parse_value(first, TIME_UNITS))
        vout_vals.append(parse_value(second, VOLT_UNITS))
    return np.asarray(time_vals), np.asarray(vout_vals)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to CSV (default: %(default)s)")
    parser.add_argument("--save", default="envelope.png", help="Output PNG path (default: %(default)s)")
    parser.add_argument("--show", action="store_true", help="Show the plot interactively")
    args = parser.parse_args()

    t, v = load_csv(args.csv)
    print(f"Loaded {len(t)} samples from {args.csv}")
    print(f"  Time: {t[0]:.3e} s  ..  {t[-1]:.3e} s")
    print(f"  Vout: {v.min():+.3f} V  ..  {v.max():+.3f} V")

    envelope = hilbert_envelope(v)

    t_ns = t * 1e9
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(t_ns, v, label="Vout", color="#1f77b4", linewidth=0.8)
    ax.plot(t_ns, envelope, label="Envelope (+)", color="#d62728", linewidth=1.4)
    ax.plot(t_ns, -envelope, label="Envelope (−)", color="#d62728", linewidth=1.4, linestyle="--")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title("Hilbert envelope of S02L120 Vout")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(args.save, dpi=120)
    print(f"Saved {args.save}")
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
