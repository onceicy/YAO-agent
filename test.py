import docker


def run():
	client = docker.from_env()
	try:
		print(client.containers.run(image="alpine", command="nvid", environment={"KEY": "value"}))
		# print(client.containers.run(image="nvidia/cuda:9.0-base", command="nvidia-smi", environment={"KEY": "value"}, runtime="nvidia"))
	except Exception as e:
		print(e.__class__.__name__, e)


def run_in_background():
	client = docker.from_env()
	container = client.containers.run("alpine", ["echo", "hello", "world"], detach=True)
	print(container.id)


def list_containers():
	client = docker.from_env()
	for container in client.containers.list():
		print(container.id)


def get_logs(id):
	try:
		client = docker.from_env()
		container = client.containers.get(id)
		print(container.logs().decode())
	except Exception as e:
		print(e)


def get_status(id):
	client = docker.from_env()
	container = client.containers.list(all=True, filters={'id': id})
	status = {}
	if len(container) > 0:
		container = container[0]
		status['id'] = container.short_id
		status['image'] = container.attrs['Config']['Image']
		status['image_digest'] = container.attrs['Image']
		status['command'] = container.attrs['Config']['Cmd']
		status['createdAt'] = container.attrs['Created']
		status['finishedAt'] = container.attrs['State']['FinishedAt']
		status['status'] = container.status
		if status['command'] is not None:
			status['command'] = ' '.join(container.attrs['Config']['Cmd'])
	print(status)
	print(container.attrs)


get_status('')
