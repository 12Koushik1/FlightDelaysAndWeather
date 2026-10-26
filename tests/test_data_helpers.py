import unittest
import tempfile
from pathlib import Path
import pandas as pd
from data_helpers import decode, scheduled_utc, match_weather, load_weather, load_flights, FLIGHT_COLUMNS

class DataChecks(unittest.TestCase):
    def test_missing_quality_and_units(self):
        values = decode(pd.Series(['+0083,5','+9999,5','+0083,3','+0000,1']),0,1,9999,10)
        self.assertAlmostEqual(values.iloc[0],8.3)
        self.assertTrue(values.iloc[1:3].isna().all())
        self.assertEqual(values.iloc[3],0)
        wind = decode(pd.Series(['230,5,N,0051,5']),3,4,9999,10)
        self.assertAlmostEqual(wind.iloc[0],5.1)

    def test_midnight_and_dst(self):
        dates = pd.Series(['2024-01-01','2024-07-01','2024-03-10','2024-11-03','2024-01-01'])
        out = scheduled_utc(dates,pd.Series([2400,1200,230,130,2460]),'America/New_York')
        self.assertEqual(out.iloc[0],pd.Timestamp('2024-01-02 05:00Z'))
        self.assertEqual(out.iloc[1],pd.Timestamp('2024-07-01 16:00Z'))
        self.assertTrue(out.iloc[2:].isna().all())

    def test_matching_keeps_cancellations_and_never_uses_future_or_other_airport(self):
        f=pd.DataFrame({'Origin':['TYS']*4,'flight_id':[1,2,3,4], 'Cancelled':[0,1,0,1],
            'scheduled_departure_utc':pd.to_datetime(['2024-01-01 10:00Z','2024-01-01 12:00Z','2024-01-01 09:00Z',None],utc=True)})
        w=pd.DataFrame({'Origin':['TYS','TYS','BNA'], 'weather_time_utc':pd.to_datetime(['2024-01-01 09:00Z','2024-01-01 10:01Z','2024-01-01 12:00Z'],utc=True), 'temperature_c':[1,2,99]})
        out=match_weather(f,w,90)
        self.assertEqual(len(out),4)
        self.assertEqual(out['Cancelled'].sum(),2)
        self.assertEqual(out.loc[0,'temperature_c'],1)
        self.assertTrue(pd.isna(out.loc[1,'temperature_c']))
        self.assertEqual(out.loc[2,'weather_age_minutes'],0)
        self.assertFalse(out.loc[3,'weather_matched'])

    def test_weather_report_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'weather.csv'
            pd.DataFrame({
                'STATION':['72326013891']*4+['wrong'],
                'DATE':['2024-01-01T10:00:00']*5,
                'REPORT_TYPE':['FM-15','FM-16','SOD','FM-15','FM-15'],
                'TMP':['+0100,5','+0110,5','+0990,5','+9999,5','+0880,5'],
                'WND':['230,5,N,0051,5']*5,
                'VIS':['016093,5,N,5']*5, 'CIG':['22000,5,9,N']*5,
                'DEW':['+0050,5']*5,
            }).to_csv(path,index=False)
            weather, inventory=load_weather({'TYS':path},2024,[1])
            self.assertEqual(len(weather),1)
            self.assertEqual(weather.iloc[0]['temperature_c'],11)
            self.assertEqual(inventory.iloc[0]['duplicate_times_removed'],2)

    def test_flight_filter_and_duplicate_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'flight.csv'
            base={c:'' for c in FLIGHT_COLUMNS}
            base.update(FlightDate='2024-01-01',Origin='TYS',Dest='ATL',CRSDepTime='1200',
                        Reporting_Airline='AA',Flight_Number_Reporting_Airline='10',Cancelled='1',Diverted='0')
            pd.DataFrame([base,base,{**base,'Origin':'LAX'},{**base,'FlightDate':'2024-02-01'}]).to_csv(path,index=False)
            flights,inv,dups=load_flights([path],2024,[1])
            self.assertEqual(len(flights),1)
            self.assertEqual(dups,1)
            self.assertEqual(inv.raw_rows.sum(),4)
            self.assertTrue(pd.isna(flights.iloc[0]['DepDelay']))
            self.assertTrue(pd.isna(flights.iloc[0]['departure_delayed_15min']))

    def test_mixed_timestamp_precision(self):
        flights = pd.DataFrame({'Origin':['TYS'], 'flight_id':[1], 'Cancelled':[0],
            'scheduled_departure_utc':pd.to_datetime(['2024-01-01 10:00Z']).as_unit('ns')})
        weather = pd.DataFrame({'Origin':['TYS','TYS'], 'temperature_c':[8.0,99.0],
            'weather_time_utc':pd.to_datetime(['2024-01-01 09:30Z',None]).as_unit('us')})
        original_dtype = weather.weather_time_utc.dtype
        out = match_weather(flights, weather)
        self.assertEqual(out.loc[0, 'weather_age_minutes'],30)
        self.assertEqual(out.loc[0, 'temperature_c'],8)
        self.assertEqual(weather.weather_time_utc.dtype,original_dtype)

if __name__=='__main__':unittest.main()
