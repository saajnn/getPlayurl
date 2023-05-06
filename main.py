import os
import json
import requests
from io import BytesIO
from urllib.parse import urlparse
from base64 import b64decode, b64encode
from flask import Flask, request, redirect, Response, render_template, send_from_directory

from proxy import Proxy
from huya import HuYa
from douyu import DouYu
from douyin import DouYin
from bilibili import BiliBili
from youtube import YouTuBe
from downloader import Downloader
from aliyundrive import AliyunDrive


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
if not 'proxyHost' in locals():
    proxyHost = '127.0.0.1'
if not 'proxyPort' in locals():
    proxyPort = 1081
if not 'proxyProtocol' in locals():
    proxyProtocol = 'http'

app = Flask(__name__)
class Spider():
    def get_playurl(self, rid, platform, proxy='off'):
        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"}
        if platform == 'huya':
            playurl = HuYa().get_real_url(rid)
        elif platform == 'douyu':
            playurl = DouYu().get_real_url(rid)
        elif platform == 'douyin':
            playurl = DouYin().get_real_url(rid)
        elif platform == 'bilibili':
            playurl = BiliBili().get_real_url(rid)
        elif platform == 'youtube':
            playurl = YouTuBe().get_real_url(rid, proxy)
        elif platform == 'link':
            playurl = rid
        else:
            playurl = ''
        return playurl, header


@app.route('/')
def web():
    return render_template('index.html')

data = {}
@app.route('/cache', methods=['POST', 'PUT', 'GET', 'DELETE'])
def handle_cache():
    methods = request.method
    key = request.args.get('key')
    if methods in ['POST', 'PUT']:
        body = request.data
        data[key] = body
        return body
    elif methods == 'GET':
        if key in data:
            return data[key]
        else:
            return ''
    else:
        data[key] = ''
        return ''

@app.route('/ali_list')
def ali_list():
    item = request.args.get('item')
    display_file_size = request.args.get('display_file_size')
    if item is None:
        return 'Erro'
    item = b64decode(item).decode("utf-8").replace('\'', '\"')
    jo = json.loads(item)
    if not display_file_size is None and display_file_size == 'True':
        display_file_size = True
    else:
        display_file_size = False
    data = AliyunDrive().list_items(jo, display_file_size)
    return data

@app.route('/ali_resolve')
def ali_resolve():
    item = request.args.get('item')
    if item is None:
        return 'Erro'
    item = b64decode(item).decode("utf-8").replace('\'', '\"')
    item = json.loads(item)
    data = AliyunDrive().resolve_play_url(item)
    url = request.url
    result = urlparse(url)
    baseurl = '{}://{}'.format(result.scheme, result.netloc)
    data = baseurl + data
    return data

@app.route('/proxy_download_file')
def proxy_download_file():
    base_headers = {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36',
        'Referer': 'https://www.aliyundrive.com/'
    }
    subt = request.args.get('subt')
    token = request.args.get('token')
    params = request.args.get('params')
    connection = request.args.get('connection')
    headers = request.headers
    cxtheaders = dict(headers)
    if params is None or token is None:
        return 'Erro'
    if connection is None:
        connection = 1
    if subt is None:
        oldapi = True
    else:
        oldapi = False
    params = b64decode(params).decode("utf-8").replace('\'', '\"')
    params = json.loads(params)
    downloader_switch = params['downloader_switch'] if 'downloader_switch' in params else None
    if downloader_switch:
        headers = base_headers.copy()
        for key in cxtheaders:
            if key.strip(',').lower() in ['user-agent', 'host']:
                continue
            headers[key] = cxtheaders[key]
        def get_url_and_headers():
            return AliyunDrive()._get_download_url(params, token, oldapi), headers.copy()
        downloader = Downloader(
            get_url_and_headers=get_url_and_headers,
            headers=headers,
            connection=int(connection),
        )
        try:
            if 'Range' in headers:
                status_code = 206
            else:
                status_code = 200
            res_headers = downloader.start()
            for key in res_headers:
                if key.lower() in ['connection']:
                    continue
                value = res_headers[key]
                cxtheaders[key] = value
            return Response(get_chunk(downloader), status_code, cxtheaders)
        except Exception:
            try:
                downloader.stop()
            except:
                pass
            return redirect('http://0.0.0.0/')
    else:
        download_url = AliyunDrive()._get_download_url(params, token, oldapi)
        result = urlparse(str(request.url))
        baseurl = '{}://{}'.format(result.scheme, result.netloc)
        url = '{}/proxy?ts_url={}&headers={}'.format(baseurl, b64encode(download_url.encode("utf-8")).decode("utf-8"), b64encode(json.dumps(base_headers.copy()).encode("utf-8")).decode("utf-8"))
        return redirect(url)

def get_chunk(downloader):
    while True:
        chunk = downloader.read()
        if chunk is None:
            try:
                downloader.stop()
            except:
                pass
            break
        yield chunk

@app.route('/proxy_preview_m3u8')
def proxy_preview_m3u8():
    token = request.args.get('token')
    params = request.args.get('params')
    headers = request.headers
    cxtheaders = dict(headers)
    if params is None or token is None:
        return 'Erro'
    params = b64decode(params).decode("utf-8").replace('\'', '\"')
    params = json.loads(params)
    share_id = params['share_id']
    file_id = params['file_id']
    template_id = params['template_id']
    cxtheaders.update({'Content-Type': 'application/vnd.apple.mpegurl'})
    result = urlparse(str(request.url))
    baseurl = '{}://{}'.format(result.scheme, result.netloc)
    m3u8, _ = AliyunDrive()._get_m3u8_cache(baseurl, share_id, file_id, template_id, token)
    return Response(m3u8, 200, cxtheaders)

@app.route('/proxy_preview_media')
def proxy_preview_media():
    base_headers = {
        'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36',
        'Referer': 'https://www.aliyundrive.com/',
    }
    params = request.args.get('params')
    headers = request.headers
    cxtheaders = dict(headers)
    result = urlparse(request.url)
    baseurl = '{}://{}'.format(result.scheme, result.netloc)
    if params is None:
        return 'Erro'
    params = b64decode(params).decode("utf-8").replace('\'', '\"')
    params = json.loads(params)
    share_id = params['share_id']
    file_id = params['file_id']
    template_id = params['template_id']
    media_id = params['media_id']
    token = params['token']
    _, media_urls = AliyunDrive()._get_m3u8_cache(baseurl, share_id, file_id, template_id, token, True)
    media_url = media_urls[media_id]
    result = urlparse(request.url)
    baseurl = '{}://{}'.format(result.scheme, result.netloc)
    playcxt, is_m3u8 = Proxy().proxy_m3u8(media_url, baseurl, base_headers.copy())
    if is_m3u8 == 'True':
        return Response(BytesIO(playcxt.encode("utf-8")), mimetype="audio/x-mpegurl", headers={"Content-Disposition": "attachment; filename=proxied.m3u8"})
    elif is_m3u8 == 'False':
        return redirect(playcxt)
    else:
        return 'Erro'

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'templates'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/live')
def getliveurl():
    rid = request.args.get('rid')
    proxy = request.args.get('proxy')
    platform = request.args.get('platform')
    if rid is None or platform is None:
        return redirect('http://0.0.0.0/')
    if proxy is None or proxy == 'off':
        proxy = 'off'
        playurl, header = Spider().get_playurl(rid, platform, proxy)
        if playurl == '':
            return redirect('http://0.0.0.0/')
        return redirect(playurl)
    else:
        result = urlparse(request.url)
        baseurl = '{}://{}'.format(result.scheme, result.netloc)
        playurl, header = Spider().get_playurl(rid, platform, proxy)
        if playurl == '':
            return redirect('http://0.0.0.0/')
        playcxt, is_m3u8 = Proxy().proxy_m3u8(playurl, baseurl, header, proxy)
        if is_m3u8 == 'True':
            return Response(BytesIO(playcxt.encode("utf-8")), mimetype="audio/x-mpegurl", headers={"Content-Disposition": "attachment; filename=proxied.m3u8"})
        elif is_m3u8 == 'False':
            return redirect(playcxt)
        else:
            return redirect('http://0.0.0.0/')

@app.route('/proxy')
def proxy():
    url = request.args.get('ts_url')
    proxy = request.args.get('proxy')
    header = request.args.get('headers')
    if proxy is None or proxy == 'off':
        proxies = {}
    else:
        proxies = {
            "http": "{}://{}:{}".format(proxyProtocol, proxyHost, proxyPort),
            "https": "{}://{}:{}".format(proxyProtocol, proxyHost, proxyPort)
        }
    if url is None or header is None:
        return redirect('http://0.0.0.0/')
    else:
        url = b64decode(url).decode("utf-8")
        header = b64decode(header).decode("utf-8")
        header = json.loads(header)
    try:
        r = requests.get(url=url, headers=header, stream=True, verify=False, proxies=proxies)
        excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        headers = {}
        for (name, value) in r.raw.headers.items():
            if name.lower() not in excluded_headers:
                headers.update({name: value})
        if not 'Content-Type' in header and not 'content-type' in header:
            header.update({'Content-Type': 'video/MP2T'})
        return Response(download_file(r), r.status_code, headers)
    except Exception:
        return redirect('http://0.0.0.0/')

def download_file(streamable):
    with streamable as stream:
        stream.raise_for_status()
        for chunk in stream.iter_content(chunk_size=40960):
            if chunk is None:
                stream.close()
                break
            yield chunk

if __name__ == '__main__':
    app.run(host="0.0.0.0", threaded=True, port=int(port))