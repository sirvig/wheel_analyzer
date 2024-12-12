import logging
import time

from scanner.marketdata.util import (
    calculate_annualized_return,
    calculate_percent_change,
    calculate_roll_price,
    format_contract_date,
    format_contract_strike,
    get_desired_delta,
    get_fridays,
    get_market_data,
)

logger = logging.getLogger(__name__)
DEBUG = False


def find_options(ticker, type, number_of_weeks=5, debug=False):
    # With a strike limit of 15 and checking 5 weeks out, we use 75 query tokens
    # If we scan 2 times an hour, the maximum number of stocks we can use in a day
    # (when the market is open - 7 hours) is 95.  Scan 4 times an hour and we can only
    # do 47 stocks.
    options = []

    ticker = ticker.upper()
    contract_type = type.lower()

    DEBUG = debug
    if DEBUG:
        logging.getLogger().setLevel(logging.DEBUG)

    list_fridays = get_fridays(number_of_weeks)
    for friday in list_fridays:
        options_chain_url = f"/options/chain/{ticker}/?weekly=true&side={contract_type}&range=otm&strikeLimit=15&expiration={friday}"
        tic = time.perf_counter()
        options_chain = get_market_data(options_chain_url)
        toc = time.perf_counter()
        logger.debug(f"Time to get options chain: {toc - tic:0.4f} seconds")

        if options_chain:
            message_printed = False
            length_of_chain = len(options_chain["optionSymbol"])

            # What are we getting back
            logger.debug(f"Calling {options_chain_url}")
            logger.debug(options_chain)

            for i in range(length_of_chain):
                strike_price = 0.01
                expiration_date = friday
                dte = 0
                bid_price = 0.01
                delta = 1
                implied_volatility = 0.01

                if options_chain["optionSymbol"][i]:
                    option = options_chain["optionSymbol"][i]
                if options_chain["strike"][i]:
                    strike_price = options_chain["strike"][i]
                if options_chain["dte"][i]:
                    dte = options_chain["dte"][i]
                if options_chain["bid"][i]:
                    bid_price = options_chain["bid"][i]
                if options_chain["delta"][i]:
                    delta = options_chain["delta"][i]
                if options_chain["iv"][i]:
                    implied_volatility = options_chain["iv"][i]
                if options_chain["underlyingPrice"][i]:
                    underlying_price = options_chain["underlyingPrice"][i]

                annualized_return = calculate_annualized_return(
                    strike_price, bid_price, dte
                )
                percent_change = calculate_percent_change(
                    strike_price, underlying_price
                )

                this_option = {
                    "date": expiration_date,
                    "strike": strike_price,
                    "change": percent_change,
                    "price": bid_price,
                    "delta": delta,
                    "annualized": annualized_return,
                    "iv": implied_volatility,
                }

                if contract_type == "put":
                    desired_delta = get_desired_delta("put", dte)
                    logger.debug(
                        f"Date: {expiration_date} annualized: {annualized_return} delta: {delta} desired: {desired_delta}"
                    )
                    if annualized_return >= 30 and delta >= -0.20:
                        options.append(this_option)
                else:
                    desired_delta = get_desired_delta("call", dte)
                    logger.debug(
                        f"C{strike_price} annualized return: {annualized_return} delta: {delta} desired: {desired_delta}"
                    )
                    if annualized_return >= 20 and delta <= desired_delta:
                        options.append(this_option)

            if DEBUG:
                logger.debug("Exiting early")
                return options

    return options


def find_rolls(
    ticker,
    type,
    current_strike,
    current_expiration,
    percentage=20,
    number_of_weeks=2,
    debug=False,
):
    options = []

    ticker = ticker.upper()
    contract_type = type.lower()
    current_strike = float(current_strike)

    DEBUG = debug
    if DEBUG:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get the current contract name
    if contract_type == "call":
        contract_type_short = "C"
    else:
        contract_type_short = "P"
    contract_name = f"{ticker}{format_contract_date(current_expiration)}{contract_type_short}{format_contract_strike(current_strike)}"
    logger.debug(f"Current contract: {contract_name}")

    # Get the ask price of the current contract
    quote_url = f"/options/quotes/{contract_name}/"
    tic = time.perf_counter()
    data = get_market_data(quote_url)
    toc = time.perf_counter()
    logger.debug(f"Time to get option quote: {toc - tic:0.4f} seconds")

    ask_price = ""
    if data:
        ask_price = data["ask"][0]
        logger.debug(f"Ask price: {ask_price}")

    # Find options to roll to
    list_fridays = get_fridays(number_of_weeks + 1)
    for friday in list_fridays:
        # only work with fridays in the future
        if friday <= current_expiration:
            continue

        options_chain_url = f"/options/chain/{ticker}/?weekly=true&side={contract_type}&range=all&strikeLimit=11&expiration={friday}"
        tic = time.perf_counter()
        options_chain = get_market_data(options_chain_url)
        toc = time.perf_counter()
        logger.debug(f"Time to get options chain: {toc - tic:0.4f} seconds")

        if options_chain:
            message_printed = False
            length_of_chain = len(options_chain["optionSymbol"])

            # What are we getting back
            logger.debug(f"Calling {options_chain_url}")
            logger.debug(options_chain)

            for i in range(length_of_chain):
                strike_price = 0.01
                expiration_date = friday
                dte = 0
                bid_price = 0.01
                delta = 1
                implied_volatility = 0.01

                if options_chain["optionSymbol"][i]:
                    option = options_chain["optionSymbol"][i]
                if options_chain["strike"][i]:
                    strike_price = options_chain["strike"][i]
                if options_chain["dte"][i]:
                    dte = options_chain["dte"][i]
                if options_chain["bid"][i]:
                    bid_price = options_chain["bid"][i]
                if options_chain["delta"][i]:
                    delta = options_chain["delta"][i]
                if options_chain["iv"][i]:
                    implied_volatility = options_chain["iv"][i]
                if options_chain["underlyingPrice"][i]:
                    underlying_price = options_chain["underlyingPrice"][i]

                roll_price = calculate_roll_price(ask_price, bid_price)
                annualized_return = calculate_annualized_return(
                    strike_price, roll_price, dte
                )
                percent_change = calculate_percent_change(
                    strike_price, underlying_price
                )

                this_option = {
                    "date": expiration_date,
                    "strike": strike_price,
                    "change": percent_change,
                    "price": bid_price,
                    "diff": roll_price,
                    "delta": delta,
                    "annualized": annualized_return,
                    "iv": implied_volatility,
                }

                if contract_type == "put":
                    # desired_delta = get_desired_delta('put', dte)
                    logger.debug(
                        f"   Date: {expiration_date} Strike: {strike_price} price: {bid_price} diff: {roll_price} annualized: {annualized_return} delta: {delta}"
                    )
                    if annualized_return >= percentage:
                        options.append(this_option)
                else:
                    desired_delta = get_desired_delta("call", dte)
                    logger.debug(
                        f"   Date: {expiration_date} Strike: {strike_price} price: {bid_price} diff: {roll_price} annualized: {annualized_return} delta: {delta} desired delta: {desired_delta}"
                    )
                    if annualized_return >= percentage:
                        options.append(this_option)

            if DEBUG:
                logger.debug("Exiting early")
                return options

    return options
