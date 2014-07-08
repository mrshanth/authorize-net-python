"""
This is an example of using Authorize.net's Direct Post Method.
This example is also extremely basic and serves to show just the basic flow of the DPM authorization method.

Take note that in this example, the amount is basically hardcoded to 9.99 as authorize.net expects a shopping cart / checkout
style experience. Where the total amount is calculated at the end before sending the transaction over.
"""
import hmac
import calendar

from datetime import datetime

from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware

from flask import Flask
from flask import request
from flask import render_template


app = Flask(__name__)

"""Replce with your login id from authorize.net"""
API_LOGIN_ID = 'YOUR_LOGIN_ID_HERE'

"""Replace with your authorize.net transaction key"""
TRANSACTION_KEY = 'YOUR_TRANSACTION_KEY_HERE'

"""
This is your base URL.
More than likely you will need to adjust firewall settings etc. as authorize.net will issue a POST request here.
Can be a domain name or IP address.
"""
DOMAIN = 'YOUR_DOMAIN_OR_IP:PORT'


def generate_fingerprint(transactionKey, loginId, sequenceNumber, timestamp, amount):
    """
    The fingerprint consists of an MD5 HMAC, using the assigned transactionKey.
    When creating the fingerprint it should be done at the last possible time and serves as a way for authorize.net
    to make sure what we sent from the client has not been tampered with. The fingerprint is generated on OUR server
    and the transactionKey that is used is NEVER sent to the client, so in theory, they have no way of reproducing
    the fingerprint.
    """
    return hmac.new(transactionKey, "%s^%s^%s^%s^US" % (loginId, sequenceNumber, timestamp, amount)).hexdigest()


def get_utc_timestamp_in_seconds():
    """Create a UTC timestamp in seconds for use in the fingerprint"""
    return calendar.timegm(datetime.utcnow().utctimetuple())


@app.route("/")
def index():
    """This is the starting point of this dance."""

    """The relayResponseUrl is where we want authorize.net to send the POST with the transaction response"""
    relayResponseUrl = '%s/relay' % DOMAIN

    """The sequence number is something that we would generate and can be basically any valid integer"""
    x_fp_sequence = '123'

    """UTC timestamp in seconds"""
    x_fp_timestamp = get_utc_timestamp_in_seconds()

    """The amount to use in the fingerprint creation"""
    amount = '9.99'

    """This is the actual hash value and is sent to authorize.net at which point they will reproduce and verify
    the hash with the form fields that are being sent over"""
    x_fp_hash = generate_fingerprint(TRANSACTION_KEY, API_LOGIN_ID, x_fp_sequence, x_fp_timestamp, amount)

    """Pass the needed data to the form fields so authorize.net will receive what they need to"""
    return render_template('index.html', apiLoginId=API_LOGIN_ID, relayResponseUrl=relayResponseUrl,
                           x_fp_sequence=x_fp_sequence, x_fp_timestamp=x_fp_timestamp,
                           x_fp_hash=x_fp_hash, amount=amount)


@app.route('/relay', methods=['POST'])
def relay():
    """This is the intermediary between the authorize.net response and the receipt page the user will see.
    At this point we need to return a bit of HTML to authorize.net so that the user's browser will be properly redirected.
    This keeps the user experience seamless as they won't appear to be redirected anwyhere"""

    # All of authorize.net's response information is within the post to this endpoint
    # Just for debugging, print all of this out
    for key, value in request.form.iteritems():
        print "%s: %s" % (key, value)

    """Anything that you want to display on the receipt page, needs to be sent as query parameters.
     All the query parameters will be passed onto the final page"""
    relayUrl = '%s/receipt?x_auth_code=%s' % (DOMAIN, request.form['x_auth_code'])
    return render_template('relay_response.html', relayUrl=relayUrl)


@app.route('/receipt')
def receipt():
    """This is the final page the user sees and completes our authorization dance. At this point, the user will
    see if the transaction was approved or not and whatever else we want them to see"""
    return render_template('receipt.html')


if __name__ == '__main__':
    run_simple('0.0.0.0', 5000, DispatcherMiddleware(app), use_reloader=True, use_debugger=True)
