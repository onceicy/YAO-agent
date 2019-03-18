#!/usr/bin/python
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi
import docker
import json
from urllib import parse

PORT_NUMBER = 8000


# This class will handles any incoming request from
# the browser
class MyHandler(BaseHTTPRequestHandler):
	# Handler for the GET requests
	def do_GET(self):
		req = parse.urlparse(self.path)
		query = parse.parse_qs(req.query)

		if req.path == "/ping":
			# Open the static file requested and send it
			self.send_response(200)
			self.send_header('Content-type', 'application/json')
			self.end_headers()
			self.wfile.write(bytes("pong", "utf-8"))

		elif req.path == "/logs":
			id = query['id'][0]
			try:
				client = docker.from_env()
				container = client.containers.get(id)
				msg = {'code': 0, 'logs': str(container.logs().decode())}
			except Exception as e:
				msg = {'code': 0, 'error': e}
			self.send_response(200)
			self.send_header('Content-type', 'application/json')
			self.end_headers()
			self.wfile.write(bytes(json.dumps(msg), "utf-8"))

		elif req.path == "/status":
			id = query['id'][0]
			client = docker.from_env()
			container = client.containers.list(all=True, filters={'id': id})
			if len(container) > 0:
				container = container[0]
				print(container.image.attrs)
				status = {
					'id': container.short_id,
					'image': container.attrs['Config']['Image'],
					'image_digest': container.attrs['Image'],
					'command': container.attrs['Config']['Cmd'],
					'createdAt': container.attrs['Created'],
					'finishedAt': container.attrs['State']['FinishedAt'],
					'status': container.status
				}
				if status['command'] is not None:
					status['command'] = ' '.join(container.attrs['Config']['Cmd'])
				msg = {'code': 0, 'status': status}
			else:
				msg = {'code': 1, 'error': "container not exist"}
			self.send_response(200)
			self.send_header('Content-type', 'application/json')
			self.end_headers()
			self.wfile.write(bytes(json.dumps(msg), "utf-8"))

		else:
			self.send_error(404, 'File Not Found: %s' % self.path)


# Handler for the POST requests
def do_POST(self):
	if self.path == "/create":
		form = cgi.FieldStorage(
			fp=self.rfile,
			headers=self.headers,
			environ={
				'REQUEST_METHOD': 'POST',
				'CONTENT_TYPE': self.headers['Content-Type'],
			})
		docker_image = form["image"].value
		docker_cmd = form["cmd"].value

		try:
			client = docker.from_env()
			container = client.containers.run(
				image=docker_image,
				command=docker_cmd,
				environment={"key": "value"},
				runtime="nvidia",
				detach=True
			)
			msg = {"code": 0, "id": container.id}
		except Exception as e:
			msg = {"code": 1, "error": e}

		self.send_response(200)
		self.send_header('Content-type', 'application/json')
		self.end_headers()
		self.wfile.write(bytes(json.dumps(msg), "utf-8"))

	elif self.path == "/stop":
		form = cgi.FieldStorage(
			fp=self.rfile,
			headers=self.headers,
			environ={
				'REQUEST_METHOD': 'POST',
				'CONTENT_TYPE': self.headers['Content-Type'],
			})
		id = form["id"].value

		client = docker.from_env()
		container = client.containers.get(id)
		container.stop()
		msg = {"code": 0}

		self.send_response(200)
		self.send_header('Content-type', 'application/json')
		self.end_headers()
		self.wfile.write(bytes(json.dumps(msg), "utf-8"))
	else:
		self.send_error(404, 'File Not Found: %s' % self.path)


try:
	# Create a web server and define the handler to manage the
	# incoming request
	server = HTTPServer(('', PORT_NUMBER), MyHandler)
	print('Started httpserver on port ', PORT_NUMBER)

	# Wait forever for incoming htto requests
	server.serve_forever()

except KeyboardInterrupt:
	print('^C received, shutting down the web server')

server.socket.close()
