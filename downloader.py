import re
import time
import requests
import threading
from queue import Queue

class Downloader(object):

    def __init__(
            self,
            url='',
            headers={},
            get_url_and_headers=None,
            chunk_size=1024 * 1024,
            buffer_size=1024 * 64,
            prefetch_size=1024 * 256,
            max_buffered_chunk=100,
            #chunk_size=4,
            #buffer_size=2,
            #prefetch_size=8,
            connection=30,
            timeout=10):
        self.url = url
        self.headers = headers
        self.get_url_and_headers = get_url_and_headers
        self.chunk_size = chunk_size
        self.buffer_size = buffer_size
        self.prefetch_size = prefetch_size
        self.max_buffered_chunk = max_buffered_chunk
        self.connection = connection
        self.timeout = timeout
        self.running = False
        self.file_size = -1
        self.content_length = -1
        self.start_offset = -1
        self.end_offset = -1
        self.current_offset = -1
        self.pending_chunk_queue = Queue()
        self.ready_chunk_queue = Queue()
        self.current_chunk = None
        self.last_read = -1
        self.lock = threading.Lock()
        self.session = requests.session()
        self.id = time.time()

    def start(self):
        if 'Range' not in self.headers:
            self.headers['Range'] = 'bytes=0-'
        m = re.search(r'bytes=(\d+)-(\d+)?', self.headers['Range'])
        self.start_offset = int(m.group(1))
        if m.group(2):
            self.end_offset = int(m.group(2))
            content_length = self.end_offset - self.start_offset + 1
            if self.prefetch_size > content_length:
                self.prefetch_size = content_length

        if self.get_url_and_headers:
            url, headers = self.get_url_and_headers()
            headers.update(self.headers)
        else:
            url = self.url
            headers = self.headers

        r = self.session.get(url, headers=headers, verify=False, stream=True)

        datas = []
        prefetch_size = 0
        for data in r.iter_content(self.buffer_size):
            datas.append(data)
            prefetch_size += len(data)
            if prefetch_size >= self.prefetch_size:
                break
        self.prefetch_size = prefetch_size
        r.close()

        chunk = Chunk(self.start_offset,
                      self.start_offset + self.prefetch_size - 1)
        for data in datas:
            chunk.queue.put(data)
        self.ready_chunk_queue.put(chunk)

        m = re.search(r'.*/(\d+)', r.headers['content-range'])
        self.file_size = int(m.group(1))
        if self.end_offset < 0:
            self.end_offset = self.file_size - 1
        self.content_length = self.end_offset - self.start_offset + 1

        self.current_offset = self.start_offset
        return r.headers

    def monitor(self):
        while self.running:
            if time.time() - self.last_read >= self.timeout:
                self.running = False
                return

    def worker(self):
        while self.running:
            chunk = None
            try:
                self.lock.acquire()
                if not self.pending_chunk_queue.empty():
                    chunk = self.pending_chunk_queue.get()
                    self.ready_chunk_queue.put(chunk)
            except Exception as e:
                print(e)
            finally:
                self.lock.release()

            if chunk is None:
                self.running = False
                break

            while self.running:
                if chunk.start_offset - self.current_offset >= self.chunk_size * self.max_buffered_chunk:
                    time.sleep(1)
                    continue
                else:
                    break

            if not self.running:
                break

            current_offset = chunk.start_offset
            while self.running and current_offset <= chunk.end_offset:
                try:
                    if self.get_url_and_headers:
                        url, headers = self.get_url_and_headers()
                        headers = headers.copy()
                    else:
                        url = self.url
                        headers = self.headers.copy()

                    headers['Range'] = 'bytes={}-{}'.format(
                        current_offset, chunk.end_offset)
                    r = self.session.get(url,
                                         headers=headers,
                                         stream=True,
                                         verify=False)
                    for data in r.iter_content(self.buffer_size):
                        chunk.queue.put(data)
                        current_offset += len(data)
                    break
                except Exception as e:
                    print(e)
                    time.sleep(1)

    def read(self):
        self.last_read = time.time()
        if self.current_offset > self.end_offset:
            self.running = False
            return None

        if not self.running and self.current_offset > self.start_offset and self.current_chunk is None:
            self.running = True
            for i in range(
                    int((self.content_length - self.prefetch_size - 1) /
                        self.chunk_size) + 1):
                start_offset = self.start_offset + self.prefetch_size + i * self.chunk_size
                end_offset = start_offset + self.chunk_size - 1
                if end_offset > self.end_offset:
                    end_offset = self.end_offset
                chunk = Chunk(start_offset, end_offset)
                self.pending_chunk_queue.put(chunk)
            for _ in range(self.connection):
                threading.Thread(target=self.worker).start()
            threading.Thread(target=self.monitor).start()

        if self.current_chunk == None:
            self.current_chunk = self.ready_chunk_queue.get(True, self.timeout)

        data = self.current_chunk.read(self.timeout)
        self.current_offset += len(data)
        if self.current_chunk.eof():
            self.current_chunk = None
        return data

    def stop(self):
        self.running = False

class Chunk(object):

    def __init__(self, start_offset=-1, end_offset=-1):
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.chunk_size = end_offset - start_offset + 1
        self.read_size = 0
        self.queue = Queue()

    def read(self, timeout=10):
        data = self.queue.get(True, timeout)
        self.queue.task_done()
        self.read_size += len(data)
        return data

    def eof(self):
        return self.read_size >= self.chunk_size

