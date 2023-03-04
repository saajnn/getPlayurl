##使用说明##

基于Flask框架的直播地址获取、代理项目，目前支持斗鱼、抖音、虎牙、Bilibili、YouTube的直播地址获取。

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
