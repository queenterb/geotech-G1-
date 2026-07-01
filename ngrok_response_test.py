import requests, urllib3
urllib3.disable_warnings()
urls = [
    'http://127.0.0.1:8000/',
    'http://127.0.0.1:8000/login',
    'http://127.0.0.1:8000/healthz',
    'https://broker-error-sublevel.ngrok-free.dev/',
    'https://broker-error-sublevel.ngrok-free.dev/login',
    'https://broker-error-sublevel.ngrok-free.dev/healthz',
]
for u in urls:
    try:
        r = requests.get(u, timeout=15, verify=False, allow_redirects=True)
        print('URL', u)
        print('STATUS', r.status_code)
        print('LOCATION', r.headers.get('Location'))
        print('CONTENT-TYPE', r.headers.get('content-type'))
        print(r.text[:1000].replace('\n', ' '))
    except Exception as e:
        print('URL', u, 'ERROR', type(e).__name__, e)
    print('---')
