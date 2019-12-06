import urllib.parse as up
import mechanize
import requests


def tdlogin(redirect, consumer_key, username, password):
    client_id = consumer_key + '@AMER.OAUTHAP'
    url = 'https://auth.tdameritrade.com/auth?response_type=code&redirect_uri=' + up.quote(redirect) + '&client_id=' + up.quote(client_id)

    # print(url)

    br = mechanize.Browser()
    br.set_handle_robots(False)
    br.open(url)
    br.select_form(nr=0)
    # print(br.form)
    br.form['su_username'] = username
    br.form['su_password'] = password
    req = br.submit(id="accept")
    # print(req.code)
    br.select_form(nr=0)
    # print(br.form)
    br.set_handle_redirect(False)
    try:
        req = br.submit(id="accept")
    except mechanize._mechanize.HTTPError as response:
        # print(response.hdrs)
        location = response.headers["Location"]
        # print(response.geturl())
        # pass
    # print(location)
    o = up.urlparse(location)
    code = up.parse_qs(o.query)['code'][0]
    # print(code)
    # return code

    resp = requests.post('https://api.tdameritrade.com/v1/oauth2/token',
                         headers={'Content-Type': 'application/x-www-form-urlencoded'},
                         data={'grant_type': 'authorization_code',
                               'refresh_token': '',
                               'access_type': 'offline',
                               'code': code,
                               'client_id': client_id,
                               'redirect_uri': redirect})

    return resp.json()