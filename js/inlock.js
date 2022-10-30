'use strict';

//  ---------------------------------------------------------------------------

const Exchange = require ('./base/Exchange');
const { ExchangeError } = require ('./base/errors');

//  ---------------------------------------------------------------------------

module.exports = class inlock extends Exchange {
    describe () {
        return this.deepExtend (super.describe (), {
            'id': 'inlock',
            'name': 'InLock.io',
            'countries': [ 'HU' ],
            'rateLimit': 20,
            'version': 'v1.0',
            'userAgent': this.userAgents['chrome'],
            'has': {
                'CORS': undefined,
                'spot': true,
                'margin': undefined,
                'swap': undefined,
                'future': undefined,
                'option': undefined,
                'fetchBalance': true,
            },
            'urls': {
                'logo': 'https://user-images.githubusercontent.com/51840849/87460810-1dd06c00-c616-11ea-9276-956f400d6ffa.jpg',
                'api': 'https://api.inlock.io/inlock/api',
                'www': 'https://inlock.io',
                'doc': 'https://app.swaggerhub.com/apis/IncomeLocker/inlock_retail_api/',
            },
            'api': {
                'retail': {
                    'get': [
                        'getBalance',
                    ],
                },
            },
            'markets': {
            },
        });
    }

    parseBalance (response) {
        const result = {
            'info': response,
        };
        const balances = response.coins;
        for (let i = 0; i < balances.length; i++) {
            const balance = balances[i];
            const symbol = this.safeString (balance, 'ticker');
            const code = this.safeCurrencyCode (symbol);
            const account = this.account ();
            account['total'] = this.safeString (balance, 'balance');
            account['used'] = this.safeString (balance, 'locked');
            result[code] = account;
        }
        return this.safeBalance (result);
    }

    async fetchBalance (params = {}) {
        await this.loadMarkets ();
        const response = await this.retailGetGetBalance (params);
        const balances = this.safeValue (response['result'], 'getBalance');
        return this.parseBalance (balances);
    }

    sign (path, api = 'public', method = 'GET', params = {}, headers = undefined, body = undefined) {
        const query = this.omit (params, this.extractParams (path));
        console.log (query);
        let url = this.urls['api'] + '/' + this.version + '/' + api + '/' + path;
        // FIXME: implement this right
        if (method === 'GET') {
            if (Object.keys (params).length) {
                url += '?' + this.urlencode (params);
            }
        } else {
            body = this.urlencode (params);
        }
        this.checkRequiredCredentials ();
        const raw_data = url;
        const signature = this.binaryToBase58 (this.hmac (raw_data, this.base58ToBinary (this.secret), 'sha512', null));
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Apikey': this.apiKey,
            'X-Signature': signature,
        };
        return { 'url': url, 'method': method, 'body': body, 'headers': headers };
    }

    handleErrors (code, reason, url, method, headers, body, response, requestHeaders, requestBody) {
        if (response === undefined) {
            return; // fallback to default error handler
        }
        if ('error' in response) {
            // const errorCode = this.safeString (response['error'], 'code');
            const message = this.safeString (response['error'], 'message');
            const feedback = this.id + ' ' + body;
            this.throwExactlyMatchedException (this.exceptions['exact'], message, feedback);
            this.throwBroadlyMatchedException (this.exceptions['broad'], message, feedback);
            throw new ExchangeError (feedback); // unknown message
        }
    }
};
