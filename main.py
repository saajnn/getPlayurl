import os
import json
import requests
from io import BytesIO
from base64 import b64decode
from urllib.parse import urlparse
from flask import Flask, request, redirect, Response, render_template, send_from_directory

from proxy import Proxy
from huya import HuYa
from douyu import DouYu
from douyin import DouYin
from bilibili import BiliBili
from youtube import YouTuBe

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

app = Flask(__name__)
class Spider():
    def get_playurl(self, rid, platform):
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
            playurl = YouTuBe().get_real_url(rid)
        elif platform == 'link':
            playurl = rid
        else:
            playurl = ''
        return playurl, header


@app.route('/')
def web():
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'templates'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/live')
def getliveurl():
    rid = request.args.get('rid')
    proxy = request.args.get('proxy')
    platform = request.args.get('platform')
    if rid is None or platform is None:
        return render_template('index.html')
    else:
        playurl, header = Spider().get_playurl(rid, platform)
    if proxy is None or proxy == 'off':
        return redirect(playurl)
    else:
        url = request.url
        result = urlparse(url)
        baseurl = '{}://{}'.format(result.scheme, result.netloc)
        playcxt, is_m3u8 = Proxy().proxy_m3u8(playurl, baseurl, header)
        if is_m3u8 == 'True':
            return Response(BytesIO(playcxt.encode("utf-8")),
                            mimetype="audio/x-mpegurl",
                            headers={"Content-Disposition": "attachment; filename=proxied.m3u8"})
        elif is_m3u8 == 'False':
            return redirect(playcxt)
        else:
            return redirect('http://0.0.0.0/')


@app.route('/proxy')
def proxy():
    url = request.args.get('ts_url')
    header = request.args.get('headers')
    if url is None or header is None:
        return redirect('http://0.0.0.0/')
    else:
        url = b64decode(url).decode("utf-8")
        header = b64decode(header).decode("utf-8")
        header = json.loads(header)
    try:
        r = requests.get(
            url=url,
            headers=header,
            stream=True,
        )
        excluded_headers = [
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
        ]
        headers = {}
        for (name, value) in r.raw.headers.items():
            if name.lower() not in excluded_headers:
                headers.update({name: value})
        return Response(download_file(r), r.status_code, headers)
    except Exception:
        return redirect('http://0.0.0.0/')


def download_file(streamable):
    with streamable as stream:
        stream.raise_for_status()
        for chunk in stream.iter_content(chunk_size=40960):
            yield chunk


if __name__ == '__main__':
    app.run(host="0.0.0.0", threaded=True, port=int(port))