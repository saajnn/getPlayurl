import os
import requests

if os.path.exists('config.conf'):
    confList = open('config.conf', 'r', encoding='utf-8').read().strip('\n').split('\n')
    if confList != []:
        for conf in confList:
            conf = conf.replace('：', ':')
            if not conf.startswith('#'):
                confname = conf.split(':', 1)[0].strip()
                confvalue = conf.split(':', 1)[1]
                confvalue = confvalue.split('#')[0].strip()
                locals()[confname] = confvalue

if not 'port' in locals():
    port = 8150

def set_cache(key, value):
    value = value.encode()
    requests.post('http://127.0.0.1:{}/cache'.format(port), params={'key': key,}, data=value, headers={'Content-Length': str(len(value))})

def get_cache(key):
    r = requests.get('http://127.0.0.1:{}/cache'.format(port),params={'key': key})
    return r.text

def del_cache(key):
    requests.delete('http://127.0.0.1:{}/cache'.format(port),params={'key': key})