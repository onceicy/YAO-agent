import os
import time
import subprocess
import json
from xml.dom.minidom import parse
import xml.dom.minidom
from kafka import KafkaProducer


ClientID = os.getenv('ClientID', 1)
KafkaBrokers = os.getenv('KafkaBrokers', 'localhost:9092').split(',')


def main():
	interval = 10
	while True:
		try:
			status, msg_gpu = execute(['nvidia-smi', '-q', '-x', '-f', 'status.xml'])
			if not status:
				print("execute failed, ", msg_gpu)
				continue
			report_msg()
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


def report_msg():
	DOMTree = xml.dom.minidom.parse("status.xml")
	collection = DOMTree.documentElement
	gpus = collection.getElementsByTagName("gpu")
	stats = []
	for gpu in gpus:
		stat = {
			'uuid': gpu.getElementsByTagName('uuid')[0].childNodes[0].data,
			'product_name': gpu.getElementsByTagName('product_name')[0].childNodes[0].data,
			'fan_speed': gpu.getElementsByTagName('fan_speed')[0].childNodes[0].data,
			'performance_state': gpu.getElementsByTagName('performance_state')[0].childNodes[0].data,
			'memory_total': gpu.getElementsByTagName('fb_memory_usage')[0].getElementsByTagName('total')[0].childNodes[0].data,
			'memory_free': gpu.getElementsByTagName('fb_memory_usage')[0].getElementsByTagName('free')[0].childNodes[0].data,
			'memory_used': gpu.getElementsByTagName('fb_memory_usage')[0].getElementsByTagName('used')[0].childNodes[0].data,
			'utilization_gpu': gpu.getElementsByTagName('utilization')[0].getElementsByTagName('gpu_util')[0].childNodes[0].data,
			'utilization_mem': gpu.getElementsByTagName('utilization')[0].getElementsByTagName('memory_util')[0].childNodes[0].data,
			'temperature_gpu': gpu.getElementsByTagName('temperature')[0].getElementsByTagName('gpu_temp')[0].childNodes[0].data,
			'power_draw': gpu.getElementsByTagName('power_readings')[0].getElementsByTagName('power_draw')[0].childNodes[0].data
		}
		stats.append(stat)

	post_fields = {'id': ClientID, 'status': stats}
	data = json.dumps(post_fields)

	producer = KafkaProducer(bootstrap_servers=KafkaBrokers)
	future = producer.send('yao', value=data.encode(), partition=0)
	result = future.get(timeout=10)
	print(result)


if __name__ == '__main__':
	os.environ["TZ"] = 'Asia/Shanghai'
	if hasattr(time, 'tzset'):
		time.tzset()
	main()
