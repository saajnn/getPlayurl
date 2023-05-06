##使用说明##

基于Flask框架的直播地址获取、代理项目，目前支持斗鱼、抖音、虎牙、Bilibili、YouTube的直播地址获取，阿里系播放地址代理。

访问
http://服务器ip:端口/live?platform=平台&rid=直播地址参数(&proxy=on)
播放直播。

通过config.conf文件端口、stock5代理等相关信息

platform：平台

斗鱼：douyu

虎牙：huya

抖音：douyin

Bilibili：bilibili

YouTube：youtube

需要代理的视频地址：link

rid：直播地址参数如下链接中的xxxxxx

斗鱼：www.douyu.com/xxxxxx 或 www.douyu.com/xx/xx?rid=xxxxxx

虎牙：www.huya.com/xxxxxx

抖音：https://v.douyin.com/xxxxxx 或 live.douyin.com/xxxxxx

Bilibili：live.bilibili.com/xxxxxx?hotRank=0......

Youtube：https://www.youtube.com/watch?v=xxxxxx&list=......

proxy：代理

on：开启

off/不填/不添加proxy参数：直链

阿里系使用说明：

爬虫参考https://github.com/lm317379829/PyramidStore/tree/pyramid/plugin中py_zhaozy.py、py_yiso.py、py_pansou.py。

获取文件列表：地址:端口/ali_list?item=base64编码后的视频参数&display_file_size=是否显示文件大小

item：{'type': 'directory', 'id': 'https://www.aliyundrive.com/s/uYHxNKhqkmk/folder/6443b93453d7fef788234d858afaa457f30ac440', 'name': '阿里盘搜：漫长的季节', 'cover': '', 'description': '更新时间：2023-05-01', 'cast': [], 'director': '', 'area': '', 'year': 0, 'sources': [], 'danmakus': [], 'subtitles': [], 'params': {'type': 'video', 'pf': 'ps', 'num': 11}}

其中，type：file/directory，文件为file，目录为directory，id：链接，name：文件名/目录名。

display_file_size：True/False，是/否显示文件大小

解析播放地址：地址:端口/ali_resolve?item=base64编码后的视频参数

item：{"drive_id": "XXXXXXX", "file_id": "XXXXXXX", "pf": "ali", "share_id": "XXXXXXX", "template_id": "", "downloader_switch": true}

其中，downloader_switch：true/false，是/否开启多线程下载。

原画播放地址：地址:端口/proxy_download_file?params=base64编码后视频参数=&token=阿里token&connection=线程数

params：同上item。

普画播放地址：地址:端口/proxy_preview_m3u8?params=base64编码后视频参数=&token=阿里token

params：同上item，其中template_id为分辨率FHD、HD、SD等，分别对应1080P、720P、480P，具体可从阿里返回数据中获取。
