#!/usr/bin/env python

import http.client
import logging
import os
import socket
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import sleep
from typing import BinaryIO

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL') or logging.ERROR)


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/ping':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'Not Found')

    def do_POST(self):
        if self.path == '/invocations':
            # for loop
            while True:
                if self.is_port_open('127.0.0.1', 8081):
                    print('Port is open')
                    response = self.forward_request(self.headers, self.rfile)
                    self.send_response(response.status)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(response.read())
                else:
                    sleep(1)
                    logger.info('Waiting for port to be open')

        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'Not Found')

    def is_port_open(self, host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0

    def forward_request(self, headers, rfile: BinaryIO):
        content_length = int(headers['Content-Length'])
        post_data = rfile.read(content_length)
        print(post_data)
        conn = http.client.HTTPConnection('127.0.0.1', 8081, timeout=60 * 10)
        conn.request("POST", "/invocations", post_data, headers)
        return conn.getresponse()


def run_server(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler):
    server_address = ('', 8080)
    httpd = server_class(server_address, handler_class)
    print("Starting server on http://localhost:8080/")
    httpd.serve_forever()


if __name__ == '__main__':
    subprocess.Popen(["bash", "/serve.sh"])
    run_server()
