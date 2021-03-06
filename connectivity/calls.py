import copy
import datetime
import hashlib
import hmac
import logging
import time
from decimal import Decimal
from random import randint

import requests

from constants import TRADING_DEFAULT_CURRENCY_PAIR

LOGGER = logging.getLogger('BitstampAPI')


def dt(timestamp):
    """
    Convert a unix timestamp or ISO 8601 date string to a datetime object.
    """
    if not timestamp:
        return None
    try:
        timestamp = int(timestamp)
    except ValueError:
        try:
            timestamp = time.mktime(
                time.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f'))
        except ValueError:
            timestamp = time.mktime(
                time.strptime(timestamp, '%Y-%m-%d %H:%M:%S'))
    return datetime.datetime.fromtimestamp(timestamp)


class APIError(Exception):
    pass


class APICall(object):
    url = None
    method = 'get'

    def _process_response(self, response):
        """
        Process the response dictionary.

        If the dictionary is just being altered, then no return is necessary.
        Alternatively, a totally different response can be returned.
        """
        return

    def call(self, prefix_url, **params):
        # Form request
        r = None
        url = prefix_url + self.url
        req_id = randint(0, 10000)

        print_params = copy.deepcopy(params)
        if 'key' in print_params:  # private call
            print_params['key'] = '*' * 3
            print_params['signature'] = '*' * 3

        # with open('/tmp/bitstamp/{}-{}-{}-REQ.json'.format(), 'w') as debug_w:
        #     json.dump(obj=params, fp=debug_w, indent=4, ensure_ascii=True)

        LOGGER.info('[{2}] TO BITSTAMP : {0} {1}'.format(url, print_params, req_id))
        if self.method == 'get':
            r = requests.get(url, params=params)
        elif self.method == 'post':
            r = requests.post(url, data=params)
        response = r.json()

        LOGGER.info('[{1}] FROM BITSTAMP : {0}'.format(response, req_id))

        # API error?
        if isinstance(response, dict) and 'error' in response:
            raise APIError(response['error'])
        # Process fields
        new_response = self._process_response(response)
        if new_response is not None:
            response = new_response
        return response


class APIPrivateCall(APICall):
    method = 'post'

    def __init__(self, client_id, api_key, api_secret, *args, **kwargs):
        super(APIPrivateCall, self).__init__(*args, **kwargs)
        self.client_id = client_id
        self.api_key = api_key
        self.api_secret = api_secret

    def _get_nonce(self):
        return str(int(time.time() * 1e6))

    def call(self, prefix_url, **params):
        nonce = self._get_nonce()
        message = nonce + self.client_id + self.api_key
        signature = hmac.new(bytes(self.api_secret.encode('utf8')),
                             msg=bytes(message.encode('utf8')),
                             digestmod=hashlib.sha256)
        signature = signature.hexdigest().upper()
        params.update({
            'key': self.api_key, 'signature': signature, 'nonce': nonce
        })
        return super(APIPrivateCall, self).call(prefix_url, **params)


# Specific call classes
class APIAccountBalanceCall(APIPrivateCall):
    url = 'balance/'

    def _process_response(self, response):
        for a, x in response.items():
            response[a] = Decimal(x)


class APIBitcoinDepositAddressCall(APIPrivateCall):
    url = 'bitcoin_deposit_address/'


class APIBitcoinWithdrawalCall(APIPrivateCall):
    url = 'bitcoin_withdrawal/'


# **** LIMIT # ****

class APIBuyLimitOrderBTCEURCall(APIPrivateCall):
    url = 'buy/{}/'.format(TRADING_DEFAULT_CURRENCY_PAIR)

    def _process_response(self, response):
        if 'datetime' in response:
            response['datetime'] = dt(response['datetime'])

        if 'price' in response:
            response['price'] = Decimal(response['price'])

        if 'amount' in response:
            response['amount'] = Decimal(response['amount'])

        if isinstance(response, dict) and 'status' in response and response['status'] == 'error':
            raise APIError(response)


class APISellLimitBTCEUROrderCall(APIBuyLimitOrderBTCEURCall):
    url = 'sell/{}/'.format(TRADING_DEFAULT_CURRENCY_PAIR)


# **** LIMIT # ****


# **** MARKET # ****


class APIBuyMarketOrderBTCEURCall(APIBuyLimitOrderBTCEURCall):
    url = 'buy/market/{}/'.format(TRADING_DEFAULT_CURRENCY_PAIR)


class APISellMarketOrderBTCEURCall(APIBuyLimitOrderBTCEURCall):
    url = 'sell/market/{}/'.format(TRADING_DEFAULT_CURRENCY_PAIR)


# **** MARKET # ****


class APICancelOrderCall(APIPrivateCall):
    url = 'cancel_order/'


class APIOrderStatusCall(APIPrivateCall):
    url = 'order_status/'


class APIEURUSDConversionRateCall(APICall):
    url = 'eur_usd/'

    def _process_response(self, response):
        response['buy'] = Decimal(response['buy'])
        response['sell'] = Decimal(response['sell'])


class APIOrderBookCall(APICall):
    url = 'order_book/{}/'.format(TRADING_DEFAULT_CURRENCY_PAIR)

    def _process_response(self, response):
        response['timestamp'] = dt(response['timestamp'])
        response['bids'] = [{
            'price': Decimal(price),
            'amount': Decimal(amount)
        } for (price, amount) in response['bids']]
        response['asks'] = [{
            'price': Decimal(price),
            'amount': Decimal(amount)
        } for (price, amount) in response['asks']]


class APIOpenOrdersCall(APIPrivateCall):
    url = 'open_orders/all/'

    def _process_response(self, response):
        for order in response:
            order['datetime'] = dt(order['datetime'])
            order['price'] = Decimal(order['price'])
            order['amount'] = Decimal(order['amount'])


class APIRippleDepositAddressCall(APIPrivateCall):
    url = 'ripple_address/'


class APIRippleWithdrawalCall(APIPrivateCall):
    url = 'ripple_withdrawal/'


class APITickerCall(APICall):
    url = 'ticker/{}/'.format(TRADING_DEFAULT_CURRENCY_PAIR)

    def _process_response(self, response):
        response['last'] = Decimal(response['last'])
        response['high'] = Decimal(response['high'])
        response['low'] = Decimal(response['low'])
        response['volume'] = Decimal(response['volume'])
        response['timestamp'] = dt(response['timestamp'])
        response['bid'] = Decimal(response['bid'])
        response['ask'] = Decimal(response['ask'])


class APITransactionsCall(APICall):
    url = 'transactions/{}/'.format(TRADING_DEFAULT_CURRENCY_PAIR)

    def _process_response(self, response):
        for tx in response:
            tx['date'] = dt(tx['date'])
            tx['price'] = Decimal(tx['price'])
            tx['amount'] = Decimal(tx['amount'])


class APIUnconfirmedBitcoinDepositsCall(APIPrivateCall):
    url = 'unconfirmed_btc/'

    def _process_response(self, response):
        response['amount'] = Decimal(response['amount'])
        response['confirmations'] = int(response['confirmations'])


class APIUserTransactionsCall(APIPrivateCall):
    # Returns transactions for all currency pairs.
    url = 'user_transactions/'

    def _process_response(self, response):
        for tx in response:
            tx['datetime'] = dt(tx['datetime'])
            tx['usd'] = Decimal(tx['usd'])
            tx['btc'] = Decimal(tx['btc'])
            tx['fee'] = Decimal(tx['fee'])


class APIWithdrawalRequestsCall(APIPrivateCall):
    url = 'withdrawal_requests/'

    def _process_response(self, response):
        for wr in response:
            wr['datetime'] = dt(wr['datetime'])
            wr['amount'] = Decimal(wr['amount'])
