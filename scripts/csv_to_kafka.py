import os
import json
import time
import argparse
import pandas as pd
from confluent_kafka import Producer
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CSVtoKafkaLoader:
    def __init__(self, bootstrap_servers, topic, csv_path, delay=0.5):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.csv_path = csv_path
        self.delay = delay
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

    def load_csv(self):
        try:
            logger.info(f"Loading CSV file: {self.csv_path}")
            df = pd.read_csv(self.csv_path)
            logger.info(f"Loaded {len(df)} records from CSV")
            return df
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            raise

    def send_to_kafka(self):
        try:
            # Setup producer
            self.setup_producer()
            
            # Load CSV
            df = self.load_csv()
            
            # Reset index to ensure we have a unique index
            df.reset_index(inplace=True)
            
            # Iterate through rows and send to Kafka
            total_rows = len(df)
            for i, (_, row) in enumerate(df.iterrows()):
                # Convert row to JSON
                message = row.to_dict()
                
                # Ensure all values are JSON serializable
                for k, v in message.items():
                    if pd.isna(v):
                        message[k] = None
                
                # Convert to JSON string and send to Kafka
                message_json = json.dumps(message)
                self.producer.produce(
                    self.topic,
                    key=str(message.get('index', i)),
                    value=message_json.encode('utf-8'),
                    callback=self.delivery_report
                )
                
                # Flush on every 100 messages or when we have reached the end
                if i % 100 == 0 or i == total_rows - 1:
                    self.producer.flush()
                    logger.info(f"Progress: {i+1}/{total_rows} records sent to Kafka")
                
                # Add delay to not overwhelm the system
                if self.delay > 0:
                    time.sleep(self.delay)
            
            logger.info(f"All {total_rows} records have been sent to Kafka")
            
        except Exception as e:
            logger.error(f"Error sending data to Kafka: {e}")
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load CSV data to Kafka')
    parser.add_argument('--bootstrap-servers', default='kafka:9092', help='Kafka bootstrap servers')
    parser.add_argument('--topic', default='transactions', help='Kafka topic to send data to')
    parser.add_argument('--csv-path', default='input/test.csv', help='Path to CSV file')
    parser.add_argument('--delay', type=float, default=0.1, help='Delay between messages (seconds)')
    
    args = parser.parse_args()
    
    loader = CSVtoKafkaLoader(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        csv_path=args.csv_path,
        delay=args.delay
    )
    
    loader.send_to_kafka() 