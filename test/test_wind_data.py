# coding=utf-8
import os
import unittest

import pandas as pd

import test


class MyTestCaseWind_Data(unittest.TestCase):
    def test_get_all_stk_list(self):
        dt = '2022-03-04'
        real = pd.read_json(os.path.join(test.__path__[0], 'all_stk_20220304.json'))
        from Barra_creator.data.wind_data import get_all_stk_list
        res = get_all_stk_list(dt)

        self.assertEqual(True, (res.values == real.values).all())  # add assertion here


if __name__ == '__main__':
    unittest.main()
