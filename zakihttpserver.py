#!/usr/bin/env python3

"""Simple HTTP Server With Folder Upload.

This module builds on SimpleHTTPServerWithUpload github gists [1] [2]
and adds folder upload functionality by taking hints from stackoverflow
answer [3].

+ Some other improvements and changes.
+ Async server from [4]

[1] https://gist.github.com/UniIsland/3346170
[2] https://gist.github.com/touilleMan/eb02ea40b93e52604938
[3] http://stackoverflow.com/a/37560550
[4] https://gist.github.com/jdinhlife/1f2e142bbe8036b1a9716f41b8b11ed1
"""
#问题：保存的文件名中文乱码
#解决：cgi.FieldStorage 出来的数据乱码
#     默认windows使用gbk编码，而cgi使用了utf8编码，会导致编码损失，变成奇怪符号����boot.txt
#     cgi编码为encoding='utf-8'，在传参的时候带上encoding='gbk'，然后再重新decode成utf8
#     
#
#问题：网页文件夹和名称中文乱码
#解决：(urllib.parse.quote(linkname), )).encode()+html.escape(displayname).encode("gbk","ignore")+'</a>\n'.encode())

#问题：localhost正常访问，但127.0.0.1不能访问
#解决：默认支支持ipv4，不支持ipv6，使用httpserver类似的DualStackServer即可解决

__version__ = "0.2"
__all__ = ["SimpleHTTPRequestHandler", "ThreadingSimpleServer","HTTPServer", "ThreadingHTTPServer", ]
__author__ = "saaketp"

import os
import posixpath
import http.server
import socketserver
import urllib.request, urllib.parse, urllib.error
import cgi
import shutil
import mimetypes
from io import BytesIO
import argparse
import html
import socket

# 获取本机所有 IP 地址
import socket
hostname = socket.gethostname()
print ( "Host name: %s" %hostname)
sysinfo = socket.gethostbyname_ex(hostname)
ip_addr = sysinfo[2]
for ip in ip_addr:
    print(ip)



class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    """Simple HTTP request handler with GET/HEAD/POST commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method. And can reveive file uploaded
    by client.

    The GET/HEAD/POST requests are identical except that the HEAD
    request omits the actual contents of the file.

    """

    server_version = "SimpleHTTPWithUpload/" + __version__

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()

    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()
        print((r, info, "by: ", self.client_address))
        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success:</strong>")
        else:
            f.write(b"<strong>Failed:</strong>")
        f.write(info.encode())
        f.write(("<br><a href=\"%s\">back</a>" % self.headers['referer']).encode())
        f.write(b"<hr></body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def save_file(self, file, folder):
        outpath = os.path.join(PATH, folder, file.filename)
        outpath1 = os.path.split(outpath)
        os.makedirs(outpath1[0], exist_ok=True)
        if os.path.exists(outpath):
            raise IOError
        with open(outpath, 'wb') as fout:
            shutil.copyfileobj(file.file, fout, 100000)

    def deal_post_data(self):
        form = cgi.FieldStorage(fp=self.rfile,
                                headers=self.headers,encoding='gbk',
                                environ={'REQUEST_METHOD': 'POST'})
        folder = urllib.parse.urlparse(form.headers['Referer']).path[1:]
        saved_fns = ""
        try:
            if isinstance(form['file'], list):
                for f in form['file']:
                    if f.filename != '':
                        saved_fns += ", " + f.filename
                        self.save_file(f, folder)
            else:
                f = form['file']
                if f.filename != '':
                    self.save_file(f, folder)
                    saved_fns += ", " + f.filename
            if isinstance(form['dfile'], list):
                for f in form['dfile']:
                    if f.filename != '':
                        saved_fns += ", " + f.filename
                        self.save_file(f, folder)
            else:
                f = form['dfile']
                if f.filename != '':
                    self.save_file(f, folder)
                    saved_fns += ", " + f.filename
            print(saved_fns)
            return (True, "File(s) "+saved_fns.encode("gbk","ignore").decode("utf-8","ignore")+" upload success!" )
        except IOError:
            return (False, "Can't create file to write, permission denied?")

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = BytesIO()
        displaypath = html.escape(urllib.parse.unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(("<html>\n<title>Directory listing for %s</title>\n" % displaypath).encode("utf-8"))
        f.write(("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath).encode())
        f.write(b"<hr>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"Files upload:\t")
        f.write(b"<input name=\"file\" type=\"file\" multiple=\"\"/>")
        f.write(b"<br>Folder upload:\t")
        f.write(b"<input name=\"dfile\" type=\"file\" multiple=\"\" ")
        f.write(b"directory=\"\" webkitdirectory=\"\" mozdirectory=\"\"/>")
        f.write(b"<input type=\"submit\" value=\"upload\"/></form>\n")
        f.write(b"<hr>\n<ul>\n")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            #str = (urllib.parse.quote(linkname), html.escape(displayname))
            f.write(('<li><a href="%s">'
                    % (urllib.parse.quote(linkname), )).encode()+html.escape(displayname).encode("gbk","ignore")+'</a>\n'.encode()) #html.escape(displayname)
            #print(html.escape(displayname).encode("gbk").decode('utf-8'))
            # print(("你好").encode())
            #chardet.detect('中国')
        f.write(b"</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        path = posixpath.normpath(urllib.parse.unquote(path))
        words = path.split('/')
        words = [_f for _f in words if _f]
        path = PATH
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path

    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile)

    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        })


class ThreadingSimpleServer(socketserver.ThreadingMixIn,
                            http.server.HTTPServer):
    pass


def test(HandlerClass=SimpleHTTPRequestHandler,
         ServerClass=ThreadingSimpleServer, port=8000):
    http.server.test(HandlerClass, ServerClass, port=port)


PATH = os.getcwd()
class HTTPServer(socketserver.TCPServer):

    allow_reuse_address = 1    # Seems to make sense in testing environment

    def server_bind(self):
        """Override server_bind to store the server name."""
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port
class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True

if __name__ == '__main__':
    import contextlib

    parser = argparse.ArgumentParser(description='''Run a simple http server
                                     to share files and folders''')
    parser.add_argument("path", help='''path to be shared''',
                        nargs='?', default=os.getcwd())
    parser.add_argument("-p", "--port", type=int, default=8000,
                        help="port number for listening to http requests")
    args = parser.parse_args()
    PATH = args.path
    
    # ensure dual-stack is not disabled; ref #38907
    class DualStackServer(ThreadingHTTPServer):

        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(
                    socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

        def finish_request(self, request, client_address):
            self.RequestHandlerClass(request, client_address, self)
    test(ServerClass=DualStackServer,port=args.port)