import re
import json
import requests

class DouYin:
    def get_roomid(self, rid):
        if rid.isnumeric():
            mode = 'web'
        else:
            header = {
                'Authority': 'v.douyin.com',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1',
            }
            url = 'https://v.douyin.com/' + rid
            r = requests.head(url, headers=header)
            if 'location' in r.headers:
                url = r.headers['location']
                rid = re.search(r'\d{19}', url).group(0)
                mode = 'app'
        return rid, mode

    def get_real_url(self, rid):
        if not 'mode' in locals() or not 'rid' in locals():
            rid, mode = self.get_roomid(rid)
        if mode == 'app':
            params = {
                "aid": "6383",
                "live_id": "1",
                "device_platform": "web",
                "language": "zh-CN",
                "enter_from": "web_search",
                "cookie_enabled": "true",
                "screen_width": "1920",
                "screen_height": "1080",
                "browser_language": "zh-CN",
                "browser_name": "Chrome",
                "room_id": rid,
                "scene": "pc_stream_4k",
            }
            url = "https://live.douyin.com/webcast/room/info_by_scene/?"
            r = requests.get(url, params=params)
            jo = json.loads(r.text)['data']
            if 'stream_url' in jo:
                if "Hls" in jo["stream_url"]["live_core_sdk_data"]["pull_data"]:
                    medias = jo["stream_url"]["live_core_sdk_data"]["pull_data"]["Hls"]
                    urlDict = {}
                    for media in medias:
                        if media['quality_name'] == 'origin':
                            urlDict.update({0: media['url']})
                        elif media['quality_name'] == 'uhd':
                            urlDict.update({1: media['url']})
                        elif media['quality_name'] == 'hd':
                            urlDict.update({2: media['url']})
                        elif media['quality_name'] == 'sd':
                            urlDict.update({3: media['url']})
                        elif media['quality_name'] == 'ld':
                            urlDict.update({4: media['url']})
                    key = sorted(urlDict)[0]
                    url = urlDict[key]
            else:
                url = ''
        else:
            url = "https://live.douyin.com/" + rid
            header = {
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
                "upgrade-insecure-requests": "1",
            }
            session = requests.session()
            r = session.get(url, headers=header)
            cookies_re = re.compile('(?i)__ac_nonce=(.*?);')
            cookies = cookies_re.findall(r.headers["Set-Cookie"])
            cookie = requests.cookies.create_cookie("__ac_nonce", cookies[0])
            session.cookies.set_cookie(cookie)
            r = session.get(url, headers=header)
            body = r.content.decode('utf-8')
            str = requests.utils.unquote(body)
            roomid_re = re.compile('(?i)\\"roomid\\":\\"([0-9]+)\\"')
            roomid = roomid_re.findall(str)
            if not roomid:
                return ''
            hls_re = re.compile('(?i)\\"id_str\\":\\"' + roomid[0] + '\\"[\\s\\S]*?\\"hls_pull_url\\"')
            hls = hls_re.findall(str)
            hlsmap_re = re.compile('(?i)\\"hls_pull_url_map\\"[\\s\\S]*?}')
            hlsmap = hlsmap_re.findall(hls[0])
            if not hlsmap:
                return ''
            mediamap = json.loads("{" + hlsmap[0] + "}")
            urlDict = {}
            for ratio in mediamap["hls_pull_url_map"]:
                if ratio == 'FULL_HD1':
                    urlDict.update({0: mediamap["hls_pull_url_map"][ratio]})
                elif ratio == 'HD1':
                    urlDict.update({1: mediamap["hls_pull_url_map"][ratio]})
                elif ratio == 'SD1':
                    urlDict.update({2: mediamap["hls_pull_url_map"][ratio]})
                else:
                    urlDict.update({3: mediamap["hls_pull_url_map"][ratio]})
            key = sorted(urlDict)[0]
            url = urlDict[key]
        return url