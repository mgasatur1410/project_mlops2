import json
import os
import logging
import psycopg2
from confluent_kafka import Consumer, KafkaException

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostgresDBService:
    def __init__(self, 
                 db_host, db_port, db_name, db_user, db_password,
                 bootstrap_servers, topic, group_id):
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.db_connection = None
        self.cursor = None
        self.consumer = None
        self.running = False
    
    def connect_to_db(self):
        try:
            logger.info(f"Connecting to PostgreSQL database at {self.db_host}:{self.db_port}/{self.db_name}")
            
            # Wait for PostgreSQL to be ready
            retries = 0
            max_retries = 30  # 30 * 2 seconds = 60 seconds max wait
            connected = False
            
            while not connected and retries < max_retries:
                try:
                    self.db_connection = psycopg2.connect(
                        host=self.db_host,
                        port=self.db_port,
                        dbname=self.db_name,
                        user=self.db_user,
                        password=self.db_password
                    )
                    connected = True
                except psycopg2.OperationalError as e:
                    retries += 1
                    logger.warning(f"Database connection attempt {retries}/{max_retries} failed: {e}")
                    if retries < max_retries:
                        import time
                        time.sleep(2)  # 2 seconds between retries
                    else:
                        raise
            
            self.cursor = self.db_connection.cursor()
            self.create_table_if_not_exists()
            logger.info("Successfully connected to the database")
            
        except Exception as e:
            logger.error(f"Failed to connect to the database: {e}")
            raise
    
    def create_table_if_not_exists(self):
        try:
            query = """
            CREATE TABLE IF NOT EXISTS transaction_scores (
                transaction_id VARCHAR(255) PRIMARY KEY,
                score FLOAT NOT NULL,
                fraud_flag INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            self.cursor.execute(query)
            self.db_connection.commit()
            logger.info("Transaction scores table created or already exists")
            
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise
    
    def setup_kafka_consumer(self):
        try:
            logger.info(f"Setting up Kafka consumer for topic: {self.topic}")
            
            conf = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': self.group_id,
                'auto.offset.reset': 'earliest'
            }
            
            self.consumer = Consumer(conf)
            self.consumer.subscribe([self.topic])
            logger.info("Kafka consumer setup successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup Kafka consumer: {e}")
            raise
    
    def insert_transaction_score(self, transaction_id, score, fraud_flag):
        try:
            query = """
            INSERT INTO transaction_scores (transaction_id, score, fraud_flag)
            VALUES (%s, %s, %s)
            ON CONFLICT (transaction_id) DO UPDATE 
            SET score = EXCLUDED.score, 
                fraud_flag = EXCLUDED.fraud_flag,
                created_at = DEFAULT;
            """
            
            self.cursor.execute(query, (transaction_id, score, fraud_flag))
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to insert transaction score: {e}")
            self.db_connection.rollback()
    
    def process_message(self, message):
        try:
            data = json.loads(message.value().decode('utf-8'))
            transaction_id = data.get('transaction_id')
            score = data.get('score')
            fraud_flag = data.get('fraud_flag')
            
            if transaction_id is not None and score is not None and fraud_flag is not None:
                self.insert_transaction_score(transaction_id, score, fraud_flag)
                logger.info(f"Stored transaction {transaction_id} in database")
            else:
                logger.warning(f"Incomplete data in message: {data}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def start(self):
        logger.info("Starting DB Service")
        
        try:
            # Connect to database
            self.connect_to_db()
            
            # Setup Kafka consumer
            self.setup_kafka_consumer()
            
            # Start consuming messages
            self.running = True
            logger.info("Starting to consume messages from Kafka")
            
            while self.running:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    raise KafkaException(msg.error())
                
                self.process_message(msg)
                
        except KeyboardInterrupt:
            logger.info("Service interrupted by user")
        except Exception as e:
            logger.error(f"Error in DB service: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
            if self.db_connection:
                self.db_connection.close()
            logger.info("Service stopped")
    
    def stop(self):
        self.running = False

if __name__ == "__main__":
    # Get configuration from environment variables
    db_host = os.environ.get('DB_HOST', 'postgres')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'frauddb')
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD', 'postgres')
    
    bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    topic = os.environ.get('KAFKA_SCORES_TOPIC', 'scores')
    group_id = os.environ.get('KAFKA_GROUP_ID', 'db-service')
    
    # Create and start service
    db_service = PostgresDBService(
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        bootstrap_servers=bootstrap_servers, 
        topic=topic,
        group_id=group_id
    )
    
    db_service.start() 