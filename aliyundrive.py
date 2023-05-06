import re
import json
import time
import ecdsa
import random
import hashlib
import requests
from base64 import b64encode
from cache import get_cache, set_cache, del_cache

base_headers = {
    'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36',
    'Referer': 'https://www.aliyundrive.com/',
}

class AliyunDrive():
    regex_share_id = re.compile(
        r'www.aliyundrive.com\/s\/([^\/]+)(\/folder\/([^\/]+))?')
    cache = {}

    def list_items(self, parent_item=None, display_file_size=True):
        if parent_item is None:
            return 'Lapse'
        m = self.regex_share_id.search(parent_item['id'])
        share_id = m.group(1)
        file_id = m.group(3)

        r = requests.post(
            'https://api.aliyundrive.com/adrive/v3/share_link/get_share_by_anonymous',
            json={'share_id': share_id},
            headers=base_headers,
            verify=False)
        share_info = r.json()

        if not 'file_infos' in share_info or len(share_info['file_infos']) == 0:
            return 'Lapse'

        file_info = None
        if file_id:
            for fi in share_info['file_infos']:
                if fi['file_id'] == file_id:
                    file_info = fi
                    break
            if file_info is None:
                file_info = {}
                if 'file_type' not in parent_item['params']:
                    share_token = self._get_share_token(share_id)
                    headers = base_headers.copy()
                    headers['x-share-token'] = share_token

                    r = requests.post(
                        'https://api.aliyundrive.com/adrive/v2/file/get_by_share',
                        json={
                            'fields':
                                '*',
                            'file_id':
                                file_id,
                            'image_thumbnail_process':
                                'image/resize,w_400/format,jpeg',
                            'image_url_process':
                                'image/resize,w_375/format,jpeg',
                            'share_id':
                                share_id,
                            'video_thumbnail_process':
                                'video/snapshot,t_1000,f_jpg,ar_auto,w_375',
                        },
                        headers=headers,
                        verify=False)
                    file_info = r.json()
                else:
                    file_info['type'] = parent_item['params']['file_type']
        else:
            if len(share_info['file_infos']) == 0:
                return 'lapse'
            file_info = share_info['file_infos'][0]
            file_id = file_info['file_id']

        parent_file_id = None
        if file_info['type'] == 'folder':
            parent_file_id = file_id
        elif file_info['type'] == 'file' and file_info['category'] == 'video':
            parent_file_id = 'root'
        else:
            return 'Lapse'

        dir_infos, video_infos, subtitle_infos = self._list_files(
            share_id,
            parent_file_id,
        )

        items = []

        for dir_info in dir_infos:
            items.append({
                'type': 'directory',
                'id': 'https://www.aliyundrive.com/s/{}/folder/{}'.format(share_id, dir_info['file_id']),
                'name': dir_info['name'],
                'cover': share_info['avatar'],
                'params': {
                    'pf': 'ali',
                    'type': 'category',
                    'file_type': dir_info['type']}
            })

        subtitles = []
        subtitle_infos.sort(key=lambda x: x['name'])
        for subtitle_info in subtitle_infos:
            subtitles.append({'name': subtitle_info['name'],
                              'params': {
                                  'share_id': subtitle_info['share_id'],
                                  'file_id': subtitle_info['file_id'],
                                  'drive_id': subtitle_info['drive_id'],
                              }})

        video_infos.sort(key=lambda x: x['name'])
        for video_info in video_infos:
            sources = [{'name': '原画',
                        'params':{
                            'template_id': '',
                            'share_id': video_info['share_id'],
                            'file_id': video_info['file_id'],
                            'drive_id': video_info['drive_id'],
                            'pf': 'ali'
                        }},
                        {'name': '超清',
                        'params': {
                            'template_id': 'FHD',
                            'share_id': video_info['share_id'],
                            'file_id': video_info['file_id'],
                            'drive_id': video_info['drive_id'],
                            'pf': 'ali'
                        }},
                        {'name': '高清',
                        'params': {
                            'template_id': 'HD',
                            'share_id': video_info['share_id'],
                            'file_id': video_info['file_id'],
                            'drive_id': video_info['drive_id'],
                            'pf': 'ali'
                        }},
                        {'name': '标清',
                        'params': {
                            'template_id': 'SD',
                            'share_id': video_info['share_id'],
                            'file_id': video_info['file_id'],
                            'drive_id': video_info['drive_id'],
                            'pf': 'ali'
                        }},
            ]

            if display_file_size:
                desc = '文件大小：{}\n{}'.format(self._sizeof_fmt(video_info['size']), parent_item['id'])
            else:
                desc = '文件大小：{}'.format(self._sizeof_fmt(video_info['size']), parent_item['id'])

            items.append({
                'type': 'file',
                'name': video_info['name'].strip(),
                'sources': sources,
                'cover': share_info['avatar'],
                'description': desc,
                'subtitles': subtitles,
                'params': {
                    'pf': 'ali',
                    'type': 'video',
                    'file_type': video_info['type']
                }})
        if len(items) == 0:
            return 'None'
        return items

    def resolve_play_url(self, source_params):
        if len(source_params['template_id']) == 0:
            params = source_params.copy()
            b64encode(json.dumps(params).encode("utf-8")).decode("utf-8")
            return '/proxy_download_file?params=' + b64encode(json.dumps(params).encode("utf-8")).decode("utf-8")
        else:
            return '/proxy_preview_m3u8?params=' + b64encode(json.dumps(source_params).encode("utf-8")).decode("utf-8")

    def _get_auth(self, token):
        key = 'aliyundrive:auth'
        data = self._get_cache(key)
        if data:
            return data
        headers = base_headers.copy()
        r = requests.post('https://auth.aliyundrive.com/v2/account/token',
                          json={
                              'refresh_token': token,
                              'grant_type': 'refresh_token'
                          },
                          headers=headers,
                          verify=False)
        data = r.json()
        if 'token_type' not in data:
            return 'Token'
        authorization = '{} {}'.format(data['token_type'], data['access_token'])
        expires_at = int(time.time()) + int(data['expires_in'] / 2)

        headers['authorization'] = authorization
        url = 'https://open.aliyundrive.com/oauth/users/authorize?client_id=76917ccccd4441c39457a04f6084fb2f&redirect_uri=https://alist.nn.ci/tool/aliyundrive/callback&scope=user:base,file:all:read,file:all:write&state='
        r = requests.post(url,
                          json={
                              'authorize': 1,
                              'scope': 'user:base,file:all:read,file:all:write'
                          },
                          headers=headers)
        code = re.search(r'code=(.*?)\"', r.text).group(1)
        r = requests.post('https://api.nn.ci/alist/ali_open/code',
                          json={
                              'code': code,
                              'grant_type': 'authorization_code'
                          },
                          headers=headers)

        opdata = json.loads(r.text)
        try:
            opentoken = opdata['refresh_token']
            opauthorization = '{} {}'.format(opdata['token_type'], opdata['access_token'])
        except:
            opentoken = ''
            opauthorization = ''
        auth = {
            'opentoken': opentoken,
            'opauthorization': opauthorization,
            'authorization': authorization,
            'device_id': data['device_id'],
            'user_id': data['user_id'],
            'drive_id': data['default_drive_id'],
            'expires_at': expires_at
        }

        self._set_cache(key, auth)
        return auth

    def _get_signature(self, token):
        auth = self._get_auth(token)
        key = 'aliyundrive:signature'
        data = self._get_cache(key)
        if data and data['device_id'] == auth['device_id'] and data['user_id'] == auth['user_id']:
            return data['signature']

        app_id = '5dde4e1bdf9e4966b387ba58f4b3fdc3'
        nonce = 0
        private_key = random.randint(1, 2 ** 256 - 1)
        ecc_pri = ecdsa.SigningKey.from_secret_exponent(private_key,
                                                        curve=ecdsa.SECP256k1)
        ecc_pub = ecc_pri.get_verifying_key()
        public_key = "04" + ecc_pub.to_string().hex()
        sign_dat = ecc_pri.sign(':'.join(
            [app_id, auth['device_id'], auth['user_id'],
             str(nonce)]).encode('utf-8'),
                                entropy=None,
                                hashfunc=hashlib.sha256)
        signature = sign_dat.hex() + "01"

        headers = base_headers.copy()
        headers['authorization'] = auth['authorization']
        headers['x-device-id'] = auth['device_id']
        headers['x-signature'] = signature

        r = requests.post(
            'https://api.aliyundrive.com/users/v1/users/device/create_session',
            json={
                'deviceName': 'Edge浏览器',
                'modelName': 'Windows网页版',
                'pubKey': public_key,
            },
            headers=headers,
            verify=False)

        result = r.json()
        if 'success' not in result or not result['success']:
            return 'Session'

        self._set_cache(
            key, {
                'device_id': auth['device_id'],
                'user_id': auth['user_id'],
                'signature': signature,
            })
        return signature

    def _get_share_token(self, share_id, share_pwd=''):
        key = 'aliyundrive:share_token'
        data = self._get_cache(key)
        if data:
            if data['share_id'] == share_id and data['share_pwd'] == share_pwd:
                return data['share_token']

        r = requests.post(
            'https://api.aliyundrive.com/v2/share_link/get_share_token',
            json={
                'share_id': share_id,
                'share_pwd': share_pwd
            },
            headers=base_headers,
            verify=False)
        data = r.json()

        share_token = data['share_token']
        expires_at = int(time.time()) + int(data['expires_in'] / 2)
        self._set_cache(
            key, {
                'share_token': share_token,
                'expires_at': expires_at,
                'share_id': share_id,
                'share_pwd': share_pwd
            })
        return share_token

    def _list_files(self, share_id, parent_file_id):
        dir_infos = []
        video_infos = []
        subtitle_infos = []

        marker = ''
        share_token = self._get_share_token(share_id)
        headers = base_headers.copy()
        headers['x-share-token'] = share_token
        for page in range(1, 51):
            if page >= 2 and len(marker) == 0:
                break

            r = requests.post(
                'https://api.aliyundrive.com/adrive/v3/file/list',
                json={
                    "image_thumbnail_process":
                        "image/resize,w_160/format,jpeg",
                    "image_url_process": "image/resize,w_1920/format,jpeg",
                    "limit": 200,
                    "order_by": "updated_at",
                    "order_direction": "DESC",
                    "parent_file_id": parent_file_id,
                    "share_id": share_id,
                    "video_thumbnail_process":
                        "video/snapshot,t_1000,f_jpg,ar_auto,w_300",
                    'marker': marker,
                },
                headers=headers,
                verify=False)
            data = r.json()

            for item in data['items']:
                if item['type'] == 'folder':
                    dir_infos.append(item)
                elif item['type'] == 'file' and item['category'] == 'video':
                    video_infos.append(item)
                elif item['type'] == 'file' and item['file_extension'] in [
                    'srt', 'ass', 'vtt'
                ]:
                    subtitle_infos.append(item)

            marker = data['next_marker']

        return dir_infos, video_infos, subtitle_infos

    def _get_m3u8_cache(self, baseurl, share_id, file_id, template_id, token, retry=False):
        key = 'aliyundrive:m3u8'
        data = self._get_cache(key)
        if data:
            if data['share_id'] == share_id and data['file_id'] == file_id and data['template_id'] == template_id:
                return data['m3u8'], data['media_urls']

        auth = self._get_auth(token)
        share_token = self._get_share_token(share_id)

        headers = base_headers.copy()
        headers['authorization'] = auth['authorization']
        headers['x-share-token'] = share_token
        headers['x-device-id'] = auth['device_id']
        headers['x-signature'] = self._get_signature(token)
        r = requests.post(
            'https://api.aliyundrive.com/v2/file/get_share_link_video_preview_play_info',
            json={
                'share_id': share_id,
                'category': 'live_transcoding',
                'file_id': file_id,
                'template_id': '',
            },
            headers=headers,
            verify=False)

        data = r.json()

        if 'video_preview_play_info' not in data:
            self._del_cache('aliyundrive:signature')
            if retry:
                return self._get_m3u8_cache(baseurl, share_id, file_id, template_id, token, False)
            else:
                raise Exception(r.text)

        preview_url = ''
        for t in data['video_preview_play_info']['live_transcoding_task_list']:
            if t['template_id'] == template_id:
                preview_url = t['url']
                break

        r = requests.get(preview_url,
                         headers=base_headers.copy(),
                         allow_redirects=False,
                         verify=False)
        preview_url = r.headers['Location']

        lines = []
        media_urls = []
        r = requests.get(preview_url,
                         headers=base_headers.copy(),
                         stream=True,
                         verify=False)
        media_id = 0
        for line in r.iter_lines():
            line = line.decode()
            if 'x-oss-expires' in line:
                media_url = preview_url[:preview_url.rindex('/') + 1] + line
                media_urls.append(media_url)
                params = {
                        'share_id': share_id,
                        'file_id': file_id,
                        'template_id': template_id,
                        'media_id': media_id,
                        'token': token
                    }
                params = json.dumps(params)
                params = b64encode(params.encode("utf-8")).decode("utf-8")
                proxyhead = baseurl + '/proxy_preview_media?params='
                line = proxyhead + params
                media_id += 1
            lines.append(line)
        m3u8 = '\n'.join(lines)

        self._set_cache(
            key, {
                'share_id': share_id,
                'file_id': file_id,
                'template_id': template_id,
                'm3u8': m3u8,
                'media_urls': media_urls,
                'expires_at': int(time.time()) + 60,
            })

        return m3u8, media_urls

    def _get_download_url(self, params, token, oldapi=False):
        share_id = params['share_id']
        file_id = params['file_id']
        key = 'aliyundrive:download_url:{}:{}'.format(share_id, file_id)
        data = self._get_cache(key)
        if data:
            return data['download_url']

        auth = self._get_auth(token)
        share_token = self._get_share_token(share_id)

        headers = base_headers.copy()
        headers['x-share-token'] = share_token
        headers['authorization'] = auth['authorization']

        temp_ids = self._get_cache('temp_ids')
        if temp_ids is None:
            temp_ids = []

        if auth['opentoken'] != '' and not oldapi:
            try:
                to_drive_id = auth['drive_id']
                headers['Content-Type'] = 'application/json'
                json_str = "{\"requests\":[{\"body\":{\"file_id\":\"%s\",\"share_id\":\"%s\",\"auto_rename\":true,\"to_parent_file_id\":\"root\",\"to_drive_id\":\"%s\"},\"headers\":{\"Content-Type\":\"application/json\"},\"id\":\"0\",\"method\":\"POST\",\"url\":\"/file/copy\"}],\"resource\":\"file\"}" % (file_id, share_id, to_drive_id)
                r = requests.post('https://api.aliyundrive.com/v3/batch', data=json_str, headers=headers)
                my_file_id = json.loads(r.text)['responses'][0]['body']['file_id']
                temp_ids.append(my_file_id)

                headers['authorization'] = auth['opauthorization']
                r = requests.post('https://open.aliyundrive.com/adrive/v1.0/openFile/getDownloadUrl', json={'file_id': my_file_id, 'drive_id': to_drive_id}, headers=headers)
                data = json.loads(r.text)
                download_url = data['url']
            except:
                oldapi = True
            finally:
                del_ids = []
                headers['authorization'] = auth['authorization']
                for file_id in temp_ids:
                    json_str = '{\"requests\":[{\"body\":{\"drive_id\":\"%s\",\"file_id\":\"%s\"},\"headers\":{\"Content-Type\":\"application/json\"},\"id\":\"%s\",\"method\":\"POST\",\"url\":\"/file/delete\"}],\"resource\":\"file\"}' % (
                    to_drive_id, file_id, file_id)
                    del_times = 0
                    while del_times < 5:
                        del_times += 1
                        r = requests.post('https://api.aliyundrive.com/v3/batch', data=json_str, headers=headers)
                        if r.status_code == 200 and r.json()['responses'][0]['status'] != 204:
                            if r.json()['responses'][0]['status'] == 404:
                                del_ids.append(file_id)
                                break
                            time.sleep(1)
                        elif r.json()['responses'][0]['status'] == 204:
                            break
                        else:
                            time.sleep(1)

                for file_id in del_ids:
                    temp_ids.remove(file_id)

                if temp_ids != []:
                    self._set_cache('temp_ids', temp_ids)
        elif auth['opentoken'] == '':
            oldapi = True
        if oldapi:
            r = requests.post('https://api.aliyundrive.com/v2/file/get_share_link_download_url',
                json={'share_id': share_id, 'file_id': file_id, 'expires_sec': 7200},
                headers=headers,
                verify=False)
            data = r.json()
            r = requests.get(data['download_url'], headers=base_headers.copy(), allow_redirects=False, verify=False)
            download_url = r.headers['Location']

        self._set_cache(
            key, {
                'download_url': download_url,
                'expires_at': int(time.time()) + 600,
                'share_id': share_id,
                'file_id': file_id,
            })
        return download_url

    def _sizeof_fmt(self, num, suffix="B"):
        for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
            if num < 1024.0:
                return f"{num:3.1f} {unit}{suffix}"
            num /= 1024.0
        return f"{num:.1f}Yi{suffix}"

    def _get_cache(self, key):
        data = get_cache(key)
        if data and data != '':
            data = json.loads(data)
            if 'expires_at' in data and data['expires_at'] >= int(time.time()) or 'signature' in data or key == 'temp_ids':
                return data
        return None

    def _set_cache(self, key, value):
        set_cache(key, json.dumps(value))

    def _del_cache(self, key):
        del_cache(key)

