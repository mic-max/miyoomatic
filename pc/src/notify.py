# Python
import http
import urllib

def send_push(pushover_token: str, message: str):
    # TODO: get this working, make app online
    conn = http.client.HTTPSConnection('api.pushover.net:443')
    conn.request('POST', '/1/messages.json',
    urllib.parse.urlencode({
        'token': 'abc123',
        'user': pushover_token,
        'message': message,
    }), { 'Content-type': 'application/x-www-form-urlencoded' })
    conn.getresponse()