import json
import requests

class BiliBili:
    def get_real_url(self, rid):
        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"}
        url = 'https://api.live.bilibili.com/room/v1/Room/playUrl?cid={0}&qn=20000&platform=h5'.format(rid)
        r = requests.get(url=url, headers=header)
        jo = json.loads(r.text)
        if 'data' in jo:
            url = jo['data']['durl'][0]['url']
        else:
            url = ''
        return url
