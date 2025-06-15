import json
import pandas as pd
from confluent_kafka import Consumer, KafkaException
import time
from preprocess import add_features
import logging

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KafkaMessageConsumer:
    def __init__(self, bootstrap_servers, topic, group_id):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.consumer = None
        self.running = False

    def setup_consumer(self):
        conf = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'auto.offset.reset': 'earliest'
        }
        
        self.consumer = Consumer(conf)
        self.consumer.subscribe([self.topic])
        logger.info(f"Kafka consumer subscribed to topic: {self.topic}")
        
    def process_message(self, message):
        try:
            transaction_data = json.loads(message.value().decode('utf-8'))
            transaction_df = pd.DataFrame([transaction_data])
            
            # Preprocessing
            processed_df = add_features(transaction_df)
            
            # Fill NA values as in preprocess.py
            for col in processed_df.columns:
                if processed_df[col].dtype == 'object':
                    processed_df[col] = processed_df[col].fillna('missing')
                else:
                    processed_df[col] = processed_df[col].fillna(processed_df[col].median())
            
            return processed_df
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None

    def consume_messages(self, process_callback):
        self.running = True
        try:
            while self.running:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                
                if msg.error():
                    raise KafkaException(msg.error())
                
                processed_df = self.process_message(msg)
                if processed_df is not None:
                    process_callback(processed_df, msg.key())
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.consumer.close()
            logger.info("Consumer closed")

    def stop(self):
        self.running = False 