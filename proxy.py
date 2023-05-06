import os
import re
import json
import requests
from base64 import b64encode

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

if not 'proxyHost' in locals():
    proxyHost = '127.0.0.1'
if not 'proxyPort' in locals():
    proxyPort = 1081
if not 'proxyProtocol' in locals():
    proxyProtocol = 'http'

class Proxy:
    def proxy_m3u8(self, url, baseurl, header, proxy='off'):
        m3u8List = []
        proxyhead = baseurl + '/proxy?ts_url='
        if proxy == 'on':
            proxies = {
                "http": "{}://{}:{}".format(proxyProtocol, proxyHost, proxyPort),
                "https": "{}://{}:{}".format(proxyProtocol, proxyHost, proxyPort)
            }
        else:
            proxies = {}
        try:
            r = requests.get(url, headers=header, stream=True, allow_redirects=False, verify=False, proxies=proxies)
            if 'Content-Type' in r.headers and 'video' in r.headers['Content-Type']:
                r.close()
                url = '/proxy?ts_url=' + b64encode(url.encode("utf-8")).decode("utf-8") + '&headers=' + b64encode(json.dumps(header).encode("utf-8")).decode("utf-8")
                return url, 'False'
            elif 'Location' in r.headers and '#EXTM3U' not in r.text:
                r.close()
                url = r.headers['Location']
                r = requests.get(url, headers=header, stream=True, allow_redirects=False, verify=False, proxies=proxies)
            start = 0
            posD = -1
            posDISList = []
            for line in r.iter_lines(8096):
                line = line.decode('utf-8', 'ignore')
                EXK_str = ''
                if len(line) > 0 and "EXT-X-KEY" in line:
                    EXK_str = line
                    line = re.search(r'URI=(.*)', line).group(1).replace('"', '').strip().split(',')[0]
                    oURI = line
                if len(line) > 0 and not line.startswith('#'):
                    if line.find(".m3u") != -1 and not line.find(".ts") != -1:
                        m3u8_url = line
                        return self.proxy_m3u8(m3u8_url, baseurl, header)
                    if not line.startswith('http'):
                        if line.startswith('/'):
                            line = url[:url.index('/', 8)] + line
                        else:
                            line = url[:url.rindex('/') + 1] + line
                    line = proxyhead + b64encode(line.encode("utf-8")).decode("utf-8") + '&headers=' + b64encode(json.dumps(header).encode("utf-8")).decode("utf-8")+ '&proxy=' + proxy
                if EXK_str != '':
                    line = EXK_str.replace(oURI, line)
                m3u8List.append(line)
                if m3u8List[posD + 1:].count('#EXT-X-DISCONTINUITY') != 0:
                    posD = m3u8List.index('#EXT-X-DISCONTINUITY', posD + 1)
                    if posD > 0 and not m3u8List[posD - 1].startswith('#'):
                        posDISList.append(posD)
            if len(posDISList) > 0:
                for posDIS in posDISList:
                    if posDIS > 0:
                        if start == 0:
                            start = posDIS
                            end = -1
                            continue
                        if end == -1:
                            end = posDIS + 1
            if start != 0 and end != -1:
                del m3u8List[start:end]
                start = 0
            m3u8str = "\n".join(m3u8List).strip('\n')
            return m3u8str, 'True'
        except Exception:
            return '', 'Erro'
        finally:
            try:
                r.close()
            except:
                pass

