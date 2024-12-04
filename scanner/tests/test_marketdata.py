from scanner.marketdata.util import calculate_annualized_return


def test_calculate_annualized_return():
    annualized_return = calculate_annualized_return(100, 0.45, 5)
    assert annualized_return == 32.85

    negative_bid_price = calculate_annualized_return(100, -0.45, 5)
    assert negative_bid_price == 0

    zero_dte = round(calculate_annualized_return(100, 0.45, 0), 2)
    assert zero_dte == 164.25
