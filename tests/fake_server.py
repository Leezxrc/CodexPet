"""Tiny protocol peer used to exercise subprocess lifecycle without network."""
import json
import sys
import time

mode = sys.argv[1]
for line in sys.stdin:
    request = json.loads(line)
    method = request.get('method')
    if mode == 'eof':
        sys.exit(0)
    if mode == 'hang':
        time.sleep(60)
    if method == 'initialize':
        print('ignored startup noise', flush=True)
        print(json.dumps({'method': 'unrelated/notification', 'params': {}}), flush=True)
        print(json.dumps({'id': 99, 'result': {}}), flush=True)
        print(json.dumps({'id': request['id'], 'result': {'userAgent': 'test'}}), flush=True)
    elif method == 'initialized':
        continue
    elif method == 'account/read':
        assert request['params'] == {'refreshToken': False}
        account = None if mode == 'signed_out' else {'type': 'apiKey' if mode == 'api_key' else 'chatgpt'}
        print(json.dumps({'id': request['id'], 'result': {'account': account}}), flush=True)
    elif method == 'account/rateLimits/read':
        if mode == 'auth':
            print(json.dumps({'id': request['id'], 'error': {'code': 401, 'message': 'auth token secret-must-not-leak'}}), flush=True)
        else:
            print(json.dumps({'id': request['id'], 'result': {
                'rateLimits': {'primary': {'usedPercent': 42, 'windowDurationMins': 300},
                               'credits': {'balance': '12.3400', 'unlimited': False}},
                'rateLimitResetCredits': {'availableCount': 2, 'credits': None}}}), flush=True)
    else:
        raise RuntimeError('Unexpected non-read-only RPC')
