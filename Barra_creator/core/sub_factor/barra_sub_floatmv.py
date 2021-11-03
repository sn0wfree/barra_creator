# coding=utf-8
import pandas as pd
import numpy as np
import os
from Barra_creator.helper.barra_helper import BarraHelper
"""
$Ln(cap)$

Natural log of market cap,

Given by the logarithm of the total market capitalization of the firm

"""

class LnCap(object):
    def __init__(self, data):
        self.data = data
    @staticmethod
    def get_ln_cap(data):
        ln_cap = np.log(data)
        return ln_cap
    @classmethod
    def calculate(cls, data):
        ln_cap = cls.get_ln_cap(data=data)
        return ln_cap

    def calculate_and_save(self):
        ln_cap = self.calculate(data=self.data)
        return ln_cap

if __name__ == '__main__':
    pass