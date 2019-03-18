# YAO-agent


```bash
bin/kafka-topics.sh \
	--describe \
	--zookeeper zookeeper_node1:2181,zookeeper_node2:2181,zookeeper_node3:2181 \
	--topic yao
```

```bash
bin/kafka-topics.sh \
	--create \
	--zookeeper zookeeper_node1:2181,zookeeper_node2:2181,zookeeper_node3:2181 \
	--replication-factor 3 \
	--partitions 1 \
	--topic yao
```

```bash
bin/kafka-console-consumer.sh \
	--bootstrap-server kafka_node1:9091,kafka_node2:9092,kafka_node3:9093 \
	--topic yao \
	--from-beginning
```

```bash
bin/kafka-console-producer.sh \
	--broker-list kafka_node1:9091,kafka_node2:9092,kafka_node3:9093 \
	--topic yao
```