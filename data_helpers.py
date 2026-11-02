"""Small, reusable download and cleaning functions for the project notebook."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

AIRPORTS = {
    'TYS': ('72326013891', 'America/New_York'),
    'BNA': ('72327013897', 'America/Chicago'),
    'MEM': ('72334013893', 'America/Chicago'),
    'CHA': ('72324013882', 'America/New_York'),
}
FLIGHT_COLUMNS = ['FlightDate', 'Reporting_Airline', 'Flight_Number_Reporting_Airline',
    'Origin', 'Dest', 'CRSDepTime', 'DepTime', 'DepDelay', 'DepDel15', 'ArrDelay',
    'Cancelled', 'CancellationCode', 'Diverted', 'Distance', 'WeatherDelay',
    'CarrierDelay', 'NASDelay', 'SecurityDelay', 'LateAircraftDelay']
WEATHER_FIELDS = ['WND', 'TMP', 'DEW', 'VIS', 'CIG', 'AA1', 'AW1', 'AW2', 'AW3',
                  'AW4', 'MW1', 'MW2', 'MW3', 'MW4', 'MW5', 'MW6', 'MW7']
MEASUREMENTS = ['temperature_c', 'dewpoint_c', 'wind_speed_mps',
                'visibility_m', 'ceiling_m']

def download(url, destination):
    """Download atomically; never replace an existing raw file."""
    destination = Path(destination)
    if destination.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + '.part')
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {'User-Agent': 'FlightWeatherClassProject/1.0'}
    if offset: headers['Range'] = f'bytes={offset}-'
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        mode = 'ab' if offset and response.status == 206 else 'wb'
        with partial.open(mode) as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
    partial.replace(destination)
    return True

def ensure_data(root, year, months, allow_download=True):
    """Reuse original files or fetch missing ones. Return file paths and provenance."""
    root = Path(root)
    manifest_path = root / 'data/source_manifest.json'
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    old = {x['path']: x for x in previous}
    records, flights, weather = [], [], {}

    def record(path, url, downloaded):
        rel = str(path.relative_to(root))
        entry = old.get(rel, {'path': rel, 'url': url, 'retrieved_utc': None,
                             'note': 'Pre-existing file; original retrieval time unknown.'})
        if downloaded:
            entry.update(retrieved_utc=datetime.now(timezone.utc).isoformat(), note='Downloaded by project notebook.')
        h = hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
        entry.update(bytes=path.stat().st_size, sha256=h.hexdigest())
        records.append(entry)

    def prepare_month(month):
        name = f'On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_{year}_{month}.csv'
        path = root / 'data/raw/flights' / name
        url = f'https://www.transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip'
        fetched = False
        if not path.exists():
            if not allow_download: raise FileNotFoundError(f'Missing flight file for {year}-{month:02}. Enable downloads.')
            archive = root / 'data/raw/archives' / f'flights_{year}_{month:02}.zip'
            print(f'Downloading flights: {year}-{month:02}', flush=True)
            download(url, archive)
            path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive) as z:
                members = [n for n in z.namelist() if n.lower().endswith('.csv')]
                if len(members) != 1: raise ValueError(f'Expected one CSV in {archive}')
                partial = path.with_suffix('.csv.part')
                with z.open(members[0]) as src, partial.open('wb') as dst: shutil.copyfileobj(src, dst)
                partial.replace(path)
            fetched = True
        record(path, url, fetched)
        return path

    with ThreadPoolExecutor(max_workers=4) as pool:
        flights = list(pool.map(prepare_month, months))
    for airport, (station, _) in AIRPORTS.items():
        path = root / 'data/raw/weather' / f'{airport}_{year}.csv'
        url = f'https://noaa-global-hourly-pds.s3.amazonaws.com/{year}/{station}.csv'
        fetched = False
        if not path.exists():
            if not allow_download: raise FileNotFoundError(f'Missing {airport} weather. Enable downloads.')
            print(f'Downloading weather: {airport}', flush=True)
            fetched = download(url, path)
        weather[airport] = path
        record(path, url, fetched)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    # Preserve provenance for files outside a later, smaller demo selection.
    old.update({x['path']: x for x in records})
    manifest_path.write_text(json.dumps(list(old.values()), indent=2) + '\n')
    return flights, weather, pd.DataFrame(records)

def scheduled_utc(dates, hhmm, zone):
    """2400 is next-day midnight; ambiguous/nonexistent DST times stay missing."""
    n = pd.to_numeric(hhmm, errors='coerce')
    valid = n.eq(n.round()) & (((n // 100).between(0, 23) & (n % 100).between(0, 59)) | n.eq(2400))
    minutes = (n // 100) * 60 + n % 100
    local = pd.to_datetime(dates, errors='coerce') + pd.to_timedelta(minutes.where(valid), unit='m')
    return local.dt.tz_localize(zone, ambiguous='NaT', nonexistent='NaT').dt.tz_convert('UTC')

def load_flights(paths, year, months):
    pieces, inventory = [], []
    for path in paths:
        total, kept = 0, 0
        for chunk in pd.read_csv(path, usecols=FLIGHT_COLUMNS, dtype='string', chunksize=100_000):
            total += len(chunk)
            date = pd.to_datetime(chunk['FlightDate'], errors='coerce')
            mask = chunk['Origin'].isin(AIRPORTS) & date.dt.year.eq(year) & date.dt.month.isin(months)
            part = chunk.loc[mask].copy()
            part['flight_source_file'] = path.name
            part['flight_source_row'] = part.index + 2  # CSV line including header
            pieces.append(part)
            kept += len(part)
        inventory.append({'file': path.name, 'raw_rows': total, 'selected_rows': kept})
    f = pd.concat(pieces, ignore_index=True)
    duplicates = int(f.duplicated(subset=FLIGHT_COLUMNS).sum())
    f = f.drop_duplicates(subset=FLIGHT_COLUMNS).reset_index(drop=True)
    numeric = ['CRSDepTime','DepTime','DepDelay','DepDel15','ArrDelay','Cancelled','Diverted',
               'Distance','WeatherDelay','CarrierDelay','NASDelay','SecurityDelay','LateAircraftDelay']
    for col in numeric: f[col] = pd.to_numeric(f[col], errors='coerce')
    f['scheduled_departure_utc'] = pd.Series(pd.NaT, index=f.index, dtype='datetime64[ns, UTC]')
    for airport, (_, zone) in AIRPORTS.items():
        mask = f['Origin'].eq(airport)
        f.loc[mask, 'scheduled_departure_utc'] = scheduled_utc(f.loc[mask,'FlightDate'], f.loc[mask,'CRSDepTime'], zone)
    f['invalid_scheduled_time'] = f['scheduled_departure_utc'].isna()
    f['flight_id'] = range(1, len(f) + 1)
    key = ['FlightDate','Reporting_Airline','Flight_Number_Reporting_Airline','Origin','Dest','CRSDepTime']
    f['possible_duplicate_flight'] = f.duplicated(key, keep=False)
    # Never interpret a cancelled flight with no delay as an on-time flight.
    f['departure_delayed_15min'] = f['DepDel15'].where(f['Cancelled'].eq(0)).astype('Int64')
    return f, pd.DataFrame(inventory), duplicates

def decode(series, value_index, quality_index, missing, scale=1):
    parts = series.astype('string').str.split(',')
    value = pd.to_numeric(parts.str[value_index], errors='coerce')
    quality = parts.str[quality_index]
    # Conservative policy: accept only these four explicit pass flags.
    return (value / scale).where(value.ne(missing) & quality.isin(['0','1','4','5']))

def load_weather(paths, year, months):
    pieces, inventory = [], []
    for airport, path in paths.items():
        raw = pd.read_csv(path, dtype='string')
        raw['REPORT_TYPE'] = raw['REPORT_TYPE'].str.strip()
        times = pd.to_datetime(raw['DATE'], utc=True, errors='coerce')
        # Include a small boundary buffer for UTC/local-date differences.
        start = pd.Timestamp(year=year, month=min(months), day=1, tz='UTC') - pd.Timedelta(days=1)
        end = pd.Timestamp(year=year, month=max(months), day=1, tz='UTC') + pd.offsets.MonthBegin(1) + pd.Timedelta(days=1)
        mask = raw['STATION'].eq(AIRPORTS[airport][0]) & raw['REPORT_TYPE'].isin(['FM-15','FM-16']) & times.ge(start) & times.lt(end)
        w = raw.loc[mask].copy()
        w['weather_source_row'] = w.index + 2
        w['weather_time_utc'] = times.loc[mask]
        w['Origin'] = airport
        w['weather_source_file'] = path.name
        for col in WEATHER_FIELDS:
            if col not in w: w[col] = pd.NA
        for name, col, vi, qi, sentinel, scale in [
            ('temperature_c','TMP',0,1,9999,10), ('dewpoint_c','DEW',0,1,9999,10),
            ('wind_speed_mps','WND',3,4,9999,10), ('visibility_m','VIS',0,1,999999,1),
            ('ceiling_m','CIG',0,1,99999,1)]:
            w[name] = decode(w[col],vi,qi,sentinel,scale)
        # Count the five core readings before decoding precipitation and condition codes.
        w['valid_weather_measurements'] = w[MEASUREMENTS].notna().sum(axis=1)
        w['_priority'] = w['REPORT_TYPE'].map({'FM-15':0,'FM-16':1})
        n = len(w)
        w = w.sort_values(['weather_time_utc','valid_weather_measurements','_priority','weather_source_row'],kind='stable')
        w = w.drop_duplicates(['Origin','weather_time_utc'],keep='last')
        inventory.append({'airport':airport,'raw_rows':len(raw),'routine_special_rows':n,
                          'duplicate_times_removed':n-len(w),'clean_weather_rows':len(w)})
        columns = ['Origin','STATION','REPORT_TYPE','weather_time_utc','weather_source_file',
                   'weather_source_row','valid_weather_measurements'] + MEASUREMENTS + WEATHER_FIELDS
        pieces.append(w[columns].rename(columns={c:c+'_raw' for c in WEATHER_FIELDS}))
    return add_weather_categories(pd.concat(pieces, ignore_index=True)), pd.DataFrame(inventory)

def match_weather(flights, weather, tolerance_minutes=90):
    if tolerance_minutes < 0: raise ValueError('Tolerance cannot be negative')
    # Pandas versions can use different timestamp precision (us versus ns).
    # merge_asof requires exactly the same type on both sides.
    flights = flights.copy()
    weather = weather.copy()
    for frame, column in [(flights, 'scheduled_departure_utc'), (weather, 'weather_time_utc')]:
        frame[column] = pd.to_datetime(frame[column], utc=True, errors='coerce').astype('datetime64[ns, UTC]')
    weather = weather.loc[weather['weather_time_utc'].notna()].copy()
    results = []
    for airport in AIRPORTS:
        f = flights.loc[flights['Origin'].eq(airport)]
        valid = f.loc[f['scheduled_departure_utc'].notna()].sort_values('scheduled_departure_utc')
        w = weather.loc[weather['Origin'].eq(airport)].drop(columns='Origin').sort_values('weather_time_utc')
        merged = pd.merge_asof(valid, w, left_on='scheduled_departure_utc', right_on='weather_time_utc',
                               direction='backward', tolerance=pd.Timedelta(minutes=tolerance_minutes))
        results.extend([merged, f.loc[f['scheduled_departure_utc'].isna()]])
    out = pd.concat(results, ignore_index=True).sort_values('flight_id').reset_index(drop=True)
    out['weather_matched'] = out['weather_time_utc'].notna()
    out['weather_age_minutes'] = (out['scheduled_departure_utc']-out['weather_time_utc']).dt.total_seconds()/60
    assert len(out) == len(flights) and out['flight_id'].is_unique
    assert out.loc[out['weather_matched'],'weather_age_minutes'].between(0,tolerance_minutes).all()
    assert out['Cancelled'].sum() == flights['Cancelled'].sum()
    return out

# NOAA ISD (2018), printed pages 31-33 and 105-107.
# AW and MW have different codebooks. Sets indicate definite current conditions.
WEATHER_CATEGORIES = {
    'rain_reported': ({57,58,60,61,62,63,81,82,83,84}, {58,59,60,61,62,63,64,65,80,81,82,83,84,91,92}),
    'drizzle_reported': ({50,51,52,53,57,58}, {50,51,52,53,54,55,58,59}),
    'snow_reported': ({67,68,70,71,72,73,77,85,86,87}, {68,69,70,71,72,73,74,75,77,83,84,85,86}),
    'freezing_precip_reported': ({47,48,54,55,56,64,65,66}, {56,57,66,67}),
    'ice_pellets_reported': ({74,75,76}, {79}),
    'fog_reported': (set(range(30,36)), {11,12,*range(41,50)}),
    'mist_reported': ({10}, {10}),
    'thunderstorm_reported': (set(range(90,97)), {17,95,96,97,98,99}),
}
# For each flag, these codes allow the condition but do not confirm it.
# AW92, for example, confirms a storm with rain and/or snow.
POSSIBLE_CONDITIONS = {
    'rain_reported': ({40,41,42,43,44,67,68,80,92,95}, {68,69,87,88,89,90,93,94,95,97}),
    'drizzle_reported': ({40,41,42,43,44,67,68,80}, {68,69}),
    'snow_reported': ({40,41,42,45,46,80,92,95}, {87,88,89,90,93,94,95,97}),
    'ice_pellets_reported': ({40,41,42,45,46,80}, set()),
    'freezing_precip_reported': ({40,41,42,43,44,80}, set()),
    'fog_reported': (set(), {76,77,78}),
}
AW_KNOWN = {0,1,2,3,4,5,7,10,11,12,18,*range(20,36),*range(40,49),
            *range(50,59),*range(60,69),*range(70,79),*range(80,88),89,*range(90,97),99}
GOOD_QUALITY = {'0','1','4','5'}


def add_weather_categories(weather):
    """1 = explicitly reported; 0 = not reported in usable codes; blank = unknown.

    Zero is not proof of absence. No usable codes leaves every category blank.
    Multiple categories may be 1. Original fields are preserved for checking.
    """
    out = weather.copy()
    fields = [f'{kind}{i}_raw' for kind, count in [('AW',4),('MW',7)]
              for i in range(1,count+1) if f'{kind}{i}_raw' in out]
    def classify(row):
        codes = {'AW':set(), 'MW':set()}
        incomplete = False
        for field in fields:
            value = row[field]
            if pd.isna(value) or not str(value).strip():
                continue
            parts = str(value).strip().split(',')
            kind = field[:2]
            if (len(parts) != 2 or not parts[0].isdigit()
                    or parts[1] not in GOOD_QUALITY):
                incomplete = True
                continue
            code = int(parts[0])
            if code not in (AW_KNOWN if kind == 'AW' else range(100)):
                incomplete = True
                continue
            codes[kind].add(code)
        usable = bool(codes['AW'] or codes['MW'])
        result = {'condition_codes_available':usable}
        for name, (aw, mw) in WEATHER_CATEGORIES.items():
            positive = bool(codes['AW'] & aw or codes['MW'] & mw)
            possible_aw, possible_mw = POSSIBLE_CONDITIONS.get(name, (set(), set()))
            possible = bool(codes['AW'] & possible_aw or codes['MW'] & possible_mw)
            if positive:
                result[name] = 1
            elif not usable or incomplete or possible:
                result[name] = pd.NA
            else:
                result[name] = 0
        return result
    flags = pd.DataFrame([classify(row) for _, row in out.iterrows()], index=out.index,
                         columns=['condition_codes_available', *WEATHER_CATEGORIES])
    for name in WEATHER_CATEGORIES:
        out[name] = flags[name].astype('Int64')
    out['condition_codes_available'] = flags['condition_codes_available'].astype(bool)

    # Only AA1 one-hour amounts are comparable. Do not divide multi-hour totals.
    parts = out.get('AA1_raw', pd.Series(pd.NA,index=out.index,dtype='string')).astype('string').str.split(',')
    hours = pd.to_numeric(parts.str[0],errors='coerce')
    depth = pd.to_numeric(parts.str[1],errors='coerce')
    condition, quality = parts.str[2], parts.str[3]
    usable = parts.str.len().eq(4) & hours.eq(1) & quality.isin(GOOD_QUALITY)
    trace = usable & condition.eq('2')
    measured = usable & condition.eq('9') & depth.between(0,9998)
    out['precipitation_1hr_mm'] = (depth / 10).where(measured).astype('Float64')
    out['precipitation_trace'] = pd.Series(pd.NA,index=out.index,dtype='Int64')
    out.loc[measured,'precipitation_trace'] = 0
    out.loc[trace,'precipitation_trace'] = 1
    return out
