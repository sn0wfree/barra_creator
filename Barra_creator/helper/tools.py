# coding=utf-8
import numpy as np
import pandas as pd


def decay_weight(decay_n=63, L=252):
    """

    :param decay_n:
    :param L:
    :return:
    """
    weight_out = 0.5 ** (np.arange(L - 1, -1, -1) / decay_n)
    weight_one_out = weight_out / weight_out.sum()
    weight_all = {'weight_out': weight_out, 'weight_one_out': weight_one_out}
    return weight_all


def normmat(data: pd.DataFrame, trade_dt: pd.DataFrame, stklist: pd.DataFrame, index_name: str = 'trade_dt',
            column_name: str = 'stk_id', value_name: str = 'close'):
    """
    转换成标准矩阵格式
    :param data:
    :param index_name:
    :param column_name:
    :param value_name:
    :return:
    """
    # df = data.pivot(values=value_name, index=index_name, columns=column_name)
    df = data.pivot_table(
        values=value_name, index=index_name, columns=column_name)
    df = df.reindex(index=trade_dt[index_name].to_list(), columns=stklist[column_name].to_list())
    return df


def mad(values: np.ndarray, n: int = 5, axis: int = 1):
    """
    中位数去极值
    :param values:
    :param n:
    :return:
    """
    if axis == 1:
        l = values.shape[0]
    elif axis == 0:
        l = values.shape[1]

    d_m = np.nanmedian(values, axis=axis).reshape(l, 1)  # 中位值
    d_mad = np.nanmedian(np.abs(values - d_m), axis=axis).reshape(l, 1)  # 偏离中位值的中位值
    data = np.where(values > (d_m + n * d_mad), d_m + n * d_mad,
                    np.where(values < (d_m - n * d_mad), d_m - n * d_mad, values))
    return data


def _preprocess(float_mv, factor_i_mat, ind_mat_list):
    """
    去极值、补缺值、标准化
    :param factor_i_mat:
    :param ind_mat:
    :return:
    """
    # 1.去极值
    factor_i_mad = pd.DataFrame(
        mad(factor_i_mat.values), index=factor_i_mat.index, columns=factor_i_mat.columns)
    if factor_i_mad.columns.name is None:
        factor_i_mad.columns.name = 'stk_id'
    # 2.补缺失值 -- 行业均值填充
    factor_i_list = factor_i_mad.stack().to_frame('data').reset_index()
    factor_i_ind = pd.merge(factor_i_list, ind_mat_list, left_on=['trade_dt', 'stk_id'],
                            right_on=['trade_dt', 'stk_id'], how='left')
    factor_i_ind['data'] = factor_i_ind['data'].loc[np.isfinite(
        factor_i_ind['data'].values)]  # 剔除infinite
    factor_i_ind['data_ind_mean'] = factor_i_ind.groupby(['trade_dt', 'ind_code_order'])['data'].transform(
        np.nanmean)
    factor_i_ind['data_filled'] = factor_i_ind['data'].fillna(
        factor_i_ind['data_ind_mean'])
    # 因子值和行业编号都为nan的剔除
    factor_i_ind = factor_i_ind[~(
            factor_i_ind['data'].isnull() & factor_i_ind['ind_code_order'].isnull())]
    # 3. 标准化
    mv = float_mv
    factor_i_ind = pd.merge(factor_i_ind, mv, left_on=['trade_dt', 'stk_id'],
                            right_on=['trade_dt', 'stk_id'], how='left')
    factor_i_ind['float_mv'] = factor_i_ind['float_mv'].where(
        factor_i_ind['data_filled'].notnull())
    factor_i_ind['mv_weight'] = factor_i_ind.groupby(
        'trade_dt')['float_mv'].transform(lambda x: x / x.sum())
    factor_i_ind['data_filled_weighted'] = factor_i_ind['data_filled'] * \
                                           factor_i_ind['mv_weight']
    factor_i_ind['data_weighted_mean'] = factor_i_ind.groupby('trade_dt')['data_filled_weighted'].transform(
        np.nansum)
    factor_i_ind['data_std'] = factor_i_ind.groupby('trade_dt')['data_filled'].transform(
        lambda x: np.std(x, ddof=1))
    factor_i_ind['data_norm'] = (factor_i_ind['data_filled'] - factor_i_ind['data_weighted_mean']) / factor_i_ind[
        'data_std']
    return factor_i_ind[['stk_id', 'trade_dt', 'data_norm']]


if __name__ == '__main__':
    pass
