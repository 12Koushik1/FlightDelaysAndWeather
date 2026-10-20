# Flight Delays and Weather

We want to see how weather conditions line up with flight delays and cancellations. We will combine flight records with weather readings for the same airports and times.

## Our starting plan

Start with Knoxville (TYS) in January 2024. Once we can match the flight and weather data, expand to Nashville (BNA), Memphis (MEM), and more months of 2024.

## Data

Download the data using the links below. CSV and ZIP files stay on each person's computer and are excluded from Git because the flight files are too large for GitHub.

**BTS flight data:** Flight dates, airports, scheduled departure times, delays, and cancellations.

[Download January 2024 flight data (ZIP)](https://www.transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_1.zip)

[Flight column descriptions](https://www.transtats.bts.gov/Fields.asp?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ)

The downloaded CSV is in `Jan_2024_Flight_Data/`. It includes airports across the country, so we need to filter it to our airports.

**NOAA weather data:** Weather observations at each airport. The files below cover 2024.

[Knoxville / TYS weather CSV](https://noaa-global-hourly-pds.s3.amazonaws.com/2024/72326013891.csv)

[Nashville / BNA weather CSV](https://noaa-global-hourly-pds.s3.amazonaws.com/2024/72327013897.csv)

[Memphis / MEM weather CSV](https://noaa-global-hourly-pds.s3.amazonaws.com/2024/72334013893.csv)

[Weather data information and documentation](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)

We saved these as `TYS_Weather.csv`, `BNA_Weather.csv`, and `MEM_Weather.csv`.

## First steps

1. Keep flights departing from TYS in January 2024.
2. Prepare the matching TYS weather readings. Use the NOAA documentation to understand the weather codes and missing values.
3. Put both datasets in the same time zone and match weather to each flight's scheduled departure time.
4. Check for missing matches and make sure flights are not duplicated. Keep cancelled flights even if their delay is blank.
5. Compare delays and cancellation rates under different weather conditions.

Keep the original downloads unchanged and save prepared data separately. We are looking for patterns; a match between bad weather and delays does not prove why an individual flight was delayed.

## Team tasks

We will fill in names together:

- Flight data: TBD
- Weather data: TBD
- Matching the data: TBD
- Proposal and project notes: TBD
