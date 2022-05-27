# coding=utf-8


class MetaRegister(object):
    """
    provide tasks schedule
    """

    @classmethod
    def call(cls, func_name: str, dt: str):
        return getattr(cls, func_name)(dt)

    pass


if __name__ == '__main__':
    pass
