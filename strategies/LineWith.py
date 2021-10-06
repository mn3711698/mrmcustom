# -*- coding: utf-8 -*-
##############################################################################
# Author：QQ173782910
##############################################################################

from datetime import datetime
from strategies.base import Base


class LineWith(Base):

    def on_pos_data(self, pos_dict):
        # 先判断是否有仓位，如果是多头的仓位， 然后检查下是多头还是空头，设置相应的止损的价格..
        current_pos = float(pos_dict['positionAmt'])
        self.unRealizedProfit = float(pos_dict['unRealizedProfit'])
        entryPrice = float(pos_dict['entryPrice'])
        if self.enter_price == 0 or self.enter_price != entryPrice:
            self.enter_price = entryPrice
            self.win_price = entryPrice * self.win_stop
            self.high_price = entryPrice
            self.low_price = entryPrice
            HYJ_jd_ss_dict = self.redisc.get(f'{self.symbol}_jdss')
            if HYJ_jd_ss_dict:
                jd_ss = int(HYJ_jd_ss_dict.decode("utf8"))  # 1停止
                if jd_ss == 1:
                    self.order_flag = entryPrice * self.fill_amount
                else:
                    self.order_flag = 0
            else:
                self.order_flag = 0

        if self.pos != 0:
            if self.unRealizedProfit > 0:
                self.maxunRealizedProfit = max(self.maxunRealizedProfit, self.unRealizedProfit)
            elif self.unRealizedProfit < 0:
                self.lowProfit = min(self.lowProfit, self.unRealizedProfit)

        if self.pos != current_pos:  # 检查仓位是否是一一样的.
            open_orders = self.broker.binance_http.get_open_orders(self.symbol)
            buy_flag = 0
            sell_flag = 0
            if isinstance(open_orders, list) and len(open_orders) > 0:
                for o in open_orders:
                    if o["side"] == 'BUY':  # 开多未成交
                        buy_flag = 1
                    elif o["side"] == 'SELL':  # 平仓未成交
                        sell_flag = 1
            if current_pos == 0 and buy_flag == 0:
                msg = f"仓位检查:{self.symbol},交易所帐户仓位为0，无持仓，系统仓位为:{self.pos},重置为0"
                self.dingding(msg, self.symbol)
                self.pos = 0
                return
            elif current_pos != 0 and sell_flag == 0:
                msg = f"仓位检查:{self.symbol},交易所仓位为:{current_pos},有持仓,系统仓位为:{self.pos},重置为:{current_pos}"
                self.dingding(msg, self.symbol)
                self.pos = current_pos
                return

    def on_ticker_data(self, ticker):
        self.ticker_data(ticker)

    def ticker_data(self, ticker):

        if self.symbol == ticker['symbol']:
            last_price = float(ticker['last_price'])  # 最新的价格.
            self.last_price = last_price

            if self.pos != 0:
                if self.high_price > 0:
                    self.high_price = max(self.high_price, self.last_price)
                if self.low_price > 0:
                    self.low_price = min(self.low_price, self.last_price)

            if self.pos == 0:  # 无持仓

                if self.order_flag > self.last_price > 0:
                    # 因为有一个止盈，在策略计算没有平仓信号的情况下平仓了，那遇到更低价的机会也不能错过
                    self.pos = self.round_to(self.trading_size, self.min_volume)
                    enter_price = self.ask
                    res_buy = self.buy(enter_price, abs(self.pos), mark=True)
                    self.enter_price = enter_price
                    self.high_price = enter_price
                    self.low_price = enter_price
                    self.maxunRealizedProfit = 0
                    self.unRealizedProfit = 0
                    self.lowProfit = 0
                    self.pos_update_time = datetime.now()
                    HYJ_jd_first = f"回补仓位,交易对:{self.symbol},仓位:{self.pos}"
                    HYJ_jd_tradeType = "开多"
                    HYJ_jd_curAmount = f"{enter_price}"
                    HYJ_jd_remark = f"回补仓位,留意仓位"
                    self.dingding(f"开多交易所返回:{res_buy}", self.symbol)
                    self.wx_send_msg(HYJ_jd_first, HYJ_jd_tradeType, HYJ_jd_curAmount, HYJ_jd_remark)

            elif self.pos > 0:  # 多单持仓

                enter_price = self.bid2  # +1
                Profit = self.round_to((enter_price - self.enter_price) * abs(self.pos), self.min_price)
                if last_price > self.win_price > 0:  # 策略未出来平仓信号，有利润要止盈
                    res_sell = self.sell(enter_price, abs(self.pos), mark=True)
                    HYJ_jd_first = "止盈平多:交易对:%s,最大亏损:%s,最大利润:%s,当前利润:%s,仓位:%s" % (
                        self.symbol, self.lowProfit, self.maxunRealizedProfit, self.unRealizedProfit, self.pos)
                    self.pos = 0
                    HYJ_jd_tradeType = "平多"
                    HYJ_jd_curAmount = "%s" % enter_price
                    HYJ_jd_remark = "止盈平多:%s,最新价:%s,最高价:%s,最低价:%s" % (
                        Profit, self.last_price, self.high_price, self.low_price)
                    self.enter_price = 0
                    self.high_price = 0
                    self.low_price = 0
                    self.maxunRealizedProfit = 0
                    self.unRealizedProfit = 0
                    self.lowProfit = 0
                    self.dingding(f"止盈平多,交易所返回:{res_sell}", self.symbol)
                    self.wx_send_msg(HYJ_jd_first, HYJ_jd_tradeType, HYJ_jd_curAmount, HYJ_jd_remark)
            elif self.pos < 0:  # 空单持仓
                enter_price = self.bid
                res_buy = self.buy(enter_price, abs(self.pos), mark=True)
                self.pos = 0
                self.dingding(f'平空返回:{res_buy}', self.symbol)
                HYJ_jd_first = f'平空,{self.symbol},last_price:{self.last_price}'
                HYJ_jd_tradeType = '平空'
                HYJ_jd_curAmount = f'{self.order_flag}'
                HYJ_jd_remark = f'平空,留意仓位, enter_price:{self.enter_price}'
                if "code" in res_buy:
                    HYJ_jd_remark += f'{res_buy}'
                self.enter_price = 0
                self.high_price = 0
                self.low_price = 0
                self.maxunRealizedProfit = 0
                self.unRealizedProfit = 0
                self.lowProfit = 0
                self.wx_send_msg(HYJ_jd_first, HYJ_jd_tradeType, HYJ_jd_curAmount, HYJ_jd_remark)

            if self.tactics_flag == 1:
                print(f'{self.symbol}', 'ws接收数据成功')
