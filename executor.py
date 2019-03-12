import docker


def run():
	client = docker.from_env()
	#print(client.containers.run(image="alpine", command="echo 'Hello World'", environment={"KEY": "value"}))
	print(client.containers.run(image="nvidia/cuda:9.0-base", command="nvidia-smi", environment={"KEY": "value"}, runtime="nvidia"))


def run_in_background():
	client = docker.from_env()
	container = client.containers.run("alpine", ["echo", "hello", "world"], detach=True)
	print(container.id)


def list_containers():
	client = docker.from_env()
	for container in client.containers.list():
		print(container.id)


run()
