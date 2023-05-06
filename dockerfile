FROM python:slim-buster	

WORKDIR /getUrl
COPY . /getUrl
RUN pip install -i https://pypi.mirrors.ustc.edu.cn/simple/ -r /getUrl/requirements.txt \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone
CMD ["python", "main.py"]