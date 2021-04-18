import argparse
from oandapyV20 import API
from typing import List
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.forexlabs as labs
from oandapyV20.exceptions import V20Error
from gamestonk_terminal import config_terminal as cfg
from gamestonk_terminal import config_plot as cfgPlot
from gamestonk_terminal import feature_flags as gtff
from gamestonk_terminal.helper_funcs import parse_known_args_and_warn, plot_autoscale
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from datetime import datetime


client = API(access_token=cfg.OANDA_TOKEN, environment="live")
account = cfg.OANDA_ACCOUNT


def get_fx_price(accountID, instrument):
    try:
        parameters = {"instruments": instrument}
        request = pricing.PricingInfo(accountID=accountID, params=parameters)
        response = client.request(request)
        bid = response["prices"][0]["bids"][0]["price"]
        ask = response["prices"][0]["asks"][0]["price"]
        print(instrument + " Bid: " + bid)
        print(instrument + " Ask: " + ask)
    except V20Error as e:
        print(e)


def get_account_summary(accountID):
    try:
        request = accounts.AccountSummary(accountID=accountID)
        response = client.request(request)
        balance = response["account"]["balance"]
        margin_available = response["account"]["marginAvailable"]
        margin_closeout = response["account"]["marginCloseoutNAV"]
        margin_closeout_percent = response["account"]["marginCloseoutPercent"]
        margin_closeout_position_value = response["account"][
            "marginCloseoutPositionValue"
        ]
        margin_used = response["account"]["marginUsed"]
        net_asset_value = response["account"]["NAV"]
        open_trade_count = response["account"]["openTradeCount"]
        total_pl = response["account"]["pl"]
        unrealized_pl = response["account"]["unrealizedPL"]

        print(f"Balance: {balance}")
        print(f"NAV: {net_asset_value}")
        print(f"Unrealized P/L:  {unrealized_pl}")
        print(f"Total P/L: {total_pl}")
        print(f"Open Trade Count: {open_trade_count}")
        print(f"Margin Available:  ${margin_available}")
        print(f"Margin Used: ${margin_used}")
        print(f"Margin Closeout {margin_closeout}")
        print(f"Margin Closeout Percent: {margin_closeout_percent}")
        print(f"Margin Closeout Position Value: {margin_closeout_position_value}")
    except V20Error as e:
        print(e)


def list_orders(accountID, other_args: List[str]):
    parser = argparse.ArgumentParser(
        add_help=False,
        prog="listorders",
        description="List order history",
    )
    parser.add_argument(
        "-s", "--state", dest="state", action="store", default="ALL", required=False
    )
    parser.add_argument(
        "-c", "--count", dest="count", action="store", default=50, required=False
    )
    ns_parser = parse_known_args_and_warn(parser, other_args)
    if not ns_parser:
        return

    parameters = {}
    parameters["state"] = ns_parser.state
    parameters["count"] = ns_parser.count

    try:
        request = orders.OrderList(accountID, parameters)
        response = client.request(request)
        df = pd.DataFrame.from_dict(response["orders"])
        df = df[["id", "instrument", "units", "price", "state", "type"]]
        print(df)
    except V20Error as e:
        print(e)


def get_order_book(instrument):
    parameters = {"bucketWidth": "1"}
    try:
        request = instruments.InstrumentsOrderBook(
            instrument=instrument, params=parameters
        )
        response = client.request(request)
        df = pd.DataFrame.from_dict(response["orderBook"]["buckets"])
        pd.set_option("display.max_rows", None)
        df = df.take(range(527, 727, 1))
        book_plot(df, instrument, "Order Book")
    except V20Error as e:
        print(e)


def get_position_book(instrument):
    try:
        request = instruments.InstrumentsPositionBook(instrument=instrument)
        response = client.request(request)
        df = pd.DataFrame.from_dict(response["positionBook"]["buckets"])
        pd.set_option("display.max_rows", None)
        df = df.take(range(219, 415, 1))
        book_plot(df, instrument, "Position Book")
    except V20Error as e:
        print(e)


def create_order(accountID, instrument, other_args: List[str]):
    parser = argparse.ArgumentParser(
        add_help=False,
        prog="create_order",
        description="Create order",
    )
    parser.add_argument(
        "-u",
        "--unit",
        dest="units",
        action="store",
        type=int,
        default=0,
        required=True,
    )
    parser.add_argument(
        "-p",
        "--price",
        dest="price",
        action="store",
        type=float,
        required=True,
    )

    ns_parser = parse_known_args_and_warn(parser, other_args)
    if not ns_parser:
        return

    data = {
        "order": {
            "price": ns_parser.price,
            "instrument": instrument,
            "units": ns_parser.units,
            "type": "LIMIT",
            "timeInForce": "GTC",
            "positionFill": "DEFAULT",
        }
    }
    try:
        request = orders.OrderCreate(accountID, data)
        response = client.request(request)
        print(response)
    except V20Error as e:
        print(e)


def cancel_pending_order(accountID, other_args: List[str]):
    parser = argparse.ArgumentParser(
        add_help=False,
        prog="cancelpendingorder",
        description="Cancel Pending Order",
    )
    parser.add_argument(
        "-i",
        "--id",
        dest="orderID",
        action="store",
        type=str,
        required=True,
    )
    ns_parser = parse_known_args_and_warn(parser, other_args)
    if not ns_parser:
        return
    try:
        request = orders.OrderCancel(accountID, ns_parser.orderID)
        client.request(request)
    except V20Error as e:
        print(e)


def get_pending_orders(accountID):
    try:
        request = orders.OrdersPending(accountID)
        response = client.request(request)
        for i in range(len(response["orders"])):
            try:
                order_id = response["orders"][i]["id"]
                instrument = response["orders"][i]["instrument"]
                price = response["orders"][i]["price"]
                units = response["orders"][i]["units"]
                create_time = response["orders"][i]["createTime"]
                time_in_force = response["orders"][i]["timeInForce"]
                print(f"Order ID: {order_id}")
                print(f"Instrument: {instrument}")
                print(f"Price: {price}")
                print(f"Units: {units}")
                print(f"Time created: {create_time}")
                print(f"Time in force: {time_in_force}")
                print("-" * 30)
            except IndexError:
                break
    except V20Error as e:
        print(e)


def get_open_positions(accountID):
    try:
        request = positions.OpenPositions(accountID)
        response = client.request(request)
        for i in range(len(response["positions"])):
            instrument = response["positions"][i]["instrument"]
            long_units = response["positions"][i]["long"]["units"]
            long_pl = response["positions"][i]["long"]["pl"]
            long_upl = response["positions"][i]["long"]["unrealizedPL"]
            short_units = response["positions"][i]["short"]["units"]
            short_pl = response["positions"][i]["short"]["pl"]
            short_upl = response["positions"][i]["short"]["unrealizedPL"]
            print(f"Instrument: {instrument}\n")
            print(f"Long Units: {long_units}")
            print(f"Total Long P/L: {long_pl}")
            print(f"Long Unrealized P/L: {long_upl}\n")
            print(f"Short Units: {short_units}")
            print(f"Total Short P/L: {short_pl}")
            print(f"Short Unrealized P/L: {short_upl}")
            print("-" * 30 + "\n")
    except V20Error as e:
        print(e)


def get_open_trades(accountID):
    try:
        request = trades.OpenTrades(accountID)
        response = client.request(request)
        df = pd.DataFrame.from_dict(response["trades"])
        df = df[
            [
                "id",
                "instrument",
                "initialUnits",
                "currentUnits",
                "price",
                "unrealizedPL",
            ]
        ]
        df = df.rename(
            columns={
                "id": "ID",
                "instrument": "Instrument",
                "initialUnits": "Initial Units",
                "currentUnits": "Current Units",
                "price": "Entry Price",
            }
        )
        print(df)
    except V20Error as e:
        print(e)


def close_trade(accountID, other_args: List[str]):
    parser = argparse.ArgumentParser(
        add_help=False,
        prog="close_trade",
        description="close a trade",
    )
    parser.add_argument(
        "-i",
        "--id",
        dest="orderID",
        action="store",
        type=str,
        required=True,
    )
    parser.add_argument(
        "-u",
        "--units",
        dest="units",
        action="store",
        type=str,
        required=False,
    )
    ns_parser = parse_known_args_and_warn(parser, other_args)
    if not ns_parser:
        return
    data = {
        "units": ns_parser.units,
    }
    try:
        request = trades.TradeClose(accountID, ns_parser.orderID, data)
        response = client.request(request)
        print(response)
    except V20Error as e:
        print(e)


def show_candles(accountID, instrument, other_args: List[str]):
    parser = argparse.ArgumentParser(
        add_help=False,
        prog="show_candles",
        description="Display Candle Data",
    )
    parser.add_argument(
        "-c",
        "--count",
        dest="candlecount",
        action="store",
        default=180,
    )
    parser.add_argument(
        "-g",
        "--granularity",
        dest="granularity",
        action="store",
        default="D",
    )
    parser.add_argument("-a", "--ad", dest="ad", action="store_true")
    parser.add_argument("-A", "--adx", dest="adx", action="store_true")
    parser.add_argument("-b", "--bollinger-bands", dest="bbands", action="store_true")
    parser.add_argument("-C", "--cci", dest="cci", action="store_true")
    parser.add_argument("-e", "--ema", dest="ema", action="store_true")
    parser.add_argument("-f", "--fwma", dest="fwma", action="store_true")
    parser.add_argument("-m", "--macd", dest="macd", action="store_true")
    parser.add_argument("-o", "--obv", dest="obv", action="store_true")
    parser.add_argument("-r", "--rsi", dest="rsi", action="store_true")
    parser.add_argument("-R", "--aroon", dest="aroon", action="store_true")
    parser.add_argument("-s", "--sma", dest="sma", action="store_true")
    parser.add_argument("-S", "--stoch", dest="stoch", action="store_true")
    parser.add_argument("-v", "--vwap", dest="vwap", action="store_true")

    ns_parser = parse_known_args_and_warn(parser, other_args)
    if not ns_parser:
        return

    parameters = {}
    parameters["granularity"] = ns_parser.granularity
    parameters["count"] = ns_parser.candlecount
    try:
        request = instruments.InstrumentsCandles(instrument, params=parameters)
        response = client.request(request)
        process_candle_response(response)
        oanda_fix_date(".temp_candles.csv")
        df = pd.read_csv(".candles.csv", index_col=0)
        df.index = pd.to_datetime(df.index)
        df.columns = ["Open", "High", "Low", "Close", "Volume"]

        plots_to_add = []

        if ns_parser.ad:
            ad = ta.ad(df["High"], df["Low"], df["Close"], df["Volume"])
            ad_plot = mpf.make_addplot(ad, panel=3)
            plots_to_add.append(ad_plot)
        if ns_parser.adx:
            adx = ta.adx(df["High"], df["Low"], df["Close"])
            adx_plot = mpf.make_addplot(adx, panel=3)
            plots_to_add.append(adx_plot)
        if ns_parser.aroon:
            aroon = ta.aroon(df["High"], df["Low"])
            aroon_plot = mpf.make_addplot(aroon, panel=3)
            plots_to_add.append(aroon_plot)
        if ns_parser.cci:
            cci = ta.cci(df["High"], df["Low"], df["Close"], length=20)
            cci_plot = mpf.make_addplot(cci, panel=3)
            plots_to_add.append(cci_plot)
        if ns_parser.bbands:
            bbands = ta.bbands(df["Close"])
            bbands = bbands.drop("BBB_5_2.0", axis=1)
            bbands_plot = mpf.make_addplot(bbands, panel=0)
            plots_to_add.append(bbands_plot)
        if ns_parser.ema:
            ema = ta.ema(df["Close"])
            ema_plot = mpf.make_addplot(ema, panel=0)
            plots_to_add.append(ema_plot)
        if ns_parser.fwma:
            fwma = ta.fwma(df["Close"])
            fwma_plot = mpf.make_addplot(fwma, panel=0)
            plots_to_add.append(fwma_plot)
        if ns_parser.rsi:
            rsi = ta.rsi(df["Close"], length=14)
            rsi_plot = mpf.make_addplot(rsi, panel=2)
            plots_to_add.append(rsi_plot)
        if ns_parser.macd:
            macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
            macd_plot = mpf.make_addplot(macd, panel=3)
            plots_to_add.append(macd_plot)
        if ns_parser.obv:
            obv = ta.obv(df["Close"], df["Volume"])
            obv_plot = mpf.make_addplot(obv, panel=3)
            plots_to_add.append(obv_plot)
        if ns_parser.sma:
            sma = ta.sma(df["Close"])
            sma_plot = mpf.make_addplot(sma, panel=0)
            plots_to_add.append(sma_plot)
        if ns_parser.stoch:
            stoch = ta.stoch(df["High"], df["Low"], df["Close"])
            stoch_plot = mpf.make_addplot(stoch, panel=0)
            plots_to_add.append(stoch_plot)
        if ns_parser.vwap:
            vwap = ta.vwap(df["High"], df["Low"], df["Close"], df["Volume"])
            vwap_plot = mpf.make_addplot(vwap, panel=0)
            plots_to_add.append(vwap_plot)

        if gtff.USE_ION:
            plt.ion()

        mpf.plot(
            df,
            type="candle",
            style="charles",
            volume=True,
            title=f"{instrument} {ns_parser.granularity}",
            addplot=plots_to_add,
        )
    except Exception as e:
        print(e)
    except NameError as e:
        print(e)


def process_candle_response(response):
    with open(".temp_candles.csv", "w") as out:
        for i in range(len(response["candles"])):
            time = response["candles"][i]["time"]
            volume = response["candles"][i]["volume"]
            o = response["candles"][i]["mid"]["o"]
            h = response["candles"][i]["mid"]["h"]
            low = response["candles"][i]["mid"]["l"]
            c = response["candles"][i]["mid"]["c"]
            out.write(
                str(time)
                + ","
                + str(o)
                + ","
                + str(h)
                + ","
                + str(low)
                + ","
                + str(c)
                + ","
                + str(volume)
                + "\n"
            )


def oanda_fix_date(file):
    with open(file) as candle_file:
        lines = candle_file.readlines()
        with open(".candles.csv", "w") as out:
            out.write("Datetime, Open, High, Low, Close, Volume\n")
        for line in lines:
            with open(".candles.csv", "a") as output:
                output.write(line[:10] + " " + line[11:19] + line[30:])


def calendar(instrument, other_args: List[str]):
    parser = argparse.ArgumentParser(
        add_help=False,
        prog="calendar",
        description="Show Calendar Data",
    )
    parser.add_argument(
        "-d",
        "--days",
        dest="days",
        action="store",
        type=int,
        default=7,
        required=False,
    )
    ns_parser = parse_known_args_and_warn(parser, other_args)
    if not ns_parser:
        return

    parameters = {"instrument": instrument, "period": str(ns_parser.days * 86400 * -1)}
    try:
        request = labs.Calendar(params=parameters)
        response = client.request(request)
        for i in range(len(response)):
            if "title" in response[i]:
                title = response[i]["title"]
                print(f"Title: {title}")
            if "timestamp" in response[i]:
                timestamp = response[i]["timestamp"]
                time = datetime.fromtimestamp(timestamp)
                print(f"Time: {time}")
            if "impact" in response[i]:
                impact = response[i]["impact"]
                print(f"Impact: {impact}")
            if "forecast" in response[i]:
                forecast = response[i]["forecast"]
                unit = response[i]["unit"]
                if unit != "Index":
                    print(f"Forecast: {forecast}{unit}")
                else:
                    print(f"Forecast: {forecast}")
            if "market" in response[i]:
                market = response[i]["market"]
                unit = response[i]["unit"]
                if unit != "Index":
                    print(f"Market Forecast: {market}{unit}")
                else:
                    print(f"Market Forecast: {market}")
            if "currency" in response[i]:
                currency = response[i]["currency"]
                print(f"Currency: {currency}")
            if "region" in response[i]:
                region = response[i]["region"]
                print(f"Region: {region}")
            if "actual" in response[i]:
                actual = response[i]["actual"]
                unit = response[i]["unit"]
                if unit != "Index":
                    print(f"Actual: {actual}{unit}")
                else:
                    print(f"Actual: {actual}")
            if "previous" in response[i]:
                previous = response[i]["previous"]
                unit = response[i]["unit"]
                if unit != "Index":
                    print(f"Previous: {previous}{unit}")
                else:
                    print(f"Previous: {previous}")
            print("-" * 30)
    except V20Error as e:
        print(e)


def load(other_args: List[str]):
    """Load a forex instrument to use"""
    parser = argparse.ArgumentParser(
        add_help=False,
        prog="Forex",
        description="Forex using oanda",
    )

    parser.add_argument(
        "-i",
        "--instrument",
        required=True,
        type=str,
        dest="instrument",
        help="Instrument to use for function calls",
    )

    try:
        if other_args:
            if "-" not in other_args[0]:
                other_args.insert(0, "-i")

        ns_parser = parse_known_args_and_warn(parser, other_args)

        if not ns_parser:
            return
        return ns_parser.instrument.upper()
    except Exception as e:
        print(e)


def book_plot(df, instrument, book_type):
    _, ax = plt.subplots(figsize=plot_autoscale(), dpi=cfgPlot.PLOT_DPI)
    df = df.apply(pd.to_numeric)
    df["shortCountPercent"] = df["shortCountPercent"] * -1
    axis_origin = max(
        abs(max(df["longCountPercent"])), abs(max(df["shortCountPercent"]))
    )
    ax.set_xlim(-axis_origin, +axis_origin)

    sns.set_style(style="darkgrid")

    sns.barplot(
        x="longCountPercent",
        y="price",
        data=df,
        label="Count Percent",
        color="green",
        orient="h",
    )

    sns.barplot(
        x="shortCountPercent",
        y="price",
        data=df,
        label="Prices",
        color="red",
        orient="h",
    )

    ax.invert_yaxis()
    plt.title(f"{instrument} {book_type}")
    plt.xlabel("Count Percent")
    plt.ylabel("Price")
    sns.despine(left=True, bottom=True)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(5))
    if gtff.USE_ION:
        plt.ion()
    plt.show()
