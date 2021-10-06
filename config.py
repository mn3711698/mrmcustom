# -*- coding: utf-8 -*-
##############################################################################
# Author：QQ173782910
##############################################################################
import redis
# 注意：
#    持仓方向为单向,不会设置杠杆
#    下边的dingding_token,wx_openid为空的话是不会发送钉钉消息和公众号消息

version_flag = '20211005'

key = ""  # 币安API的key
secret = ""  # 币安API的secret

dingding_token = ""  # 钉钉webhook的access_token
wx_openid = ""  # 关注简道斋后发送openid得到的那一串字符就是这个

tactics_flag = 0  # 0不发消息，1，2，3每次策略信号计算发一次
add_pos_flag = 0  # 加仓标识，为1开启，0关闭,加仓是当币在扛单中，再次遇到开仓信号就又开一次仓，这样会降低持仓均价，但爆仓风险更大
add_pos_amount = 0  # 加仓次数，0不限次数，其他的整数值为最大加仓次数，每个币的次数一样，不单独设置
symbol = "DOGEUSDT"  # 交易对
trading_size = 23  # 下单量,要注意价值大于5U
win_stop = 1.006  # 止盈参数
fill_amount = 0.985  # 补仓参数
add_size = 23  # 加仓下单量,要注意价值大于5U

redis_pool = redis.ConnectionPool(host='127.0.0.1', port='6379', db='0', password='')
redisc = redis.StrictRedis(connection_pool=redis_pool)
