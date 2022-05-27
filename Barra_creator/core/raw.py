# coding=utf-8
import pandas as pd
import numpy as np


class MetaFactorCreator(object):
    """
    provide factor creator
    """

    def __init__(self, ):
        pass

    def __call__(self, *args,**kwargs):

        dta = self.calculate(*args,**kwargs)
        return dta


if __name__ == '__main__':
    pass
