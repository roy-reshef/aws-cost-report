def calc_percentage(val1, val2) -> str:
    """
    returns a percentage string representation of val1 from val2
    :param val1:
    :param val2:
    :return:
    """

    return "0%" if val2 == 0 else "{:.1f}%".format(100 - (100 * val2 / val1))
