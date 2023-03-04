# 获取斗鱼直播间的真实流媒体地址，默认最高画质
# 使用 https://github.com/wbt5/real-url/issues/185 中两位大佬@wjxgzz @4bbu6j5885o3gpv6ss8找到的的CDN，在此感谢！
import re
import time
import json
import hashlib
import quickjs
import requests

class DouYu:
    def get_roomid(self, rid):
        did = '10000000000000000000000000001501'
        t = str(int(time.time()))
        s = requests.Session()
        r = s.get('https://m.douyu.com/' + str(rid), timeout=30).text
        result = re.search(r'rid":(\d{1,8}),"vipId', r)
        if result:
            erro = False
            rid = result.group(1)
        else:
            erro = True
        return did, t, s, r, rid, erro

    def md5(self, data):
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def get_js(self, rid):
        if not 'did' in locals() or not 't' in locals() or not 's' in locals() or not 'r' in locals() or not 'rid' in locals() or not 'erro' in locals():
            did, t, s, r, rid, erro = self.get_roomid(rid)
        if erro:
            return ''
        result = re.search(r'(function ub98484234.*)\s(var.*)', r).group()
        func_ub9 = re.sub(r'eval.*;}', 'strc;}', result)
        js_func = quickjs.Function('ub98484234', func_ub9)
        res = js_func()
        v = re.search(r'v=(\d+)', res).group(1)
        rb = self.md5(rid + did + t + v)

        func_sign = re.sub(r'return rt;}\);?', 'return rt;}', res)
        func_sign = func_sign.replace('(function (', 'function sign(')
        func_sign = func_sign.replace('CryptoJS.MD5(cb).toString()', '"' + rb + '"')

        js_func = quickjs.Function('sign', func_sign)
        params = js_func(rid, did, t)
        params += '&ver=219032101&rid={}&rate=-1'.format(rid)

        url = 'https://m.douyu.com/api/room/ratestream'
        r = s.post(url, params=params, timeout=30)
        jo = json.loads(r.text)['data']

        if 'url' in jo:
            url = jo['url']
        else:
            url = ''
        return url

    def get_real_url(self, rid):
        url = self.get_js(rid)
        return url
