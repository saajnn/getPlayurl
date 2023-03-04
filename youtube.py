import os
import re
import json
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

if not 'stock5' in locals():
    stock5 = 'off'
if not 'stock5Host' in locals():
    stock5Host = '127.0.0.1'
if not 'stock5Port' in locals():
    stock5Port = 1081

if stock5 == 'on':
    import socket
    import socks
    socks.set_default_proxy(socks.SOCKS5, stock5Host, int(stock5Port))
    socket.socket = socks.socksocket


class YouTuBe:
    def get_real_url(self, rid):

        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"}
        url = 'https://www.youtube.com/watch?v={}'.format(rid)
        r = requests.get(url=url, headers=header, timeout=10)
        jostr_re = re.compile('var ytInitialPlayerResponse =(.*?});')
        jostr = jostr_re.findall(r.text)
        if not jostr:
            return ''
        jo = json.loads(jostr[0])
        if 'streamingData' in jo and 'hlsManifestUrl' in jo['streamingData']:
            if type(jo['streamingData']['hlsManifestUrl']) is str:
                url = jo['streamingData']['hlsManifestUrl']
            elif type(jo['streamingData']['hlsManifestUrl']) is list:
                url = jo['streamingData']['hlsManifestUrl'][0]
            else:
                return ''
            r = requests.get(url, headers=header, timeout=10)
            m3u8List = r.text.strip('\n').split('\n')
            url = m3u8List[-1]
        else:
            return ''
        return url
