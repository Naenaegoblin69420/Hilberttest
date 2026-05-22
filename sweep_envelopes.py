"""Generate Hilbert-envelope plots for every L1 value in an ADS parametric sweep.

Writes one plot per sweep value into --all-dir, plus a second copy of every
--step nH value into --step-dir, using the same blue-trace / red-envelope
style as hilbert_envelope.py.
"""

import argparse
from collections import OrderedDict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from hilbert_envelope import (
    NUM_PATTERN, TIME_UNITS, VOLT_UNITS, dedup_time, hilbert_envelope, parse_value,
)

DEFAULT_CSV = r"C:\Users\angel\OneDrive\Code\ADS workspaces\SharpTestbenchV2\S02LSweep50130R2.csv"


def load_sweep_csv(path: str) -> "OrderedDict[float, tuple[np.ndarray, np.ndarray]]":
    """Load an ADS parametric-sweep CSV (columns: L1, time, Vout).

    Rows are grouped by L1 sweep value; the time/Vout unit suffixes in each
    cell are parsed to SI. Returns {L1_nH: (time_s, vout_V)}.
    """
    sweeps: "OrderedDict[float, tuple[list, list]]" = OrderedDict()
    for line in Path(path).read_text().splitlines():
        parts = line.strip().split(",")
        if len(parts) != 3 or not NUM_PATTERN.match(parts[0]):
            continue
        l1 = float(parts[0])
        t, v = sweeps.setdefault(l1, ([], []))
        t.append(parse_value(parts[1], TIME_UNITS))
        v.append(parse_value(parts[2], VOLT_UNITS))
    return OrderedDict((k, dedup_time(np.asarray(t), np.asarray(v))) for k, (t, v) in sweeps.items())


def plot_envelope(l1: float, t: np.ndarray, v: np.ndarray, out_path: Path) -> None:
    env = hilbert_envelope(v)
    t_ns = t * 1e9
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(t_ns, v, label="Vout", color="#1f77b4", linewidth=0.8)
    ax.plot(t_ns, env, label="Envelope (+)", color="#d62728", linewidth=1.4)
    ax.plot(t_ns, -env, label="Envelope (−)", color="#d62728", linewidth=1.4, linestyle="--")
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title(f"Hilbert envelope of S02 Vout — L1 = {l1:g} nH")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=DEFAULT_CSV)
    parser.add_argument("--all-dir", default="sweep_all")
    parser.add_argument("--step-dir", default="sweep_every10nH")
    parser.add_argument("--step", type=int, default=10, help="nH increment for the second folder")
    args = parser.parse_args()

    sweeps = load_sweep_csv(args.csv)
    all_dir = Path(args.all_dir)
    step_dir = Path(args.step_dir)
    all_dir.mkdir(exist_ok=True)
    step_dir.mkdir(exist_ok=True)

    vals = list(sweeps)
    print(f"Loaded {len(vals)} sweeps: {min(vals):g}..{max(vals):g} nH, "
          f"{len(sweeps[vals[0]][0])} pts each")

    n_step = 0
    for l1, (t, v) in sweeps.items():
        name = f"L1_{int(round(l1)):03d}nH.png"
        plot_envelope(l1, t, v, all_dir / name)
        if int(round(l1)) % args.step == 0:
            plot_envelope(l1, t, v, step_dir / f"step{args.step}_{name}")
            n_step += 1
    print(f"Wrote {len(vals)} plots -> {all_dir}/  and  {n_step} plots -> {step_dir}/")


if __name__ == "__main__":
    main()
