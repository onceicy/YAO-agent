import os
from threading import Thread
from threading import Lock
import time
import subprocess
import json
from xml.dom.minidom import parse
import xml.dom.minidom
from kafka import KafkaProducer
import multiprocessing
import psutil
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi
import docker
from urllib import parse

ClientID = os.getenv('ClientID', 1)
ClientHost = os.getenv('ClientHost', "localhost")
KafkaBrokers = os.getenv('KafkaBrokers', 'localhost:9092').split(',')

PORT_NUMBER = 8000

lock = Lock()
pending_tasks = {}

ver = 0
last_version = {}

counter = {}


def launch_task_in_background(container, task_id):
	script = " ".join([
		"docker exec",
		task_id,
		"pkill",
		"sleep"
	])

	while True:
		code = container.exec_run('sh -c \'' + script + '\'').exit_code
		if code == 0:
			break
		time.sleep(0.1)


def launch_tasks(stats):
	utils = {}
	mems = {}
	for stat in stats:
		utils[stat['uuid']] = stat['utilization_gpu']
		if int(stat['utilization_gpu']) < 60:
			if stat['uuid'] not in counter:
				counter[stat['uuid']] = 0
			counter[stat['uuid']] += 1
		else:
			counter[stat['uuid']] = 0
		mems[stat['uuid']] = stat['memory_free']

	client = docker.from_env()
	container = client.containers.get('yao-agent-helper')
	entries_to_remove = []
	lock.acquire()
	for task_id, task in pending_tasks.items():
		if int(utils[task['gpus'][0]]) < 60 and counter[task['gpus'][0]] >= 2 \
				and mems[task['gpus'][0]] > task['gpu_mem']:
			entries_to_remove.append(task_id)

			t = Thread(target=launch_task_in_background, name='launch_task', args=(container, task_id,))
			t.start()

	for k in entries_to_remove:
		pending_tasks.pop(k, None)
	lock.release()


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
					#if container_id in pending_tasks:
					#	status['status'] = 'ready'
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
			docker_cpu_limit = form.getvalue('cpu_limit')
			docker_network = form.getvalue('network')
			docker_wait = form.getvalue('should_wait')
			docker_output = form.getvalue('output_dir')
			docker_hdfs_address = form.getvalue('hdfs_address')
			docker_hdfs_dir = form.getvalue('hdfs_dir')
			docker_gpu_mem = form.getvalue('gpu_mem')

			try:
				script = " ".join([
					"docker run",
					"--gpus '\"device=" + docker_gpus + "\"'",
					"--detach=True",
					"--hostname " + docker_name,
					"--network " + docker_network,
					"--network-alias " + docker_name,
					"--memory-reservation " + docker_mem_limit,
					"--cpus " + docker_cpu_limit,
					"--env repo=" + docker_workspace,
					"--env should_wait=" + docker_wait,
					"--env output_dir=" + docker_output,
					"--env hdfs_address=" + docker_hdfs_address,
					"--env hdfs_dir=" + docker_hdfs_dir,
					"--env gpu_mem=" + docker_gpu_mem,
					docker_image,
					docker_cmd
				])

				client = docker.from_env()
				container = client.containers.get('yao-agent-helper')
				exit_code, output = container.exec_run(['sh', '-c', script])
				msg = {"code": 0, "id": output.decode('utf-8').rstrip('\n')}

				lock.acquire()
				pending_tasks[msg['id']] = {'gpus': str(docker_gpus).split(','), 'gpu_mem': int(docker_gpu_mem)}
				lock.release()
				if exit_code != 0:
					msg["code"] = 1
					msg["error"] = output.decode('utf-8').rstrip('\n')
			except Exception as e:
				msg = {"code": 1, "error": str(e)}
				print(str(e))

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
				container.stop(timeout=1)
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


def report():
	interval = 3
	while True:
		try:
			status, msg_gpu = execute(['nvidia-smi', '-q', '-x', '-f', 'status.xml'])
			if not status:
				print("execute failed, ", msg_gpu)
			stats = get_gpu_status()
			report_msg(stats)
			t = Thread(target=launch_tasks, name='launch_tasks', args=(stats,))
			t.start()
			time.sleep(interval)
		except Exception as e:
			print(e)
			time.sleep(interval)


def execute(cmd):
	try:
		result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		if result.returncode == 0:
			return True, result.stdout.decode('utf-8').rstrip('\n')
		return False, result.stderr.decode('utf-8').rstrip('\n')
	except Exception as e:
		return False, e


def get_gpu_status():
	DOMTree = xml.dom.minidom.parse("status.xml")
	collection = DOMTree.documentElement
	gpus = collection.getElementsByTagName("gpu")
	stats = []
	for gpu in gpus:
		stat = {
			'uuid': gpu.getElementsByTagName('uuid')[0].childNodes[0].data,
			'product_name': gpu.getElementsByTagName('product_name')[0].childNodes[0].data,
			'performance_state': gpu.getElementsByTagName('performance_state')[0].childNodes[0].data,
			'memory_total': gpu.getElementsByTagName('fb_memory_usage')[0].getElementsByTagName('total')[0].childNodes[
				0].data,
			'memory_free': gpu.getElementsByTagName('fb_memory_usage')[0].getElementsByTagName('free')[0].childNodes[
				0].data,
			'memory_used': gpu.getElementsByTagName('fb_memory_usage')[0].getElementsByTagName('used')[0].childNodes[
				0].data,
			'utilization_gpu':
				gpu.getElementsByTagName('utilization')[0].getElementsByTagName('gpu_util')[0].childNodes[0].data,
			'utilization_mem':
				gpu.getElementsByTagName('utilization')[0].getElementsByTagName('memory_util')[0].childNodes[0].data,
			'temperature_gpu':
				gpu.getElementsByTagName('temperature')[0].getElementsByTagName('gpu_temp')[0].childNodes[0].data,
			'power_draw':
				gpu.getElementsByTagName('power_readings')[0].getElementsByTagName('power_draw')[0].childNodes[0].data
		}

		stat['memory_total'] = int(float(stat['memory_total'].split(' ')[0]))
		stat['memory_free'] = int(float(stat['memory_free'].split(' ')[0]))
		stat['memory_used'] = int(float(stat['memory_used'].split(' ')[0]))
		stat['utilization_gpu'] = int(float(stat['utilization_gpu'].split(' ')[0]))
		stat['utilization_mem'] = int(float(stat['utilization_mem'].split(' ')[0]))
		stat['temperature_gpu'] = int(float(stat['temperature_gpu'].split(' ')[0]))
		stat['power_draw'] = int(float(stat['power_draw'].split(' ')[0]))

		stats.append(stat)
	return stats


def report_msg(stats):
	global last_version
	global ver
	mem = psutil.virtual_memory()

	post_fields = {
		'id': ClientID,
		'host': ClientHost,
		'status': stats,
		'cpu_num': multiprocessing.cpu_count(),
		'cpu_load': os.getloadavg()[0],
		'mem_total': math.floor(mem.total / (1024. ** 3)),
		'mem_available': math.floor(mem.available / (1024. ** 3))
	}

	flag = False
	if 'cpu_num' in last_version:  # not null
		if abs(last_version['cpu_num'] - post_fields['cpu_num']) > 0.0:
			flag = True
		if abs(last_version['cpu_load'] - post_fields['cpu_load']) / post_fields['cpu_num'] > 0.1:
			flag = True
		if abs(last_version['mem_total'] - post_fields['mem_total']) > 0.0:
			flag = True
		if abs(last_version['mem_available'] - post_fields['mem_available']) / post_fields['mem_available'] > 0.05:
			flag = True
		for i in range(len(stats)):
			if abs(last_version['status'][i]['memory_total'] - post_fields['status'][i]['memory_total']) > 0.0:
				flag = True
			if abs(last_version['status'][i]['memory_free'] - post_fields['status'][i]['memory_free']) / \
					post_fields['status'][i]['memory_total'] > 0.05:
				flag = True
			if abs(last_version['status'][i]['utilization_gpu'] - post_fields['status'][i]['utilization_gpu']) > 25.0:
				flag = True
	else:
		flag = True

	if flag:
		ver = time.time()
		last_version = post_fields

	post_fields['version'] = ver
	data = json.dumps(post_fields)

	if flag:
		print(ver)
		print(post_fields)

	producer = KafkaProducer(bootstrap_servers=KafkaBrokers)
	future = producer.send('yao', value=data.encode(), partition=0)
	result = future.get(timeout=10)
	print(result)


def listener():
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


if __name__ == '__main__':
	os.environ["TZ"] = 'Asia/Shanghai'
	if hasattr(time, 'tzset'):
		time.tzset()
	t1 = Thread(target=report)
	t2 = Thread(target=listener)
	t1.start()
	t2.start()
	while True:
		time.sleep(5)
		pass
