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

## Files

- `hilbert_envelope.py` — loader + Hilbert envelope plotter
- `requirements.txt` — `numpy`, `scipy`, `matplotlib`
- `envelope.png` — generated plot (committed for reference)
