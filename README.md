# Flight Delays and Weather

We are looking at weather and flight delays at TYS, BNA, MEM, and CHA during 2024.

## Start here

Open **Prepare_Data.ipynb** and run the cells from top to bottom. It downloads missing files, shows the raw data, filters it, and saves one combined CSV.

Use `MONTHS = [1]` to try January first. Use `MONTHS = list(range(1, 13))` for the full year. The full-year CSV is saved to `data/processed/flights_weather_2024_full_year.csv`, with one row per scheduled departure.

## First-time setup

Use Python 3.10 or newer. In a terminal inside this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m jupyterlab
```

On Windows, use `.venv\Scripts\activate` to activate the environment. In VS Code, select `.venv` as the notebook kernel.

The first run needs internet access. No API keys or manual downloads are needed. A full year needs roughly 4 GB of free space. Later runs reuse the files.

## Where things are

- **Prepare_Data.ipynb**: start here.
- **data/raw/**: original flight and weather files.
- **data/processed/**: the combined CSV.
- **data_helpers.py**: supporting code; you do not need to edit it to run the notebook.
- **docs/data_notes.md**: optional cleaning details and source links.
- **tests/**: checks for the supporting code.

The data folder is created automatically and stays off GitHub. Each teammate downloads their own copy by running the notebook.

The notebook now includes reported rain, snow, fog, and other weather conditions, plus one-hour precipitation amounts. A weather report can have measurements even when its condition codes are blank. See the [weather code guide](docs/weather_codes.md) for how to read these columns.

To run the code checks: `python -m unittest discover -s tests`.
