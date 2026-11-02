# Data notes

These details explain the cleaning rules. You do not need them to run the notebook.


One row represents one scheduled departure. Flight columns retain BTS names. `Cancelled` is 1 for a cancellation; `DepDelay` is minutes, including negative values for early departures. `departure_delayed_15min` uses BTS's 15-minute indicator and stays blank for cancelled flights.

Decoded weather columns are `temperature_c`, `dewpoint_c`, `wind_speed_mps`, `visibility_m`, and `ceiling_m`. Blank values mean missing or excluded, not zero. A ceiling of 22,000 m represents NOAA's unlimited-ceiling code. Columns ending `_raw` preserve codes for later inspection. Weather categories and one-hour precipitation are decoded using the rules in [weather_codes.md](weather_codes.md).

`scheduled_departure_utc` uses the airport's local time zone (Eastern for TYS/CHA; Central for BNA/MEM), including daylight saving. Ambiguous or invalid local times are flagged and kept unmatched. NOAA report times are UTC. Routine and special reports are retained; daily/monthly summaries are excluded.

We conservatively accept weather quality codes 0, 1, 4, and 5. Other codes are excluded even though some may be usable. At duplicate station timestamps, the most complete core measurements win, followed by special-report preference and source-row order. Exact duplicate selected flight records are removed; conflicting flight identifiers are flagged for review.

The join uses the most recent report at or before scheduled departure within 90 minutes. Unmatched flights are kept. `weather_matched`, `weather_age_minutes`, and `valid_weather_measurements` show whether the match is usable. A matched report can still have missing individual readings. File names and source-row numbers allow checks against the downloads. No destination weather is included, and this does not prove the cause of a delay.


## Sources


[BTS monthly flight downloads](https://www.transtats.bts.gov/PREZIP/)

[BTS flight column descriptions](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ)

[Knoxville weather CSV](https://noaa-global-hourly-pds.s3.amazonaws.com/2024/72326013891.csv)

[Nashville weather CSV](https://noaa-global-hourly-pds.s3.amazonaws.com/2024/72327013897.csv)

[Memphis weather CSV](https://noaa-global-hourly-pds.s3.amazonaws.com/2024/72334013893.csv)

[Chattanooga weather CSV](https://noaa-global-hourly-pds.s3.amazonaws.com/2024/72324013882.csv)

[NOAA weather field documentation](https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf)

