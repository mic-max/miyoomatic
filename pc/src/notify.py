# Python
import http.client
import urllib.parse


def send_push(api_token: str, user_token: str, message: str,
              title: str | None = None, priority: int = 0) -> None:
    payload = {
        'token': api_token,
        'user': user_token,
        'message': message,
        'priority': priority,
    }
    if title:
        payload['title'] = title
    conn = http.client.HTTPSConnection('api.pushover.net:443')
    conn.request(
        'POST', '/1/messages.json',
        urllib.parse.urlencode(payload),
        {'Content-type': 'application/x-www-form-urlencoded'},
    )
    conn.getresponse().read()
    conn.close()