# coding=utf-8
from datetime import datetime
from functools import partial

import pandas as pd
from WindPy import w

from Barra_creator.utils.chunk import chunk
from Barra_creator.utils.file_cache import file_cache
from Barra_creator.utils.singleton import Singleton

__CacheGranularity__ = 'd'


def wind_exec_deco(w, enable_cache=True):
    if not w.isconnected():
        w.start()

    def deco(func):
        if enable_cache:  #
            func = file_cache(granularity=__CacheGranularity__)(func)

        def _deco(*args, **kwargs):
            errno, df = func(*args, w=w, **kwargs)
            if errno != 0:
                raise ValueError(df['OUTMESSAGE'].values[0])
            return df

        return _deco

    return deco


def push_back_tdays_by_wind(dt, window_length=252, shift=1, w=None):
    error, start_dt = w.tdaysoffset(-1 * (window_length + shift), dt, "", usedf=True)
    start_dt = start_dt[''].dt.strftime("%Y-%m-%d").values[0]
    return start_dt


class WindDataAPIRawNotChange(object):
    @staticmethod
    # @file_cache(granularity=__CacheGranularity__)
    @wind_exec_deco(w, enable_cache=True)
    def get_all_stk_list(dt, w=None):
        """
        获取所有股票列表
        :param dt: string 'YYYY-MM-DD'
        :return: DataFrame[date,wind_code,sec_name]
        """

        return w.wset("sectorconstituent", f"date={dt};sectorid=a001010100000000", usedf=True, )

    @classmethod
    @wind_exec_deco(w, enable_cache=True)
    def __func_create__(cls, stk_list: list, dt: str, window_length=0, shift=0, max_duration=30, func_name: str = None,
                        w=None):
        if isinstance(stk_list, str):
            stk_list = [stk_list]

        # stk_length = len(stk_list)

        if window_length + shift == 0:
            return getattr(cls, func_name)(stk_list, dt, dt, w=w)

        elif window_length + shift > max_duration:
            start_dt = push_back_tdays_by_wind(dt, window_length=window_length, shift=shift, w=w)
            s_holder = []
            for start_end in chunk(pd.date_range(start_dt, dt), chunks=max_duration):
                errno, s1 = getattr(cls, func_name)(stk_list,
                                                    start_end.min().strftime("%Y-%m-%d"),
                                                    start_end.max().strftime("%Y-%m-%d"),
                                                    w=w)
                s_holder.append(s1)

            return errno, pd.concat(s_holder)
        else:
            start_dt = push_back_tdays_by_wind(dt, window_length=window_length, shift=shift, w=w)
            return getattr(cls, func_name)(stk_list, start_dt, dt, w=w)

    @staticmethod
    def __wsd_get_stk_floatmv__(stk_list: list, start_dt: str, end_dt, w=None):
        return w.wsd(",".join(stk_list), "mkt_cap_float", start_dt, end_dt, "unit=1;currencyType=", usedf=True)

    @staticmethod
    def __wsd_get_stk_close__(stk_list: list, start_dt: str, end_dt, w=None):
        return w.wsd(",".join(stk_list), "close", start_dt, end_dt, "unit=1;Currency=CNY;PriceAdj=B", usedf=True)

    @staticmethod
    def __wsd_get_stk_pct_chg__(stk_list: list, start_dt: str, end_dt, w=None):
        return w.wsd(",".join(stk_list), "pct_chg", start_dt, end_dt, "unit=1;Currency=CNY;PriceAdj=B", usedf=True)

    @staticmethod
    def __wsd_get_stk_adjfactor__(stk_list: list, start_dt: str, end_dt, w=None):
        return w.wsd(",".join(stk_list), "adjfactor", start_dt, end_dt, "unit=1;Currency=CNY;PriceAdj=B", usedf=True)

    @staticmethod
    def __wsd_get_stk_trade_status__(stk_list: list, start_dt: str, end_dt, w=None):
        return w.wsd(",".join(stk_list), "trade_status", start_dt, end_dt, "unit=1;Currency=CNY;PriceAdj=B", usedf=True)

    @staticmethod
    # @wind_exec_deco(w, enable_cache=True)
    def __edb_get_bond_rf__(indicator_id: (str, list), start_dt: str = '2000-01-01',
                            end_dt=datetime.today().strftime('%Y-%m-%d'),
                            w=None):
        """

        存贷款利率(央行)[CBondBenchmark]
        select trade_dt, b_info_rate from eterminal.CBondBenchmark  where b_info_benchmark=01010203 order by trade_dt asc
        01010203个人定期(整存整取)一年


        :param stk_list:
        :param start_dt:
        :param end_dt:
        :param w:
        :return:
        """
        if indicator_id is None:
            indi_id = "M0009808"
        elif isinstance(indicator_id, str):
            indi_id = indicator_id
        elif isinstance(indicator_id, list):
            indi_id = ','.join(indicator_id)
        else:
            raise ValueError('indicator_id must be str list')
        res = w.edb(indi_id, start_dt, end_dt, "Fill=Previous", usedf=True)
        return res


@Singleton
class WindDataAPIRaw(WindDataAPIRawNotChange):
    @classmethod
    def init(cls):
        func_name_list = list(filter(lambda x: x.startswith('__wsd_get_') and x.endswith('__'), dir(cls)))
        f_name_list = [func_name[6:-2] for func_name in func_name_list]
        for f_name, func_name in zip(f_name_list, func_name_list):
            func = partial(cls.__func_create__, func_name=func_name)
            setattr(cls, f_name, func)

    def __getattr__(self, item):
        dir_funcs_list = dir(self)
        wsd_func_name_list = list(filter(lambda x: x.startswith('__wsd_get_') and x.endswith('__'), dir_funcs_list))
        edb_func_name_list = list(filter(lambda x: x.startswith('__edb_get_') and x.endswith('__'), dir_funcs_list))
        wsd_f_name_list = [func_name[6:-2] for func_name in wsd_func_name_list]
        edb_f_name_list = [func_name[6:-2] for func_name in edb_func_name_list]
        if item in dir_funcs_list:
            return super(WindDataAPIRaw, self).__getattribute__(item)
        elif item in wsd_f_name_list:
            return partial(self.__func_create__, func_name=wsd_func_name_list[wsd_f_name_list.index(item)])
        elif item in edb_f_name_list:
            return partial(self.__func_create__, func_name=edb_func_name_list[edb_f_name_list.index(item)])
        else:
            return super(WindDataAPIRawNotChange, self).__getattribute__(item)

    # @classmethod
    # # @file_cache(granularity=__CacheGranularity__)
    # def get_stk_floatmv(cls, stk_list: list, dt: str, window_length=0, shift=0, max_duration=30, w=None):
    #     """
    #     获取指定stk list 的流动市值
    #     :param stk_list:
    #     :param dt:  YYYY-MM-DD
    #     :return: DataFrame; mkt_cap_float with stk index
    #     """
    #     if window_length + shift == 0:
    #         return cls.__get_stk_floatmv__(stk_list, dt, dt, w=w)
    #
    #     elif window_length + shift > max_duration:
    #         start_dt = push_back_tdays_by_wind(dt, window_length=window_length, shift=shift, w=w)
    #         s_holder = []
    #         for start_end in chunk(pd.date_range(start_dt, dt), chunks=max_duration):
    #             errno, s1 = cls.__get_stk_floatmv__(stk_list,
    #                                                 start_end.min().strftime("%Y-%m-%d"),
    #                                                 start_end.max().strftime("%Y-%m-%d"),
    #                                                 w=w)
    #             s_holder.append(s1)
    #
    #         return errno, pd.concat(s_holder)
    #     else:
    #         start_dt = push_back_tdays_by_wind(dt, window_length=window_length, shift=shift, w=w)
    #         return cls.__get_stk_floatmv__(stk_list, start_dt, dt, w=w)
    #
    # @classmethod
    # # @file_cache(granularity=__CacheGranularity__)
    # @wind_exec_deco(w, enable_cache=False)
    # def get_stk_close(cls, stk_list: list, dt: str, window_length=252, shift=1, max_duration=30, w=None):
    #     """
    #     获取指定stk list 的流动市值
    #     :param stk_list:
    #     :param dt:  YYYY-MM-DD
    #     :return: DataFrame; mkt_cap_float with stk index
    #     """
    #     if window_length + shift == 0:
    #         return cls.__get_stk_close__(stk_list, dt, dt, w=w)
    #
    #     elif window_length + shift > max_duration:
    #         # push back given window_length trading days
    #         start_dt = push_back_tdays_by_wind(dt, window_length=window_length, shift=shift, w=w)
    #         s_holder = []
    #         for start_end in chunk(pd.date_range(start_dt, dt), chunks=max_duration):
    #             errno, s1 = cls.__get_stk_close__(stk_list, start_end.min().strftime("%Y-%m-%d"),
    #                                               start_end.max().strftime("%Y-%m-%d"), w=w)
    #
    #             s_holder.append(s1)
    #         return errno, pd.concat(s_holder)
    #     else:
    #         # push back given window_length trading days
    #         error, start_dt = w.tdaysoffset(-1 * (window_length + shift), dt, "", usedf=True)
    #         start_dt = start_dt[''].dt.strftime("%Y-%m-%d").values[0]
    #         return cls.__get_stk_close__(stk_list, start_dt, dt, w=w)
    #
    # @staticmethod
    # # @file_cache(granularity=__CacheGranularity__)
    # @wind_exec_deco(w, enable_cache=True)
    # def get_stk_adjfactor(stk_list: list, dt: str, window_length=252, shift=1, w=None):
    #     """
    #     获取指定stk list 的流动市值
    #     :param stk_list:
    #     :param dt:  YYYY-MM-DD
    #     :return: DataFrame; mkt_cap_float with stk index
    #     """
    #     # push back given window_length trading days
    #     error, start_dt = w.tdaysoffset(-1 * (window_length + shift), dt, "", usedf=True)
    #     start_dt = start_dt[''].dt.strftime("%Y-%m-%d").values[0]
    #     s = w.wsd(",".join(stk_list), "adjfactor", start_dt, dt, "unit=1;Currency=CNY;PriceAdj=B", usedf=True)
    #     return s


wd = WindDataAPIRaw()


class BarraDataFromWind(object):
    @staticmethod
    def get_stk_all_floatmv(dt: str, ret_full_stk_list=False, window_length=252):
        """
        get float market value and stk list
        :param dt:  YYYY-MM-DD
        :return:
        """

        stk_list = wd.get_all_stk_list(dt)['wind_code'].unique().tolist()
        df = wd.get_stk_floatmv(stk_list, dt, window_length=window_length, shift=1, max_duration=30)
        if len(stk_list) == 1:
            df.columns = stk_list
        return stk_list, df if ret_full_stk_list else df

    @staticmethod
    def get_stk_all_beta(dt, window_length=252, ):
        stk_list = wd.get_all_stk_list('2022-03-04')['wind_code'].unique().tolist()
        risk_free = wd.get_bond_rf(["M0009808"], dt, window_length=6000, max_duration=100000000)
        mkt_ret = wd.get_stk_pct_chg(['000985.CSI'], dt, window_length=window_length, shift=1)
        trade_status = wd.get_stk_trade_status(stk_list,dt, window_length=window_length, shift=1)
        close = wd.get_stk_close(stk_list, dt, window_length=window_length, shift=1)
        adjfactor = wd.get_stk_adjfactor(stk_list, dt, window_length=window_length, shift=1)
        print(1)

    # @staticmethod
    # def get_mkt_ret(dt, wind_code=['000985.CSI'], window_length=252):
    #     res = wd.get_stk_pct_chg(wind_code, dt, window_length=window_length, shift=1)
    #     if len(wind_code) == 1:
    #         res.columns = wind_code
    #     return res


if __name__ == '__main__':
    wd = WindDataAPIRaw()

    c = BarraDataFromWind.get_stk_all_beta('2022-03-04')
    # c2 = c['wind_code'].unique().tolist()
    # d = wd.get_stk_trade_status(c2, '2022-03-04', window_length=252, shift=1)
    # rf1 = wd.get_bond_rf("M0009808", '2022-03-04', window_length=6000, max_duration=100000000)
    # c2 = BarraDataFromWind.get_risk_free('2022-03-04')
    print(1)
    pass
