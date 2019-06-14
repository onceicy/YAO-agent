#!/usr/bin/python
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi
import docker
import json
from urllib import parse

PORT_NUMBER = 8000


class MyHandler(BaseHTTPRequestHandler):
	# Handler for the GET requests
	def do_GET(self):
		req = parse.urlparse(self.path)
		query = parse.parse_qs(req.query)

		if req.path == "/ping":
			self.send_response(200)
			self.send_header('Content-type', 'application/json')
			self.end_headers()
			self.wfile.write(bytes("pong", "utf-8"))

		elif req.path == "/logs":
			try:
				container_id = query.get('id')[0]
				client = docker.from_env()
				container = client.containers.get(container_id)
				msg = {'code': 0, 'logs': str(container.logs().decode())}
			except Exception as e:
				msg = {'code': 1, 'error': str(e)}
			self.send_response(200)
			self.send_header('Content-type', 'application/json')
			self.end_headers()
			self.wfile.write(bytes(json.dumps(msg), "utf-8"))

		elif req.path == "/status":
			try:
				container_id = query.get('id')[0]
				client = docker.from_env()
				container = client.containers.list(all=True, filters={'id': container_id})
				if len(container) > 0:
					container = container[0]
					status = {
						'id': container.short_id,
						'image': container.attrs['Config']['Image'],
						'image_digest': container.attrs['Image'],
						'command': container.attrs['Config']['Cmd'],
						'created_at': container.attrs['Created'],
						'finished_at': container.attrs['State']['FinishedAt'],
						'status': container.status,
						'hostname': container.attrs['Config']['Hostname'],
						'state': container.attrs['State']
					}
					if status['command'] is not None:
						status['command'] = ' '.join(container.attrs['Config']['Cmd'])
					msg = {'code': 0, 'status': status}
				else:
					msg = {'code': 1, 'error': "container not exist"}
			except Exception as e:
				msg = {'code': 2, 'error': str(e)}
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
			docker_image = form.getvalue('image')
			docker_name = form.getvalue('name')
			docker_cmd = form.getvalue('cmd')
			docker_workspace = form.getvalue('workspace')
			docker_gpus = form.getvalue('gpus')
			docker_mem_limit = form.getvalue('mem_limit')
			docker_cpu_limit = int(form.getvalue('cpu_limit'))
			docker_network = form.getvalue('network')

			try:
				client = docker.APIClient(base_url='unix://var/run/docker.sock')

				host_config = client.create_host_config(
					mem_limit=docker_mem_limit,
					cpu_shares=docker_cpu_limit * 1024
				)
				networking_config = client.create_networking_config(
					endpoints_config={
						docker_network: client.create_endpoint_config(
							aliases=[docker_name],
						)
					}
				)

				container = client.create_container(
					image=docker_image,
					command=docker_cmd,
					hostname=docker_name,
					detach=True,
					host_config=host_config,
					environment={"repo": docker_workspace, "NVIDIA_VISIBLE_DEVICES": docker_gpus},
					networking_config=networking_config,
					runtime='nvidia'
				)
				client.start(container)
				msg = {"code": 0, "id": container['Id']}
			except Exception as e:
				msg = {"code": 1, "error": str(e)}

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
			container_id = form.getvalue('id')

			try:
				client = docker.from_env()
				container = client.containers.get(container_id)
				container.stop()
				msg = {"code": 0, "error": "Success"}
			except Exception as e:
				msg = {"code": 1, "error": str(e)}

			self.send_response(200)
			self.send_header('Content-type', 'application/json')
			self.end_headers()
			self.wfile.write(bytes(json.dumps(msg), "utf-8"))

		elif self.path == "/remove":
			form = cgi.FieldStorage(
				fp=self.rfile,
				headers=self.headers,
				environ={
					'REQUEST_METHOD': 'POST',
					'CONTENT_TYPE': self.headers['Content-Type'],
				})
			container_id = form.getvalue('id')

			try:
				client = docker.from_env()
				container = client.containers.get(container_id)
				container.remove(force=True)
				msg = {"code": 0, "error": "Success"}
			except Exception as e:
				msg = {"code": 1, "error": str(e)}

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
	print('Started http server on port ', PORT_NUMBER)

	# Wait forever for incoming http requests
	server.serve_forever()

except KeyboardInterrupt:
	print('^C received, shutting down the web server')

server.socket.close()
