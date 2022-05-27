# coding=utf-8

import numpy as np
import pandas as pd

from Barra_creator.core.raw import MetaFactorCreator

"""
### 1. Size

* Definition：

  > $Ln(cap)$
  >
  > Natural log of market cap,
  >
  > Given by the logarithm of the total market capitalization of the firm

"""


def get_ln_cap(data: (np.array, pd.Series)):
    return np.log(data)


output_cols = ['stk_code', 'mkt_cap_float', 'trade_dt']


class LnCap(MetaFactorCreator):

    @classmethod
    def calculate(cls, data: pd.Series, full_stk_list, dt: str, return_columns=False):
        """

        :param data: float mv with stk index
        :param full_stk_list:
        :param dt:  YYYY-MM-DD
        :return: DataFrame[stk_code,mkt_cap_float,trade_dt]
        """

        ln_cap = get_ln_cap(data=data)
        ln_cap['trade_dt'] = pd.to_datetime(dt)
        dta = ln_cap.reindex(full_stk_list).reset_index()  # add missing stk_code with fill nan
        dta.columns = output_cols
        if return_columns:
            return dta, output_cols
        else:
            return dta


if __name__ == '__main__':
    from Barra_creator.data.wind_data import BarraDataFromWind

    dt = '2022-03-04'
    stk_list, data = BarraDataFromWind.get_stk_all_floatmv(dt, ret_full_stk_list=True)
    c_data = LnCap.calculate(data, stk_list, dt)

    print(1)
    pass


