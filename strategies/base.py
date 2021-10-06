# -*- coding: utf-8 -*-
##############################################################################
# Author：QQ173782910
##############################################################################

import logging
import time
import traceback
from datetime import datetime
import pandas as pd
from utils.brokers import Broker
from getaway.binance_http import OrderSide, OrderType
from constant.constant import (EVENT_POS, EVENT_TICKER, EVENT_KLINE, EVENT_DEPTH)
from utils.event import Event
from utils.utility import round_to, save_json, load_json
from getaway.send_msg import dingding, bugcode, wx_send_msg
from config import (trading_size, tactics_flag, add_pos_amount, add_pos_flag, win_stop, fill_amount, add_size, redisc)
from RunUse import TradeRun


class Base:

    def __init__(self, broker, symbol: str, min_volume=0.001):
        self.broker: Broker = broker
        self.symbol = symbol
        self.round_to = round_to
        self.save_json = save_json
        self.load_json = load_json
        self.dingding = dingding
        self.bugcode = bugcode
        self.wx_send_msg = wx_send_msg
        self.TradeRun = TradeRun()
        self.open_orders = []
        self.pos = 0
        self.pos_flag = 0
        self.order_flag = 0
        self.high_price = 0.0
        self.low_price = 0.0
        self.enter_price = 0  # 开仓价
        self.ask2 = 0
        self.bid2 = 0
        self.bid = 0
        self.ask = 0
        self.min_price = 0.01
        self.win_price = 0.0
        self.trading_size = trading_size  # 开仓量
        self.add_pos_amount = add_pos_amount
        self.add_pos_flag = add_pos_flag
        self.win_stop = win_stop
        self.fill_amount = fill_amount
        self.add_size = add_size
        self.redisc = redisc
        self.tactics_flag = tactics_flag
        self.last_price = 0.0  # 从websocket推送得到lastprice
        self.min_volume = min_volume  # 0.001
        self.unRealizedProfit = 0  # 浮亏
        self.maxunRealizedProfit = 0  # 最高浮盈
        self.lowProfit = 0  # 最高浮损

        self.sold = 28
        self.bought = 75.5
        self.sold_bar = 10
        self.bought_bar = 10

        self.pos_dict = {}
        self.pos_update_time = datetime.now()  #
        self.logger = logging.getLogger('print')
        self.broker.event_engine.register(EVENT_POS, self.on_pos)
        self.broker.event_engine.register(EVENT_KLINE, self.on_kline)
        self.broker.event_engine.register(EVENT_TICKER, self.on_ticker)
        self.broker.event_engine.register(EVENT_DEPTH, self.on_depth)

    def on_pos(self, event: Event):
        try:
            if event.data['symbol'] == self.symbol:
                self.pos_dict = event.data['pos']
                self.on_pos_data(self.pos_dict)
        except:
            self.dingding("有故障，请联系作者共同处理", self.symbol)
            self.bugcode(traceback, 'mrmcustom_on_pos')

    def on_pos_data(self, pos_dict):
        pass

    def on_kline(self, event: Event):
        try:
            data = event.data['data']
            self.on_kline_data(data)
        except:
            self.dingding("有故障，请联系作者共同处理", self.symbol)
            self.bugcode(traceback, 'mrmcustom_on_kline')

    def on_ticker(self, event: Event):
        try:
            ticker = event.data['ticker']
            self.on_ticker_data(ticker)
        except:
            self.bugcode(traceback, 'mrmcustom_on_ticker')

    def on_ticker_data(self, ticker):
        pass

    def on_depth(self, event: Event):
        depth = event.data['depth']
        self.bid2 = depth['bid2']
        self.ask2 = depth['ask2']
        self.bid = depth['last_bid']
        self.ask = depth['last_ask']

    def getToday(self, formats=3):
        """返回今天的日期字串"""
        t = time.time()
        date_ary = time.localtime(t)
        if formats == 1:
            x = time.strftime("%Y%m%d", date_ary)
        elif formats == 2:
            x = time.strftime("%H:%M", date_ary)
        elif formats == 3:
            x = time.strftime("%Y/%m/%d", date_ary)
        elif formats == 4:
            x = time.strftime("%Y/%m/%d %H:%M", date_ary)
        elif formats == 5:
            x = time.strftime("%y%m%d", date_ary)
        elif formats == 6:
            x = time.strftime("%Y-%m-%d", date_ary)
        elif formats == 7:
            x = time.strftime("%Y/%m/%d %H:%M:%S", date_ary)
        elif formats == 8:
            x = time.strftime("%Y-%m-%d %H:%M", date_ary)
        elif formats == 9:
            x = time.strftime("%Y-%m-%d %H:%M:%S", date_ary)
        elif formats == 10:
            x = time.strftime("%Y年%m月%d日 %H:%M", date_ary)
        else:
            x = time.strftime("%Y-%m-%d %H:%M:%S", date_ary)
        return x

    def buy(self, price, amount, mark=False, stop=False):
        """
        做多
        :return:
        """
        return self.send_order(OrderSide.BUY, price, amount, mark, stop)

    def sell(self, price, amount, mark=False, stop=False):
        """
        做多平仓.
        :return:
        """
        return self.send_order(OrderSide.SELL, price, amount, mark, stop)

    def cancel_all_orders(self):
        for order in self.open_orders:
            self.broker.binance_http.cancel_order(self.symbol, order['orderId'])

    def cancel_order(self, orderid):
        return self.broker.binance_http.cancel_order(self.symbol, orderid)

    def send_order(self, side: OrderSide, price, amount, mark=False, stop=False):

        if stop:
            return self.broker.binance_http.place_order(self.symbol, side=side, order_type=OrderType.STOP,
                                                        quantity=amount, price=price, stop_price=price)
        elif mark:
            return self.broker.binance_http.place_order(self.symbol, side=side, order_type=OrderType.MARKET,
                                                        quantity=amount, price=price, stop_price=price)
        else:
            return self.broker.binance_http.place_order(self.symbol, side=side, order_type=OrderType.LIMIT,
                                                        quantity=amount, price=price)

    def dataframe_mr(self, data):

        df = pd.DataFrame(data, columns={"open_time": 0, "open": 1, "high": 2, "low": 3, "close": 4, "volume": 5,
                                         "close_time": 6, "trade_money": 7, "trade_count": 8, "buy_volume": 9,
                                         "sell_volume": 10, "other": 11})

        df = df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]

        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms') + pd.Timedelta(hours=8)
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms') + pd.Timedelta(hours=8)
        return df

    def on_kline_data(self, data):
        now_data = data[:-1]
        df = self.dataframe_mr(now_data)  # [::-1]
        buy_signal, sell_signal = self.TradeRun.calculate_data(self.sold, self.bought,
                                                               self.sold_bar, self.bought_bar, df)

        if buy_signal:
            if self.pos > 0:
                if self.add_pos_flag == 0:
                    msg = f"多单信号,持仓中,机器人运行中,如需开启加仓，请进行配置"
                    self.dingding(msg, self.symbol)
                    HYJ_jd_first = f'{self.symbol},开仓信号,持仓中'
                    HYJ_jd_tradeType = '持仓'
                    HYJ_jd_curAmount = f'{self.enter_price}'
                    HYJ_jd_remark = f'开仓信号，当前仓位,{self.pos}'
                    self.wx_send_msg(HYJ_jd_first, HYJ_jd_tradeType, HYJ_jd_curAmount, HYJ_jd_remark)
                elif self.add_pos_flag == 1:
                    add_pos_dicts = self.redisc.get(f'{self.symbol}_addpos')
                    if add_pos_dicts:
                        addpos = int(add_pos_dicts.decode("utf8"))
                        if 0 < addpos <= self.add_pos_amount:
                            eprice = self.ask
                            tradingsize = self.add_size
                            res_buy = self.buy(eprice, tradingsize, mark=True)
                            self.dingding(f'加仓返回:{res_buy}', self.symbol)
                            HYJ_jd_first = f'{self.symbol},开仓信号'
                            HYJ_jd_tradeType = '加仓'
                            HYJ_jd_curAmount = f'{eprice}'
                            HYJ_jd_remark = f'所加仓位:{tradingsize}'
                            if "code" in res_buy:
                                HYJ_jd_remark += f'{res_buy}'
                            else:
                                self.redisc.set(f'{self.symbol}_addpos', addpos + 1)
                            self.wx_send_msg(HYJ_jd_first, HYJ_jd_tradeType, HYJ_jd_curAmount, HYJ_jd_remark)
                else:
                    msg = f"加仓参数配置有误"
                    self.dingding(msg, self.symbol)
                return
            self.redisc.set(f'{self.symbol}_jdss', 1)
            enter_price = self.ask
            self.pos = self.round_to(self.trading_size, self.min_volume)
            res_buy = self.buy(enter_price, abs(self.pos), mark=True)
            self.order_flag = enter_price * self.fill_amount
            self.enter_price = enter_price
            self.high_price = enter_price
            self.low_price = enter_price
            self.maxunRealizedProfit = 0
            self.unRealizedProfit = 0
            self.lowProfit = 0
            self.pos_update_time = datetime.now()
            HYJ_jd_first = f"交易对:{self.symbol},仓位:{self.pos}"
            HYJ_jd_tradeType = "开多"
            HYJ_jd_curAmount = f"{enter_price}"
            HYJ_jd_remark = f"最新价:{self.last_price}"
            self.dingding(f"开多交易所返回:{res_buy}", self.symbol)
            self.wx_send_msg(HYJ_jd_first, HYJ_jd_tradeType, HYJ_jd_curAmount, HYJ_jd_remark)
        if sell_signal:
            self.redisc.set(f'{self.symbol}_jdss', 0)
            if self.pos == 0:
                msg = f"无持仓，平多机器人运行中"
                self.dingding(msg, self.symbol)
                HYJ_jd_first = f'{self.symbol}平仓信号，无持仓'
                HYJ_jd_tradeType = '空仓'
                HYJ_jd_curAmount = f'{self.last_price}'
                HYJ_jd_remark = f'平仓信号，无持仓,{self.pos}'
                self.wx_send_msg(HYJ_jd_first, HYJ_jd_tradeType, HYJ_jd_curAmount, HYJ_jd_remark)
                return
            enter_price = self.bid2
            Profit = self.round_to((enter_price - self.enter_price) * abs(self.pos), self.min_price)
            res_sell = self.sell(enter_price, abs(self.pos), mark=True)
            HYJ_jd_first = "平仓信号:交易对:%s,最大亏损:%s,最大利润:%s,当前利润:%s,仓位:%s" % (
                self.symbol, self.lowProfit, self.maxunRealizedProfit, self.unRealizedProfit, self.pos)
            self.pos = 0
            HYJ_jd_tradeType = "平多"
            HYJ_jd_curAmount = "%s" % enter_price
            HYJ_jd_remark = "平多:%s,最新价:%s,最高价:%s,最低价:%s" % (
                Profit, self.last_price, self.high_price, self.low_price)
            self.enter_price = 0
            self.high_price = 0
            self.low_price = 0
            self.maxunRealizedProfit = 0
            self.unRealizedProfit = 0
            self.lowProfit = 0
            self.dingding(f"平多,交易所返回:{res_sell}", self.symbol)
            self.wx_send_msg(HYJ_jd_first, HYJ_jd_tradeType, HYJ_jd_curAmount, HYJ_jd_remark)

        if not buy_signal and not sell_signal and self.tactics_flag == 3:
            msg = f"机器人运行中,持仓:{self.pos}"
            self.dingding(msg, self.symbol)
