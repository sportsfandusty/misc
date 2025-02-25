import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.5',
    # 'Accept-Encoding': 'gzip, deflate, br, zstd',
    'x-px-context': '_px3=8c02b51d985fab3219775f6c14a01bf3f1987ebdae114ebf3306662168719da6:P1IZSZz4h34MXcQchRQktWmt6T/wUaAFJvmuCKZmpDjl+3vKqIwko0TZS1zP4CB4uIclwfL8AJZK+sWU0Vvnww==:1000:QUDasbLg/6PmGvVGuPkgF27E3IL+bl/4mLzxc3Ri55d6Qa+WY0F9Hh4sh3pIM5Z4AqV7BRpv/xP9LqNYSOfOAerH57TKN9bitFgOseDG/gss1WMQ8jYKHueeuQc7G/PgfFKBELt9PkmlJpnpdRzANBZlcqdSxojZJ/TJt7wMjNbSBWdJAZuvlxIq89RiP/0LH5XgqxjGXDQ2VXM24ZIaexobw2+7pjpcT1z0Ld2QRsw=;_pxvid=284b83f1-a67b-11ef-80fa-d720d0310285;pxcts=d3c53c80-cf7a-11ef-bb31-59b72ac82bb9;',
    'Origin': 'https://sportsbook.fanduel.com',
    'DNT': '1',
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
    'Referer': 'https://sportsbook.fanduel.com/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
}

params = {
    '_ak': 'FhMFpcPWXMeyZxOx',
    'eventId': '33904281',
    'tab': 'popular',
    'pulseScalingEnable': 'true',
    'useCombinedTouchdownsVirtualMarket': 'true',
    'usePulse': 'true',
    'useQuickBets': 'true',
    'useQuickBetsNFL': 'true',
}

response = requests.get('https://sbapi.oh.sportsbook.fanduel.com/api/event-page', params=params, headers=headers)
data=response.json()
print(json.dumps(data, indent=4)) 