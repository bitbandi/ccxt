# -*- coding: utf-8 -*-

# PLEASE DO NOT EDIT THIS FILE, IT IS GENERATED AND WILL BE OVERWRITTEN:
# https://github.com/ccxt/ccxt/blob/master/CONTRIBUTING.md#how-to-contribute-code

from ccxt.pro.base.exchange import Exchange
import ccxt.async_support
from ccxt.pro.base.cache import ArrayCache, ArrayCacheBySymbolById, ArrayCacheByTimestamp
import hashlib
from ccxt.base.errors import AuthenticationError
from ccxt.base.errors import ArgumentsRequired


class bitmart(Exchange, ccxt.async_support.bitmart):

    def describe(self):
        return self.deep_extend(super(bitmart, self).describe(), {
            'has': {
                'ws': True,
                'watchTicker': True,
                'watchOrderBook': True,
                'watchOrders': True,
                'watchTrades': True,
                'watchOHLCV': True,
            },
            'urls': {
                'api': {
                    'ws': {
                        'public': 'wss://ws-manager-compress.{hostname}/api?protocol=1.1',
                        'private': 'wss://ws-manager-compress.{hostname}/user?protocol=1.1',
                    },
                },
            },
            'options': {
                'defaultType': 'spot',
                'watchOrderBook': {
                    'depth': 'depth5',  # depth5, depth400
                },
                'ws': {
                    'inflate': True,
                },
                'timeframes': {
                    '1m': '1m',
                    '3m': '3m',
                    '5m': '5m',
                    '15m': '15m',
                    '30m': '30m',
                    '45m': '45m',
                    '1h': '1H',
                    '2h': '2H',
                    '3h': '3H',
                    '4h': '4H',
                    '1d': '1D',
                    '1w': '1W',
                    '1M': '1M',
                },
            },
            'streaming': {
                'keepAlive': 15000,
            },
        })

    async def subscribe(self, channel, symbol, params={}):
        await self.load_markets()
        market = self.market(symbol)
        url = self.implode_hostname(self.urls['api']['ws']['public'])
        messageHash = market['type'] + '/' + channel + ':' + market['id']
        request = {
            'op': 'subscribe',
            'args': [messageHash],
        }
        return await self.watch(url, messageHash, self.deep_extend(request, params), messageHash)

    async def subscribe_private(self, channel, symbol, params={}):
        await self.load_markets()
        market = self.market(symbol)
        url = self.implode_hostname(self.urls['api']['ws']['private'])
        messageHash = channel + ':' + market['id']
        await self.authenticate()
        request = {
            'op': 'subscribe',
            'args': [messageHash],
        }
        return await self.watch(url, messageHash, self.deep_extend(request, params), messageHash)

    async def watch_trades(self, symbol, since=None, limit=None, params={}):
        """
        get the list of most recent trades for a particular symbol
        :param str symbol: unified symbol of the market to fetch trades for
        :param int|None since: timestamp in ms of the earliest trade to fetch
        :param int|None limit: the maximum amount of trades to fetch
        :param dict params: extra parameters specific to the bitmart api endpoint
        :returns [dict]: a list of `trade structures <https://docs.ccxt.com/en/latest/manual.html?#public-trades>`
        """
        await self.load_markets()
        symbol = self.symbol(symbol)
        trades = await self.subscribe('trade', symbol, params)
        if self.newUpdates:
            limit = trades.getLimit(symbol, limit)
        return self.filter_by_since_limit(trades, since, limit, 'timestamp', True)

    async def watch_ticker(self, symbol, params={}):
        """
        watches a price ticker, a statistical calculation with the information calculated over the past 24 hours for a specific market
        :param str symbol: unified symbol of the market to fetch the ticker for
        :param dict params: extra parameters specific to the bitmart api endpoint
        :returns dict: a `ticker structure <https://docs.ccxt.com/en/latest/manual.html#ticker-structure>`
        """
        return await self.subscribe('ticker', symbol, params)

    async def watch_orders(self, symbol=None, since=None, limit=None, params={}):
        """
        watches information on multiple orders made by the user
        :param str|None symbol: unified market symbol of the market orders were made in
        :param int|None since: the earliest time in ms to fetch orders for
        :param int|None limit: the maximum number of  orde structures to retrieve
        :param dict params: extra parameters specific to the bitmart api endpoint
        :returns [dict]: a list of `order structures <https://docs.ccxt.com/en/latest/manual.html#order-structure>`
        """
        if symbol is None:
            raise ArgumentsRequired(self.id + ' watchOrders requires a symbol argument')
        await self.load_markets()
        market = self.market(symbol)
        symbol = market['symbol']
        if market['type'] != 'spot':
            raise ArgumentsRequired(self.id + ' watchOrders supports spot markets only')
        channel = 'spot/user/order'
        orders = await self.subscribe_private(channel, symbol, params)
        if self.newUpdates:
            limit = orders.getLimit(symbol, limit)
        return self.filter_by_symbol_since_limit(orders, symbol, since, limit, True)

    def handle_orders(self, client, message):
        #
        # {
        #     "data":[
        #         {
        #             symbol: 'LTC_USDT',
        #             notional: '',
        #             side: 'buy',
        #             last_fill_time: '0',
        #             ms_t: '1646216634000',
        #             type: 'limit',
        #             filled_notional: '0.000000000000000000000000000000',
        #             last_fill_price: '0',
        #             size: '0.500000000000000000000000000000',
        #             price: '50.000000000000000000000000000000',
        #             last_fill_count: '0',
        #             filled_size: '0.000000000000000000000000000000',
        #             margin_trading: '0',
        #             state: '8',
        #             order_id: '24807076628',
        #             order_type: '0'
        #           }
        #     ],
        #     "table":"spot/user/order"
        # }
        #
        channel = self.safe_string(message, 'table')
        orders = self.safe_value(message, 'data', [])
        ordersLength = len(orders)
        if ordersLength > 0:
            limit = self.safe_integer(self.options, 'ordersLimit', 1000)
            if self.orders is None:
                self.orders = ArrayCacheBySymbolById(limit)
            stored = self.orders
            marketIds = []
            for i in range(0, len(orders)):
                order = self.parse_ws_order(orders[i])
                stored.append(order)
                symbol = order['symbol']
                market = self.market(symbol)
                marketIds.append(market['id'])
            for i in range(0, len(marketIds)):
                messageHash = channel + ':' + marketIds[i]
                client.resolve(self.orders, messageHash)

    def parse_ws_order(self, order, market=None):
        #
        # {
        #     symbol: 'LTC_USDT',
        #     notional: '',
        #     side: 'buy',
        #     last_fill_time: '0',
        #     ms_t: '1646216634000',
        #     type: 'limit',
        #     filled_notional: '0.000000000000000000000000000000',
        #     last_fill_price: '0',
        #     size: '0.500000000000000000000000000000',
        #     price: '50.000000000000000000000000000000',
        #     last_fill_count: '0',
        #     filled_size: '0.000000000000000000000000000000',
        #     margin_trading: '0',
        #     state: '8',
        #     order_id: '24807076628',
        #     order_type: '0'
        #   }
        #
        marketId = self.safe_string(order, 'symbol')
        market = self.safe_market(marketId, market)
        id = self.safe_string(order, 'order_id')
        clientOrderId = self.safe_string(order, 'clientOid')
        price = self.safe_string(order, 'price')
        filled = self.safe_string(order, 'filled_size')
        amount = self.safe_string(order, 'size')
        type = self.safe_string(order, 'type')
        rawState = self.safe_string(order, 'state')
        status = self.parseOrderStatusByType(market['type'], rawState)
        timestamp = self.safe_integer(order, 'ms_t')
        symbol = market['symbol']
        side = self.safe_string_lower(order, 'side')
        return self.safe_order({
            'info': order,
            'symbol': symbol,
            'id': id,
            'clientOrderId': clientOrderId,
            'timestamp': None,
            'datetime': None,
            'lastTradeTimestamp': timestamp,
            'type': type,
            'timeInForce': None,
            'postOnly': None,
            'side': side,
            'price': price,
            'stopPrice': None,
            'amount': amount,
            'cost': None,
            'average': None,
            'filled': filled,
            'remaining': None,
            'status': status,
            'fee': None,
            'trades': None,
        }, market)

    def handle_trade(self, client, message):
        #
        #     {
        #         table: 'spot/trade',
        #         data: [
        #             {
        #                 price: '52700.50',
        #                 s_t: 1630982050,
        #                 side: 'buy',
        #                 size: '0.00112',
        #                 symbol: 'BTC_USDT'
        #             },
        #         ]
        #     }
        #
        table = self.safe_string(message, 'table')
        data = self.safe_value(message, 'data', [])
        tradesLimit = self.safe_integer(self.options, 'tradesLimit', 1000)
        for i in range(0, len(data)):
            trade = self.parse_trade(data[i])
            symbol = trade['symbol']
            marketId = self.safe_string(trade['info'], 'symbol')
            messageHash = table + ':' + marketId
            stored = self.safe_value(self.trades, symbol)
            if stored is None:
                stored = ArrayCache(tradesLimit)
                self.trades[symbol] = stored
            stored.append(trade)
            client.resolve(stored, messageHash)
        return message

    def handle_ticker(self, client, message):
        #
        #     {
        #         data: [
        #             {
        #                 base_volume_24h: '78615593.81',
        #                 high_24h: '52756.97',
        #                 last_price: '52638.31',
        #                 low_24h: '50991.35',
        #                 open_24h: '51692.03',
        #                 s_t: 1630981727,
        #                 symbol: 'BTC_USDT'
        #             }
        #         ],
        #         table: 'spot/ticker'
        #     }
        #
        table = self.safe_string(message, 'table')
        data = self.safe_value(message, 'data', [])
        for i in range(0, len(data)):
            ticker = self.parse_ticker(data[i])
            symbol = ticker['symbol']
            marketId = self.safe_string(ticker['info'], 'symbol')
            messageHash = table + ':' + marketId
            self.tickers[symbol] = ticker
            client.resolve(ticker, messageHash)
        return message

    async def watch_ohlcv(self, symbol, timeframe='1m', since=None, limit=None, params={}):
        await self.load_markets()
        symbol = self.symbol(symbol)
        timeframes = self.safe_value(self.options, 'timeframes', {})
        interval = self.safe_string(timeframes, timeframe)
        name = 'kline' + interval
        ohlcv = await self.subscribe(name, symbol, params)
        if self.newUpdates:
            limit = ohlcv.getLimit(symbol, limit)
        return self.filter_by_since_limit(ohlcv, since, limit, 0, True)

    def handle_ohlcv(self, client, message):
        #
        #     {
        #         data: [
        #             {
        #                 candle: [
        #                     1631056350,
        #                     '46532.83',
        #                     '46555.71',
        #                     '46511.41',
        #                     '46555.71',
        #                     '0.25'
        #                 ],
        #                 symbol: 'BTC_USDT'
        #             }
        #         ],
        #         table: 'spot/kline1m'
        #     }
        #
        table = self.safe_string(message, 'table')
        data = self.safe_value(message, 'data', [])
        parts = table.split('/')
        part1 = self.safe_string(parts, 1)
        interval = part1.replace('kline', '')
        # use a reverse lookup in a static map instead
        timeframes = self.safe_value(self.options, 'timeframes', {})
        timeframe = self.find_timeframe(interval, timeframes)
        duration = self.parse_timeframe(timeframe)
        durationInMs = duration * 1000
        for i in range(0, len(data)):
            marketId = self.safe_string(data[i], 'symbol')
            candle = self.safe_value(data[i], 'candle')
            market = self.safe_market(marketId)
            symbol = market['symbol']
            parsed = self.parse_ohlcv(candle, market)
            parsed[0] = int(parsed[0] / durationInMs) * durationInMs
            self.ohlcvs[symbol] = self.safe_value(self.ohlcvs, symbol, {})
            stored = self.safe_value(self.ohlcvs[symbol], timeframe)
            if stored is None:
                limit = self.safe_integer(self.options, 'OHLCVLimit', 1000)
                stored = ArrayCacheByTimestamp(limit)
                self.ohlcvs[symbol][timeframe] = stored
            stored.append(parsed)
            messageHash = table + ':' + marketId
            client.resolve(stored, messageHash)

    async def watch_order_book(self, symbol, limit=None, params={}):
        """
        watches information on open orders with bid(buy) and ask(sell) prices, volumes and other data
        :param str symbol: unified symbol of the market to fetch the order book for
        :param int|None limit: the maximum amount of order book entries to return
        :param dict params: extra parameters specific to the bitmart api endpoint
        :returns dict: A dictionary of `order book structures <https://docs.ccxt.com/en/latest/manual.html#order-book-structure>` indexed by market symbols
        """
        options = self.safe_value(self.options, 'watchOrderBook', {})
        depth = self.safe_string(options, 'depth', 'depth400')
        orderbook = await self.subscribe(depth, symbol, params)
        return orderbook.limit(limit)

    def handle_delta(self, bookside, delta):
        price = self.safe_float(delta, 0)
        amount = self.safe_float(delta, 1)
        bookside.store(price, amount)

    def handle_deltas(self, bookside, deltas):
        for i in range(0, len(deltas)):
            self.handle_delta(bookside, deltas[i])

    def handle_order_book_message(self, client, message, orderbook):
        #
        #     {
        #         asks: [
        #             ['46828.38', '0.21847'],
        #             ['46830.68', '0.08232'],
        #             ['46832.08', '0.09285'],
        #             ['46837.82', '0.02028'],
        #             ['46839.43', '0.15068']
        #         ],
        #         bids: [
        #             ['46820.78', '0.00444'],
        #             ['46814.33', '0.00234'],
        #             ['46813.50', '0.05021'],
        #             ['46808.14', '0.00217'],
        #             ['46808.04', '0.00013']
        #         ],
        #         ms_t: 1631044962431,
        #         symbol: 'BTC_USDT'
        #     }
        #
        asks = self.safe_value(message, 'asks', [])
        bids = self.safe_value(message, 'bids', [])
        self.handle_deltas(orderbook['asks'], asks)
        self.handle_deltas(orderbook['bids'], bids)
        timestamp = self.safe_integer(message, 'ms_t')
        marketId = self.safe_string(message, 'symbol')
        symbol = self.safe_symbol(marketId)
        orderbook['symbol'] = symbol
        orderbook['timestamp'] = timestamp
        orderbook['datetime'] = self.iso8601(timestamp)
        return orderbook

    def handle_order_book(self, client, message):
        #
        #     {
        #         data: [
        #             {
        #                 asks: [
        #                     ['46828.38', '0.21847'],
        #                     ['46830.68', '0.08232'],
        #                     ['46832.08', '0.09285'],
        #                     ['46837.82', '0.02028'],
        #                     ['46839.43', '0.15068']
        #                 ],
        #                 bids: [
        #                     ['46820.78', '0.00444'],
        #                     ['46814.33', '0.00234'],
        #                     ['46813.50', '0.05021'],
        #                     ['46808.14', '0.00217'],
        #                     ['46808.04', '0.00013']
        #                 ],
        #                 ms_t: 1631044962431,
        #                 symbol: 'BTC_USDT'
        #             }
        #         ],
        #         table: 'spot/depth5'
        #     }
        #
        data = self.safe_value(message, 'data', [])
        table = self.safe_string(message, 'table')
        parts = table.split('/')
        lastPart = self.safe_string(parts, 1)
        limitString = lastPart.replace('depth', '')
        limit = int(limitString)
        for i in range(0, len(data)):
            update = data[i]
            marketId = self.safe_string(update, 'symbol')
            symbol = self.safe_symbol(marketId)
            orderbook = self.safe_value(self.orderbooks, symbol)
            if orderbook is None:
                orderbook = self.order_book({}, limit)
                self.orderbooks[symbol] = orderbook
            orderbook.reset({})
            self.handle_order_book_message(client, update, orderbook)
            messageHash = table + ':' + marketId
            client.resolve(orderbook, messageHash)
        return message

    async def authenticate(self, params={}):
        self.check_required_credentials()
        url = self.implode_hostname(self.urls['api']['ws']['private'])
        messageHash = 'login'
        client = self.client(url)
        future = self.safe_value(client.subscriptions, messageHash)
        if future is None:
            future = client.future('authenticated')
            timestamp = str(self.milliseconds())
            memo = self.uid
            path = 'bitmart.WebSocket'
            auth = timestamp + '#' + memo + '#' + path
            signature = self.hmac(self.encode(auth), self.encode(self.secret), hashlib.sha256)
            request = {
                'op': messageHash,
                'args': [
                    self.apiKey,
                    timestamp,
                    signature,
                ],
            }
            self.spawn(self.watch, url, messageHash, request, messageHash, future)
        return await future

    def handle_subscription_status(self, client, message):
        #
        #     {"event":"subscribe","channel":"spot/depth:BTC-USDT"}
        #
        return message

    def handle_authenticate(self, client, message):
        #
        #     {event: 'login', success: True}
        #
        client.resolve(message, 'authenticated')
        return message

    def handle_error_message(self, client, message):
        #
        #     {event: 'error', message: 'Invalid sign', errorCode: 30013}
        #     {"event":"error","message":"Unrecognized request: {\"event\":\"subscribe\",\"channel\":\"spot/depth:BTC-USDT\"}","errorCode":30039}
        #
        errorCode = self.safe_string(message, 'errorCode')
        try:
            if errorCode is not None:
                feedback = self.id + ' ' + self.json(message)
                self.throw_exactly_matched_exception(self.exceptions['exact'], errorCode, feedback)
                messageString = self.safe_value(message, 'message')
                if messageString is not None:
                    self.throw_broadly_matched_exception(self.exceptions['broad'], messageString, feedback)
        except Exception as e:
            if isinstance(e, AuthenticationError):
                client.reject(e, 'authenticated')
                method = 'login'
                if method in client.subscriptions:
                    del client.subscriptions[method]
                return False
        return message

    def handle_message(self, client, message):
        if not self.handle_error_message(client, message):
            return
        #
        #     {"event":"error","message":"Unrecognized request: {\"event\":\"subscribe\",\"channel\":\"spot/depth:BTC-USDT\"}","errorCode":30039}
        #     {"event":"subscribe","channel":"spot/depth:BTC-USDT"}
        #     {
        #         table: "spot/depth",
        #         action: "partial",
        #         data: [
        #             {
        #                 instrument_id:   "BTC-USDT",
        #                 asks: [
        #                     ["5301.8", "0.03763319", "1"],
        #                     ["5302.4", "0.00305", "2"],
        #                 ],
        #                 bids: [
        #                     ["5301.7", "0.58911427", "6"],
        #                     ["5301.6", "0.01222922", "4"],
        #                 ],
        #                 timestamp: "2020-03-16T03:25:00.440Z",
        #                 checksum: -2088736623
        #             }
        #         ]
        #     }
        #
        #     {data: '', table: 'spot/user/order'}
        #
        table = self.safe_string(message, 'table')
        if table is None:
            event = self.safe_string(message, 'event')
            if event is not None:
                methods = {
                    # 'info': self.handleSystemStatus,
                    # 'book': 'handleOrderBook',
                    'login': self.handle_authenticate,
                    'subscribe': self.handle_subscription_status,
                }
                method = self.safe_value(methods, event)
                if method is None:
                    return message
                else:
                    return method(client, message)
        else:
            parts = table.split('/')
            name = self.safe_string(parts, 1)
            methods = {
                'depth': self.handle_order_book,
                'depth5': self.handle_order_book,
                'depth400': self.handle_order_book,
                'ticker': self.handle_ticker,
                'trade': self.handle_trade,
                # ...
            }
            method = self.safe_value(methods, name)
            if name.find('kline') >= 0:
                method = self.handle_ohlcv
            privateName = self.safe_string(parts, 2)
            if privateName == 'order':
                method = self.handle_orders
            if method is None:
                return message
            else:
                return method(client, message)
