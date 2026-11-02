import unittest
import pandas as pd
from data_helpers import add_weather_categories

class WeatherCategories(unittest.TestCase):
    def decode(self, **columns):
        return add_weather_categories(pd.DataFrame(columns))

    def test_different_codebooks_and_multiple_conditions(self):
        out=self.decode(AW1_raw=['63,5','64,5','74,5','30,5'],
                        MW1_raw=['','64,5','74,5',''],MW2_raw=['71,5','','',''])
        self.assertEqual(out.loc[0,'rain_reported'],1)
        self.assertEqual(out.loc[0,'snow_reported'],1)
        self.assertEqual(out.loc[1,'freezing_precip_reported'],1)
        self.assertEqual(out.loc[1,'rain_reported'],1)
        self.assertEqual(out.loc[2,'ice_pellets_reported'],1)
        self.assertEqual(out.loc[2,'snow_reported'],1)
        self.assertEqual(out.loc[3,'fog_reported'],1)

    def test_unknown_quality_and_ambiguous_precipitation(self):
        out=self.decode(AW1_raw=['','61,3','92,5','00,5','61,5'],MW1_raw=['','','','','71,3'])
        self.assertTrue(out.loc[:2,'rain_reported'].isna().all())
        self.assertEqual(out.loc[2,'thunderstorm_reported'],1)
        self.assertEqual(out.loc[3,'rain_reported'],0)
        self.assertEqual(out.loc[4,'rain_reported'],1)
        self.assertTrue(pd.isna(out.loc[4,'snow_reported']))
        self.assertFalse(out.loc[0,'condition_codes_available'])

    def test_only_the_named_alternatives_stay_unknown(self):
        out = self.decode(AW1_raw=['92,5', '92,5', '67,5', ''], MW1_raw=['', '61,5', '', '77,5'])
        self.assertTrue(pd.isna(out.loc[0, 'rain_reported']))
        self.assertTrue(pd.isna(out.loc[0, 'snow_reported']))
        self.assertEqual(out.loc[0, 'drizzle_reported'], 0)
        self.assertEqual(out.loc[1, 'rain_reported'], 1)
        self.assertEqual(out.loc[2, 'snow_reported'], 1)
        self.assertTrue(pd.isna(out.loc[2, 'drizzle_reported']))
        self.assertEqual(out.loc[2, 'ice_pellets_reported'], 0)
        self.assertTrue(pd.isna(out.loc[3, 'fog_reported']))

    def test_current_vs_previous_hour_and_all_slots(self):
        out=self.decode(AW1_raw=['23,5','10,5','99,5',''],MW7_raw=['','','','99,5'])
        self.assertEqual(out.loc[0,'rain_reported'],0)
        self.assertEqual(out.loc[1,'mist_reported'],1)
        self.assertEqual(out.loc[1,'fog_reported'],0)
        self.assertEqual(out.loc[2,'thunderstorm_reported'],0)
        self.assertEqual(out.loc[3,'thunderstorm_reported'],1)

    def test_precipitation_units_trace_period_and_flags(self):
        out=self.decode(AA1_raw=['01,0010,9,5','01,0000,9,5','01,0000,2,5',
                                '01,0007,3,1','06,0010,9,5','01,9999,9,5',
                                '01,0010,9,3','01,0010,I,5',''])
        self.assertEqual(out.loc[0,'precipitation_1hr_mm'],1)
        self.assertEqual(out.loc[1,'precipitation_1hr_mm'],0)
        self.assertEqual(out.loc[1,'precipitation_trace'],0)
        self.assertEqual(out.loc[2,'precipitation_trace'],1)
        self.assertTrue(out.loc[2:,'precipitation_1hr_mm'].isna().all())
        self.assertTrue(out.loc[3:,'precipitation_trace'].isna().all())

if __name__=='__main__': unittest.main()
