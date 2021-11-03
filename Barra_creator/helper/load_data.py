# coding=utf-8
from dataclasses import dataclass
import datetime
from typing import Union
import numpy as np
import pandas as pd
import os
from Barra_creator.utils.chunk import chunk


def check_file_deco(func):
    def wrapper(*args, **kwargs):
        file_path = args[0]
        if os.path.isfile(file_path):
            return func(*args, **kwargs)
        else:
            raise ValueError(
                'Data file not found! please enter correct data_path')
    return wrapper


class DataLoad(object):
    def __new__(cls, config):
        if os.path.isfile(config):
            if config.endswith(('.csv', 'xlsx')):
                return DataLoaderCSV(config)
            elif config.endswith('.h5'):
                return DataLoaderH5(config)
            else:
                raise ValueError(
                    f'{config} not found! please enter correct config settings or data path')
        elif config.startswith('clickhouse://'):
            return DataLoaderSQLCH(config)
        else:
            raise ValueError(
                f'{config} not found! please enter correct config settings or data path')


class DataLoaderSQLCH(object):
    """
    Load data from ClickHouse database
    """

    def __init__(self, ch_config: str, **kwargs):

        from ClickSQL import BaseSingleFactorTableNode
        self.conn = BaseSingleFactorTableNode(ch_config)

        self.kwargs = kwargs

    def get(self, sql, *args, **kwargs):
        """
        Get data from ClickHouse
        :param table_name:
        :param kwargs:
        :return:
        """
        return self.conn(sql)

    def save(self, df: pd.DataFrame, db: str, table: str, *args, chunksize: int = 100000, **kwargs):
        self.conn.insert_df(df, db, table, chunksize)


class DataLoaderH5(object):
    """
    This class is used to load data from h5 file
    """

    def __init__(self, data_path):
        self.data_path = data_path

    def get(self, key, *args, **kwargs):
        """
        This function is used to get data from h5 file
        :return:
        """
        data = self._get_data(self.data_path, key)
        return data

    def save(self, key, data, *args, **kwargs):
        """
        This function is used to save data to h5 file
        """
        self._save_data(self.data_path, key, data)

    @staticmethod
    @check_file_deco
    def _get_data(data_path, key):
        """
        This function is used to get data from h5 file
        """
        data = pd.read_hdf(data_path, key)
        return data

    @staticmethod
    @check_file_deco
    def _save_data(data_path, data, key):
        """
        This function is used to save data to h5 file
        """
        data.to_hdf(data_path, key)


class DataLoaderCSV(object):
    def __init__(self, data_path):
        self.data_path = data_path

    def get(self, *args, **kwargs):
        """
        This function is used to get data from csv file
        :return:
        """
        data = self._get_data(self.data_path)
        return data

    def save(self, data, *args, **kwargs):
        self._save_data(self.data_path, data)

    @staticmethod
    @check_file_deco
    def _get_data(data_path):

        if data_path.endswith('.csv'):
            data = pd.read_csv(data_path)
        elif data_path.endswith('.xlsx'):
            data = pd.read_excel(data_path)
        else:
            raise ValueError(
                'Data file format not supported! accept csv or xlsx!')
        return data

    @staticmethod
    @check_file_deco
    def _save_data(output_path, data, data_format='csv'):
        if data_format == 'csv':
            data.to_csv(output_path, index=False)
        elif data_format == 'xlsx':
            data.to_excel(output_path, index=False)
        else:
            raise ValueError(
                'Data file format not supported! accept csv or xlsx!')


# @dataclass


class SQLSet(object):
    def __init__(self, configs_dict):
        """

        :param configs_dict:
        """
        self.configs_dict = configs_dict

    @staticmethod
    def _parse_dt_period(dt_period: Union[int, tuple]):
        if isinstance(dt_period, int):
            dt_from = dt_period
            dt_end = int(datetime.datetime.today().strftime("%Y%m%d"))

        elif isinstance(dt_period, tuple):
            dt_from, dt_end = min(dt_period), max(dt_period)
        else:
            raise ValueError(
                'dt_period is wrong type! which must be int or tuple of int')
        return dt_from, dt_end

    @staticmethod
    def general_simple_sql(config_kwargs):
        source = config_kwargs['source']
        select = config_kwargs['select']
        return [select], source

    @staticmethod
    def general_multi_period_sql(cls, dt_period: Union[int, tuple], config_kwargs, chunk_size=30, **others):

        sql = config_kwargs['select']
        source = config_kwargs['source']
        dt_from, dt_end = cls._parse_dt_period(dt_period)

        dt_from_dtformat = pd.to_datetime(str(dt_from), format='%Y%m%d')
        dt_end_dtformat = pd.to_datetime(str(dt_end), format='%Y%m%d')
        dt_range = pd.date_range(dt_from_dtformat, dt_end_dtformat)
        h = [sql.format(dt_from=i_list.min().strftime('%Y%m%d'), dt_end=i_list.max(
        ).strftime('%Y%m%d'), **others) for i_list in chunk(dt_range, chunk_size)]

        return h, source

    pass


if __name__ == '__main__':
    from Barra_creator.utils.parse_rfc_1738_args import parse_rfc1738_args
    path = 'F:\Data\data\AShareST.csv'
    # path = 'clickhouse://default:Imsn0wfree@47.104.186.157:8123/test.test'

    c = DataLoad(path)
    test = c.get()
    print(test)
    # c = parse_rfc1738_args(config_str)
