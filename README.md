# hilberttest

![Hilbert envelope of S02L120 Vout](envelope.png)

Hilbert transform of a time-domain `Vout` trace exported from Keysight ADS.
The script reads an ADS-style CSV (multi-line metadata header, per-cell unit
suffixes like `psec` / `nsec` / `mV` / `V`), computes the analytic signal via
`scipy.signal.hilbert`, and plots the original waveform with the +/- envelope
overlaid.

## Usage

```bash
pip install -r requirements.txt
python hilbert_envelope.py --save envelope.png
```

By default the script reads the path baked into `DEFAULT_CSV`. Override with
`--csv path/to/other.csv`, or pass `--show` to open the plot interactively.

## Parametric sweep (L1 = 50–130 nH)

`sweep_envelopes.py` runs the same envelope analysis across an ADS L1 sweep
(`S02LSweep50130R2.csv` — 81 values from 50 to 130 nH in 1 nH steps):

```bash
python sweep_envelopes.py
```

- `sweep_all/` — one plot per L1 value (`L1_050nH.png` … `L1_130nH.png`, 81 total)
- `sweep_every10nH/` — only the 10 nH increments (`step10_L1_050nH.png` … `step10_L1_130nH.png`, 9 total)

## Files

- `hilbert_envelope.py` — loader + Hilbert envelope plotter (single trace)
- `sweep_envelopes.py` — batch envelope plots across an L1 parametric sweep
- `requirements.txt` — `numpy`, `scipy`, `matplotlib`
- `envelope.png` — generated plot (committed for reference)
- `sweep_all/`, `sweep_every10nH/` — generated sweep plots
