#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
计算：股票技术因子：MA5。频率为：日频
"""

import datetime
import numpy as np
import pandas as pd
import math
# from gjfactor import Factor

SQL_HQ = """
    select trade_dt, s_info_windcode, s_dq_close, s_dq_adjfactor, s_dq_amount
    from eterminal.ashareeodprices
    where trade_dt >={} and trade_dt<={}
"""

SQL_RISKFREE = """
    select trade_dt, b_info_rate from eterminal.CBondBenchmark
    where b_info_benchmark=01010203 order by trade_dt asc
"""

SQL_ST = """
    select s_info_windcode, entry_dt, remove_dt 
    from eterminal.AShareST
"""

SQL_MKT_RET = """
  select S_INFO_WINDCODE, to_number(TRADE_DT), S_DQ_PCTCHANGE
        from eterminal.AIndexEODPrices
        where (trade_dt >= {begin_date} and trade_dt <= {end_date}) and S_INFO_WINDCODE = '000985.CSI'
        order by trade_dt
"""

SQL_STOCK_ALL = """
    select s_info_windcode, trade_dt, s_dq_close
    from eterminal.ashareeodprices
    where trade_dt >={} and trade_dt<={}
"""


def _update_rf_rate(rf_rate, trade_dt):
    rf_rate['rate'] = rf_rate['rate'] / 100 / 360
    rf_rate.rename({'rate': 'rf_rate'}, axis=1, inplace=True)
    rf_rate.set_index(['trade_dt'], inplace=True)
    date_range = pd.DataFrame(
        pd.date_range(start=str(rf_rate.index[0]), end=str(trade_dt[-1])).strftime('%Y%m%d')).astype(
        'int')
    rf_rate = rf_rate.reindex(
        index=date_range.iloc[:, 0]).fillna(method='ffill')
    rf_rate_all = rf_rate.reindex(index=trade_dt)
    return rf_rate_all.copy()


def decay_weight(decay_n=63, L=252):
    weight_out = 0.5 ** (np.arange(L - 1, -1, -1) / decay_n)
    weight_one_out = weight_out / weight_out.sum()
    weight_all = {'weight_out': weight_out, 'weight_one_out': weight_one_out}
    return weight_all


def deal_st(st_list, trade_dt, stock_list):
    st_list.columns = ['stk_id', 'list_date', 'delist_date']
    st_list['list_date'] = st_list['list_date'].astype(int)
    st_list['delist_date'] = st_list['delist_date'].fillna(trade_dt[-1])
    st_list['delist_date'] = st_list['delist_date'].astype(int)

    st_list['delist'] = 1
    if_delist = st_list.pivot_table(
        values='delist', index='delist_date', columns='stk_id')
    if_list = st_list.pivot_table(
        values='delist', index='list_date', columns='stk_id')
    if_delist = if_delist.reindex(index=trade_dt,
                                  columns=stock_list).fillna(method='bfill')  # 退市后为nan
    if_list = if_list.reindex(index=trade_dt,
                              columns=stock_list).fillna(method='ffill')  # 上市前为nan
    if_list_mat = (if_list * if_delist.values).reindex(index=trade_dt)
    if_list = if_list_mat.stack().to_frame('is_list').reset_index()
    return if_list_mat, if_list


def weight_std(values, weights):
    values = values.reshape(values.shape[0], )
    weights = weights.reshape(weights.shape[0], )
    # average = np.average(values, weights=weights)
    average = np.nansum(values * weights)
    # Fast and numerically precise:
    variance = np.nansum((values - average) ** 2 * weights)
    return math.sqrt(variance)


def cal_beta(stk_rt: np.array, market_ret: np.array, weight: np.array, rf=0.0):
    # 可以交易的股票才计算Beta.非停牌。
    # 如果回归样本点停牌日期的ewma权重超过0.5(近似最近58天都停牌)则也为nan
    # result_beta = {}

    stk_excess = stk_rt - rf  # 股票超额
    mkt_excess = market_ret - rf  # 市场超额
    data = pd.DataFrame(
        {'stk_excess': stk_excess, 'mkt_excess': mkt_excess, 'weight': weight})
    data.dropna(inplace=True)

    # 两种算法，结果相同
    X_i = data[['mkt_excess']]
    X_i.insert(0, column='constant', value=1)
    x_i = X_i.values
    y_i = data['stk_excess'].values.reshape(data.shape[0], 1)
    weight_diag = np.diag(data['weight'].values / sum(data['weight']))
    coef = np.linalg.inv(x_i.transpose().dot(weight_diag).dot(
        x_i)).dot(x_i.transpose().dot(weight_diag).dot(y_i))
    beta_i = coef[1, 0]
    res_i = y_i - x_i.dot(coef)

    hsigma_i = weight_std(res_i, (data['weight'] / sum(data['weight'])).values)
    return [beta_i, hsigma_i]


class BarraSubBeta(object):
    name = "s_style_barra_sub_beta"
    name_zh = "barra_子类_市场敏感度"

    # FIXME 注意！！注意！！ 如下变量，有默认值，可以直接使用
    # # 如果需要自定义格式，可以重写。否则可以直接使用，不用写到自己的代码里。
    # date_fmt = "%Y%m%d"
    # datetime_fmt = "%Y-%m-%d %H:%M:%S"
    # res_columns = ["s_info_windcode", "trade_dt", "value"]

    # 自定义的变量，

    def calc(self, date: datetime.datetime, **kwargs) -> pd.DataFrame:
        """
        必须实现这个方法。

        FIXME 看一下
        如果有其他的一些功能需要封装的。可以自定义函数。平台只会调用本函数（calc）
        :param date:
        :param kwargs:
        :return:
        """
        n = 21
        T = 12  # 252日动量
        L = 252
        decay_n = 63

        max_window_long = L  # 上一个交易日
        weight = decay_weight(decay_n, L)['weight_one_out']
        date_str = date.strftime(self.date_fmt)
        date_long = self.trading_date.get_offset_trading_date(
            date_str, - max_window_long - 1)
        date_long0 = self.trading_date.get_offset_trading_date(
            date_str, - max_window_long)  # 多取一天的数，用来算个股收益

        risk_free = SQL_RISKFREE.format(date_long, date_str)
        risk_free = self.db.read_sql(risk_free)
        risk_free.columns = ['trade_dt', 'rate']
        risk_free['trade_dt'] = risk_free['trade_dt'].astype(int)

        sql_hq = SQL_HQ.format(date_long0, date_str)
        df_hq = self.db.read_sql(sql_hq)
        df_hq.columns = ['trade_dt', 'ticker', 'cp', 'adj', 'amt']
        df_hq.eval('cp = cp * adj', inplace=True)
        df_hq['trade_dt'] = df_hq['trade_dt'].astype(int)
        amt = df_hq.pivot_table(
            values='amt', index='trade_dt', columns='ticker').sort_index().sort_index(axis=1)
        amt = amt.iloc[1:, :]
        trade_dt = amt.index.tolist()
        stock_list = amt.columns.tolist()

        st_list = self.db.read_sql(SQL_ST)
        if_list_mat, _ = deal_st(st_list, trade_dt, stock_list)
        suspend = amt < 10

        trade_dt = amt.index.tolist()
        rf_rate = _update_rf_rate(risk_free, trade_dt)
        stock_ret_i = df_hq.pivot_table(values='cp', index='trade_dt', columns='ticker').sort_index().sort_index(
            axis=1).pct_change()
        stock_ret_i = stock_ret_i.iloc[1:, :]
        stock_ret_i = stock_ret_i * \
            (~ (if_list_mat.values == 1)) * (~ suspend.values)

        # FIXME 需要实现
        sql_mkt_ret = SQL_MKT_RET.format(
            begin_date=date_long0, end_date=date_str)
        market_ret = self.db.read_sql(sql_mkt_ret)
        market_ret.columns = ['s_info_windcode', 'trade_dt', 'ret']
        market_ret['ret'] = market_ret['ret'] / 100
        market_ret = market_ret[['trade_dt', 'ret']].set_index('trade_dt')
        market_ret = market_ret.iloc[1:, :]

        market_ret_i = market_ret.loc[:, 'ret']
        rf_rate_i = rf_rate['rf_rate']  # rf_rate_all.loc[:, 'rf_rate']

        nan_ewma_i = (stock_ret_i.isnull() * weight.reshape(252, 1)).sum()
        stock_ret_i = stock_ret_i.loc[:, nan_ewma_i <= 0.5]
        beta_i = stock_ret_i.apply(lambda x: cal_beta(
            x, market_ret_i.values, weight, rf=rf_rate_i.values))
        beta_i.index = ['beta', 'hsigma']
        beta_i2 = beta_i.T.reset_index()
        beta_i2.columns = ["s_info_windcode", 'beta', 'hsigma']
        beta_i2['trade_dt'] = date_str

        df_result = beta_i2[["s_info_windcode", 'trade_dt', 'beta']].copy()
        df_result.rename(columns={'beta': 'value'}, inplace=True)
        res = df_result[self.res_columns]

        sql_stock_all = SQL_STOCK_ALL.format(date_str, date_str)
        df_data = self.db.read_sql(sql_stock_all)
        res_full = pd.DataFrame(
            np.zeros((df_data.shape[0], 3)), columns=self.res_columns)
        res_full[:] = np.nan
        res_full['s_info_windcode'] = df_data.iloc[:, 0].values
        res_full['trade_dt'] = date_str
        res_diff = np.setdiff1d(res_full.iloc[:, 0], res.iloc[:, 0]).tolist()
        res2 = pd.concat([res, res_full.set_index(
            's_info_windcode').loc[res_diff, :].reset_index()])
        return res2


if __name__ == '__main__':
    obj_ma5 = BarraSubBeta()
    yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
    yesterday = pd.to_datetime('20210222')
    df = obj_ma5.calc(yesterday)
    print(df.head(10))
    df.to_csv('debug_remote.csv')
