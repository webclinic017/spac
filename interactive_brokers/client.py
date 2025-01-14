from order import Order
import requests
from typing import Dict, List
import urllib3
from urllib3.exceptions import InsecureRequestWarning
urllib3.disable_warnings(category=InsecureRequestWarning)

class IBClient(object):
    def __init__(self):
        # Account info
        self.acctId = open('account_info.txt', 'r').read()

        # URL components
        self.ib_gateway_path = 'https://localhost:5000'
        self.api_version = 'v1'

    def _build_url(self, endpoint: str) -> str:
        """Builds a url for a request.
        Arguments:
        ----
        endpoint {str} -- The URL that needs conversion to a full endpoint URL.
        Returns:
        ----
        {str} -- A full URL path.
        """

        # build the URL
        full_url = self.ib_gateway_path + '/' + self.api_version + '/portal/' + endpoint
        return full_url

    def _make_request(self, endpoint: str, req_type: str, params: Dict = None) -> Dict:
        """Handles the request to the client.
        Handles all the requests made by the client and correctly organizes
        the information so it is sent correctly. Additionally it will also
        build the URL.
        Arguments:
        ----
        endpoint {str} -- The endpoint we wish to request.
        req_type {str} --  Defines the type of request to be made. Can be one of four
            possible values ['GET','POST','DELETE','PUT']
        params {dict} -- Any arguments that are to be sent along in the request. That
            could be parameters of a 'GET' request, or a data payload of a
            'POST' request.
        
        Returns:
        ----
        {Dict} -- A response dictionary.
        """

        # first build the url
        url = self._build_url(endpoint = endpoint)

        # make sure it's a JSON String
        headers = {'Content-Type':'application/json'}

        # Scenario 1: POST with a payload
        if req_type == 'POST' and params is not None:
            response = requests.post(url, headers = headers, json=params, verify = False)

        # SCENARIO 2: POST without a payload
        elif req_type == 'POST' and params is None:
            response = requests.post(url, headers = headers, verify = False)

        # SCENARIO 3: GET without parameters
        elif req_type == 'GET' and params is None:
            response = requests.get(url, headers = headers, verify = False)

         # SCENARIO 4: GET with parameters
        elif req_type == 'GET' and params is not None:
            response = requests.get(url, headers = headers, params = params, verify = False)

         # SCENARIO 5: DELETE (does not accept parameters)
        elif req_type == 'DELETE':
            response = requests.delete(url, headers = headers, verify = False)

        # grab the status code
        status_code = response.status_code

        # grab the response headers
        response_headers = response.headers

        # Check to see if it was successful
        if response.ok:
            if req_type == 'DELETE':
                return None
            elif response_headers.get('Content-Type','null') == 'application/json;charset=utf-8':
                return response.json()
            else:
                return response.json()

        # if it was a bad request print it out
        elif not response.ok and url != 'https://localhost:5000/v1/portal/iserver/account':
            print('')
            print('-'*80)
            print("BAD REQUEST - STATUS CODE: {}".format(status_code))
            print("RESPONSE URL: {}".format(response.url))
            print("RESPONSE HEADERS: {}".format(response.headers))
            print("RESPONSE TEXT: {}".format(response.text))
            print('-'*80)
            print('')

    def validate(self) -> Dict:
        """Validates the current session for the SSO user."""

        # define request components
        endpoint = 'sso/validate'
        req_type = 'GET'

        content = self._make_request(endpoint = endpoint, req_type = req_type)

        return content

    def tickle(self) -> Dict:
        """Keeps the session open.
        If the gateway has not received any requests for several minutes an open session will 
        automatically timeout. The tickle endpoint pings the server to prevent the 
        session from ending.
        """

        # define request components
        endpoint = 'tickle'
        req_type = 'POST'

        content = self._make_request(endpoint = endpoint, req_type = req_type)

        return content

    def is_authenticated(self) -> Dict:
        """Checks if session is authenticated.
        Current Authentication status to the Brokerage system. Market Data and 
        Trading is not possible if not authenticated, e.g. authenticated 
        shows False.
        """

        # define request components
        endpoint = 'iserver/auth/status'
        req_type = 'POST'

        content = self._make_request(endpoint = endpoint, req_type = req_type)

        return content

    def reauthenticate(self) -> Dict:
        """Reauthenticates an existing session.
        Provides a way to reauthenticate to the Brokerage system as long as there 
        is a valid SSO session, see /sso/validate.
        """

        # define request components
        endpoint = 'iserver/reauthenticate'
        req_type = 'POST'

        content = self._make_request(endpoint = endpoint, req_type = req_type)
        
        return content

    def logout(self) -> Dict:
        """End current session.
        Logs the user out of the gateway session. Any further activity requires 
        re-authentication.
        """

        # define request components
        endpoint = 'logout'
        req_type = 'POST'

        content = self._make_request(endpoint = endpoint, req_type = req_type)

        return content

    def get_accounts(self) -> Dict:
        """Get accounts.
        Returns a list of accounts the user has trading access to, their respective aliases
        and the currently selected account. Note this endpoint must be called before modifying
        an order or querying open orders.
        """

        # define request components
        endpoint = 'iserver/accounts'
        req_type = 'GET'

        content = self._make_request(endpoint = endpoint, req_type = req_type)

        return content

    def get_account_balance(self) -> Dict:
        """Get account balance(s).
        Returns a summary of all account balances for the given accounts, if more than
        one account is passed, the result is consolidated.

        Query parameters:
        1. acctIds: list of account ids
        """

        # define request components
        endpoint = 'pa/summary'
        req_type = 'POST'
        payload = {
            'acctIds': [self.acctId]
        }

        # this is special, I don't want the JSON content right away.
        content = self._make_request(endpoint = endpoint, req_type = req_type, params = payload)
        
        return content

    def get_outstanding_orders(self):
        """Get current live orders.
        The endpoint is meant to be used in polling mode, e.g. requesting every 
        x seconds. The response will contain two objects, one is notification, the 
        other is orders. Orders is the list of orders (cancelled, filled, submitted) 
        with activity in the current day. Notifications contains information about 
        execute orders as they happen, see status field.

        Order status definitions:
        PendingSubmit - Indicates the order was sent, but confirmation has not been received that
        it has been received by the destination. Occurs most commonly if an exchange is closed.
        PendingCancel - Indicates that a request has been sent to cancel an order but confirmation
        has not been received of its cancellation.
        PreSubmitted - Indicates that a simulated order type has been accepted by the IBKR system
        and that this order has yet to be elected. The order is held in the IBKR system until
        the election criteria are met. At that time the order is transmitted to the order
        destination as specified.
        Submitted - Indicates that the order has been accepted at the order destination and
        is working.
        Cancelled - Indicates that the balance of the order has been confirmed cancelled by the
        IB system. This could occur unexpectedly when IB or the destination has rejected the order.
        Filled - Indicates that the order has been completely filled
        Inactive - Indicates the order is not working, for instance if the order was invalid and
        triggered an error message, or if the order was to short a security and shares have not yet
        been located
        """

        # define request components
        endpoint = 'iserver/account/orders'
        req_type = 'GET'

        content = self._make_request(endpoint = endpoint, req_type = req_type)

        return content

    def get_conid(self, symbol: str):
        """Get current live orders. Returns and array of results.
        Symbol or name to be searched.

        Query parameters:
        1. symbol: If symbol is warrant, warrant conid can be found in 'sections' in resulting array.
        2. (optional) name: should be true if the search is to be performed by name. false by default.
        3. (optional) secType: If search is done by name, only the assets provided in this field will
        be returned. Currently, only STK is supported.
        """

        # define request components
        endpoint = 'iserver/secdef/search'
        req_type = 'POST'
        payload = {
            'symbol': symbol,
            'name': True,
        }

        content = self._make_request(endpoint = endpoint, req_type = req_type, params = payload)

        return content

    def preview_order(self, order: Order) -> Dict:
        """Preview a new order.
        This endpoint allows you to preview order without actually submitting the order and you can
        get commission information in the response.

        Query parameters: see order.py
        """

        # define request components
        endpoint = 'iserver/account/{}/order/whatif'.format(self.acctId)
        req_type = 'POST'
        payload = {
            "acctId": order.get_acctId(),
            "conid": order.get_conid(),
            "secType": order.get_secType(),
            "cOID": order.get_cOID(),
            "parentId": order.get_parentId(),
            "orderType": order.get_orderType(),
            "listingExchange": order.get_listingExchange(),
            "outsideRTH": order.get_outsideRTH(),
            "price": order.get_price(),
            "side": order.get_side(),
            "ticker": order.get_ticker(),
            "tif": order.get_tif(),
            "referrer": order.get_referrer(),
            "quantity": order.get_quantity(),
            "fxQty": order.get_fxQty(),
            "useAdaptive": order.get_useAdaptive(),
            "isCurrencyConversion": order.get_isCurrencyConversion()
        }

        content = self._make_request(endpoint = endpoint, req_type = req_type, params = payload)

        return content

    def new_order(self, order: Order) -> Dict:
        """Place a new order.
        Please note here, sometimes this endpoint alone can't make sure you submit the order 
        successfully, you could receive some questions in the response, you have to to answer 
        them in order to submit the order successfully. You can use "/iserver/reply/{replyid}" 
        end-point to answer questions.

        Query parameters: see order.py
        """

        # define request components
        endpoint = 'iserver/account/{}/order'.format(self.acctId)
        req_type = 'POST'
        payload = {
            "acctId": order.get_acctId(),
            "conid": order.get_conid(),
            "secType": order.get_secType(),
            "cOID": order.get_cOID(),
            "parentId": order.get_parentId(),
            "orderType": order.get_orderType(),
            "listingExchange": order.get_listingExchange(),
            "outsideRTH": order.get_outsideRTH(),
            "price": order.get_price(),
            "side": order.get_side(),
            "ticker": order.get_ticker(),
            "tif": order.get_tif(),
            "referrer": order.get_referrer(),
            "quantity": order.get_quantity(),
            "fxQty": order.get_fxQty(),
            "useAdaptive": order.get_useAdaptive(),
            "isCurrencyConversion": order.get_isCurrencyConversion()
        }

        content = self._make_request(endpoint = endpoint, req_type = req_type, params = payload)

        return content

    def delete_order(self, orderId: str) -> Dict:
        """Place a new order.
        Deletes an open order. Must call /iserver/accounts prior to deleting an order.
        Use get_outstanding_orders() to review open orders.

        Path parameters:
        1. account id
        2. orderId (NOT cOID/order_ref)
        """

        # call iserver/accounts endpoint
        self.get_accounts()

        # define request components
        endpoint = 'iserver/account/{}/order/{}'.format(self.acctId, orderId)
        req_type = 'DELETE'

        content = self._make_request(endpoint = endpoint, req_type = req_type)

        return content

    def get_market_data(self, conids: List[str], fields: List[str] = None) -> Dict:
        """
        Get Market Data for the given conid(s). The endpoint will return by default bid,
        ask, last, change, change pct, close, listing exchange. See response fields for
        a list of available fields that can be request via fields argument. The endpoint
        /iserver/accounts must be called prior to /iserver/marketdata/snapshot. First
        /snapshot endpoint call for given conid will initiate the market data request.
        To receive all available fields the /snapshot endpoint will need to be called
        several times.

        Query parameters:
        1. conids: list of conids separated by comma
        2. (optional) since: time period since which updates are required.
        uses epoch time with milliseconds.
        3. (optional) fields: list of fields separated by comma
        """

        # call iserver/accounts endpoint
        self.get_accounts()

        # define request components
        endpoint = 'iserver/marketdata/snapshot'
        req_type = 'GET'
        if fields is not None:
            payload = {
                'conids': conids,
                'fields': fields
            }
        else:
            payload = {
                'conids': conids
            }

        content = self._make_request(endpoint = endpoint, req_type = req_type, params = payload)

        return content

    def kill_market_data(self):
        """
        Cancel all market data request(s). To cancel market data for given conid, see
        /iserver/marketdata/{conid}/unsubscribe.
        """

        # define request components
        endpoint = 'iserver/marketdata/unsubscribeall'
        req_type = 'GET'

        content = self._make_request(endpoint = endpoint, req_type = req_type)

        return content

