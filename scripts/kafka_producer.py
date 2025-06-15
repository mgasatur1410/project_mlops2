import json
from confluent_kafka import Producer
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KafkaResultProducer:
    def __init__(self, bootstrap_servers, topic):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None

    def setup_producer(self):
        conf = {'bootstrap.servers': self.bootstrap_servers}
        self.producer = Producer(conf)
        logger.info(f"Kafka producer setup for topic: {self.topic}")

    def delivery_report(self, err, msg):
        if err is not None:
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.debug(f'Message delivered to {msg.topic()} [{msg.partition()}]')

    def send_result(self, transaction_id, score, fraud_flag):
        try:
            # Преобразуем transaction_id в строку, если это bytes
            if isinstance(transaction_id, bytes):
                transaction_id = transaction_id.decode('utf-8')
            
            # Преобразуем transaction_id в строку, если это не строка
            if not isinstance(transaction_id, str):
                transaction_id = str(transaction_id)
            
            result = {
                'transaction_id': transaction_id,
                'score': float(score),
                'fraud_flag': int(fraud_flag)
            }
            
            self.producer.produce(
                self.topic,
                key=str(transaction_id),
                value=json.dumps(result).encode('utf-8'),
                callback=self.delivery_report
            )
            self.producer.poll(0)  # Trigger delivery reports
            
        except Exception as e:
            logger.error(f"Error sending result to Kafka: {e}")

    def flush(self):
        self.producer.flush() 