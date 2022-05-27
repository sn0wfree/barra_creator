# coding=utf-8
from Barra_creator.data.wind_data import BarraDataFromWind
from Barra_creator.error import TargetColumnsNotExistsError
from Barra_creator.register import MetaRegister


def target_check(code_col='stk_code', dt_col='trade_dt'):
    def deco(func):
        def _deco(*args, **kwargs):
            data = func(*args, **kwargs)
            cols = data.columns.tolist()
            for check_col in [code_col, dt_col]:
                if check_col not in cols:
                    raise TargetColumnsNotExistsError(
                        f"{check_col} is not in data columns! data columns have {','.join(cols)}")

            else:
                print(f"{','.join([code_col, dt_col])} both are in columns, target columns check pass")
            return data
        return _deco
    return deco


class Register(MetaRegister):
    """
    provide tasks schedule
    """

    @staticmethod
    @target_check(code_col='stk_code', dt_col='trade_dt')
    def barra_size(dt: str):
        from Barra_creator.factor.barra_size import LnCap
        # data
        stk_list, data = BarraDataFromWind.get_stk_all_floatmv(dt, ret_full_stk_list=True)
        # calculate
        c_data = LnCap.calculate(data, stk_list, dt, return_columns=False)
        return c_data


if __name__ == '__main__':
    dt = '2022-03-04'
    dta = Register.call('barra_size', dt)
    print(1)
    pass
