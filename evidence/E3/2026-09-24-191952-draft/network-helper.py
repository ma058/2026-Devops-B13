from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.request import build_opener,ProxyHandler
from urllib.parse import urlparse
opener=build_opener(ProxyHandler({}))
class Proxy(BaseHTTPRequestHandler):
    def do_GET(self):
        u=urlparse(self.path)
        if u.hostname not in ('archive.ubuntu.com','security.ubuntu.com') or not u.path.startswith('/ubuntu/'):
            self.send_error(403);return
        try:
            r=opener.open('https://mirrors.tuna.tsinghua.edu.cn'+u.path,timeout=60)
            data=r.read()
            self.send_response(r.status)
            self.send_header('Content-Length',str(len(data)))
            self.end_headers();self.wfile.write(data)
        except Exception as e:self.send_error(502,str(e))
    def log_message(self,*args):pass
ThreadingHTTPServer(('0.0.0.0',18764),Proxy).serve_forever()
