# coding=utf-8
import pandas as pd

from Barra_creator.core.raw import MetaFactorCreator


def get_mkt_beta(data):
    return data


output_cols = ['stk_code', 'mkt_cap_float', 'trade_dt']


class MktBeta(MetaFactorCreator):
    @classmethod
    def calculate(cls, data: pd.Series, full_stk_list, dt: str, return_columns=False):
        """

        :param data: float mv with stk index
        :param full_stk_list:
        :param dt:  YYYY-MM-DD
        :return: DataFrame[stk_code,mkt_cap_float,trade_dt]
        """

        ln_cap = get_mkt_beta(data=data)
        ln_cap['trade_dt'] = pd.to_datetime(dt)
        dta = ln_cap.reindex(full_stk_list).reset_index()  # add missing stk_code with fill nan
        dta.columns = output_cols
        if return_columns:
            return dta, output_cols
        else:
            return dta

    pass


if __name__ == '__main__':
    pass
