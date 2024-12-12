from datetime import datetime

from scanner.marketdata.util import (
    calculate_annualized_return,
    calculate_percent_change,
    calculate_roll_price,
    format_contract_date,
    format_contract_strike,
    is_market_open,
)


def test_calculate_annualized_return():
    annualized_return = calculate_annualized_return(100, 0.45, 5)
    assert annualized_return == 32.85

    negative_bid_price = calculate_annualized_return(100, -0.45, 5)
    assert negative_bid_price == 0

    zero_dte = round(calculate_annualized_return(100, 0.45, 0), 2)
    assert zero_dte == 164.25


def test_calculate_percent_change():
    percent_change = calculate_percent_change(100, 105)
    assert percent_change == 5

    negative_percent_change = calculate_percent_change(100, 95)
    assert negative_percent_change == -5


def test_calculate_roll_price():
    roll_price = round(calculate_roll_price(0.45, 0.5), 2)
    assert roll_price == 0.05

    negative_roll_price = round(calculate_roll_price(0.5, 0.45), 2)
    assert negative_roll_price == -0.05


def test_format_contract_date():
    date = format_contract_date("2022-12-31")
    assert date == "221231"


def test_format_contract_strike():
    strike = format_contract_strike(100.50)
    assert strike == "00100500"

    strike = format_contract_strike(100.00)
    assert strike == "00100000"

    strike = format_contract_strike(1000.00)
    assert strike == "01000000"


def test_is_market_open():
    friday_during = datetime(2024, 12, 6, 14, 15)
    monday_before = datetime(2024, 12, 9, 8, 15)
    wednesday_after = datetime(2024, 12, 4, 16, 15)
    assert is_market_open(friday_during) == True
    assert is_market_open(monday_before) == False
    assert is_market_open(wednesday_after) == False
