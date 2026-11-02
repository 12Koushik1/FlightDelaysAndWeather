# Weather categories

Use these columns to compare flights with reported weather conditions. They describe the matched report, which can be up to 90 minutes before departure.

- **1:** a usable code explicitly reports the condition.
- **0:** usable codes do not explicitly report it. This is not proof of clear weather or absence.
- **Blank:** no usable codes, rejected codes, or an uncertain precipitation type.
- `condition_codes_available` says whether any usable AW/MW codes were found. This is separate from `weather_matched`.

Several groups can be 1 on the same row. Rain excludes freezing rain; drizzle, mist, and ice pellets have their own columns. Snow includes snow grains and explicitly mixed snow. We do not infer rain or snow from temperature or precipitation amount.

## Positive mappings

These sets cover definite current conditions, including codes not yet seen in our files. Check every AW1–AW4 and MW1–MW7 slot; the two families use different codebooks.

| Column | AW codes | MW codes |
|---|---|---|
| `rain_reported` | 57, 58, 60, 61, 62, 63, 81, 82, 83, 84 | 58, 59, 60, 61, 62, 63, 64, 65, 80, 81, 82, 83, 84, 91, 92 |
| `drizzle_reported` | 50, 51, 52, 53, 57, 58 | 50, 51, 52, 53, 54, 55, 58, 59 |
| `snow_reported` | 67, 68, 70, 71, 72, 73, 77, 85, 86, 87 | 68, 69, 70, 71, 72, 73, 74, 75, 77, 83, 84, 85, 86 |
| `freezing_precip_reported` | 47, 48, 54, 55, 56, 64, 65, 66 | 56, 57, 66, 67 |
| `ice_pellets_reported` | 74, 75, 76 | 79 |
| `fog_reported` | 30, 31, 32, 33, 34, 35 | 11, 12, 41, 42, 43, 44, 45, 46, 47, 48, 49 |
| `mist_reported` | 10 | 10 |
| `thunderstorm_reported` | 90, 91, 92, 93, 94, 95, 96 | 17, 95, 96, 97, 98, 99 |

## Uncertainty and quality

Use quality flags 0, 1, 4, and 5, matching our existing conservative cleaning policy. Rejected or unrecognized codes keep non-positive categories unknown. Missing optional slots do not invalidate usable slots.

Some reports name alternatives. AW92 confirms a thunderstorm with rain, snow, or both. We mark thunderstorm as 1 and leave rain and snow blank unless another usable code confirms one of them. A usable rain code in the same report sets rain to 1. Each flag has its own list of possible codes in `POSSIBLE_CONDITIONS`. A 0 means the codes did not mention that condition.

Past-hour weather is not classified as current weather. For example AW23 is past rain; MW91/92 establish current rain but only past thunder. Blowing snow/sand is not treated as falling snow. Unclassified conditions remain in the original code columns; a row of zero flags must not be called clear weather.

## Precipitation

`precipitation_1hr_mm` uses only AA1 with a one-hour period, accepted quality, condition 9, and a valid amount (0–9998), divided by ten. Condition 9 means the condition flag is missing; it does not invalidate the amount by itself. We retain it under this explicit project rule.

Condition 2 sets `precipitation_trace` to 1, with amount blank rather than a made-up zero. An accepted measurable amount sets the trace flag to 0. Accumulation boundaries, incomplete/estimated amounts, missing sentinels, and multi-hour totals stay blank. AA2–AA4 are not used; this sacrifices coverage for simplicity. This is water-equivalent precipitation, not snowfall depth. Do not sum across flights: flights can share the same weather report.

## Source and checking

[NOAA ISD documentation](https://www.ncei.noaa.gov/pub/data/noaa/isd-format-document.pdf), printed pages 13–14 (AA), 31–33 (AW), and 105–107 (MW).

Tests cover the separate codebooks, mixed conditions, missing/poor-quality reports, past versus current weather, all manual slots, trace amounts, accumulation flags, and units. Keep the raw columns to inspect individual matches. Compare “reported” with “not reported in usable codes”; report unknown coverage alongside results.
