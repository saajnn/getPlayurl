import os
import re
import time
import json
import html
import base64
import hashlib
import requests
import urllib.parse

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
if not 'location' in locals():
    location = 'abroad'


class HuYa:
    def get_real_url(self, rid):
        header = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36'
        }
        url = 'https://www.huya.com/' + rid
        r = requests.get(url, headers=header)
        streamInfo = re.findall(r'stream: ([\s\S]*?)\n', r.text)
        if (len(streamInfo) > 0):
            liveData = json.loads(streamInfo[0])
        else:
            streamInfo = re.findall(r'"stream": "([\s\S]*?)"', r.text)
            if (len(streamInfo) > 0):
                liveDataBase64 = streamInfo[0]
                liveData = json.loads(str(base64.b64decode(liveDataBase64), 'utf-8'))
            else:
                return ''
        streamInfoList = liveData['data'][0]['gameStreamInfoList']
        urlList=[]
        for streamInfo in streamInfoList:
            hls_url = streamInfo['sHlsUrl'] + '/' + streamInfo['sStreamName'] + '.' + streamInfo['sHlsUrlSuffix']
            srcAntiCode = html.unescape(streamInfo['sHlsAntiCode'])
            c = srcAntiCode.split('&')
            c = [i for i in c if i != '']
            n = {i.split('=')[0]: i.split('=')[1] for i in c}
            fm = urllib.parse.unquote(n['fm'])
            u = base64.b64decode(fm).decode('utf-8')
            hash_prefix = u.split('_')[0]
            ctype = n.get('ctype', '')
            txyp = n.get('txyp', '')
            fs = n.get('fs', '')
            t = n.get('t', '')
            seqid = str(int(time.time() * 1e3 + 1463993859134))
            wsTime = hex(int(time.time()) + 3600).replace('0x', '')
            hash = hashlib.md5('_'.join([hash_prefix, '1463993859134', streamInfo['sStreamName'],
                                         hashlib.md5((seqid + '|' + ctype + '|' + t).encode('utf-8')).hexdigest(),
                                         wsTime]).encode('utf-8')).hexdigest()
            ratio = ''
            url = "{}?wsSecret={}&wsTime={}&seqid={}&ctype={}&ver=1&txyp={}&fs={}&ratio={}&u={}&t={}&sv=2107230339".format(
                hls_url, hash, wsTime, seqid, ctype, txyp, fs, ratio, '1463993859134', t)
            urlList.append(url)
        if location == 'abroad':
            url = urlList[0]
        else:
            for url in urlList:
                r = requests.get(url, headers=header, stream=True)
                if r.status_code != 200:
                    r.close()
                    continue
                for line in r.iter_lines(8096):
                    line = line.decode('utf-8', 'ignore')
                    if len(line) > 0 and not line.startswith('#'):
                        if not line.startswith('http'):
                            if line.startswith('/'):
                                line = url[:url.index('/', 8)] + line
                            else:
                                line = url[:url.rindex('/') + 1] + line
                        if line.startswith('http'):
                            r.close()
                            break
                r = requests.get(line, headers=header, stream=True)
                count = 0
                count_tmp = 0
                stime = time.time()
                i = 0
                speed = 0
                for chunk in r.iter_content(chunk_size=40960):
                    if chunk:
                        if i == 2:
                            r.close()
                            break
                        count += len(chunk)
                        sptime = time.time() - stime
                        if count == int(r.headers['content-length']):
                            speed = int((count - count_tmp) / sptime)
                        elif sptime > 0:
                            speed = int((count - count_tmp) / sptime)
                            stime = time.time()
                            count_tmp = count
                            i = i + 1
                if speed > 102400:
                    break
        return url