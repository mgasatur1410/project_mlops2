import os
import logging
from catboost import CatBoostClassifier
from kafka_consumer import KafkaMessageConsumer
from kafka_producer import KafkaResultProducer
import time

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FraudScoringService:
    def __init__(self, 
                bootstrap_servers,
                input_topic, 
                output_topic,
                group_id,
                model_path='model/catboost_model.cbm'):
        self.bootstrap_servers = bootstrap_servers
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.group_id = group_id
        self.model_path = model_path
        self.model = None
        self.consumer = None
        self.producer = None
        
    def load_model(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file {self.model_path} not found!")
            
        logger.info(f"Loading model from {self.model_path}")
        self.model = CatBoostClassifier()
        self.model.load_model(self.model_path)
        logger.info("Model loaded successfully")
        
    def setup_kafka(self):
        logger.info("Setting up Kafka consumer and producer")
        
        # Setup consumer
        self.consumer = KafkaMessageConsumer(
            bootstrap_servers=self.bootstrap_servers,
            topic=self.input_topic,
            group_id=self.group_id
        )
        self.consumer.setup_consumer()
        
        # Setup producer
        self.producer = KafkaResultProducer(
            bootstrap_servers=self.bootstrap_servers,
            topic=self.output_topic
        )
        self.producer.setup_producer()
        
    def process_transaction(self, transaction_df, transaction_key):
        try:
            # Extract transaction ID (assuming it's in the dataframe)
            transaction_id = transaction_key
            if transaction_id is None and 'index' in transaction_df.columns:
                transaction_id = transaction_df['index'].iloc[0]
                
            # Get features for prediction
            features = [c for c in transaction_df.columns if c not in ['index', 'transaction_time']]
            
            # Make prediction
            score = self.model.predict_proba(transaction_df[features])[0, 1]
            fraud_flag = int(score > 0.5)
            
            # Send result to Kafka
            self.producer.send_result(transaction_id, score, fraud_flag)
            
            logger.info(f"Processed transaction {transaction_id}: score={score:.4f}, fraud={fraud_flag}")
            
        except Exception as e:
            logger.error(f"Error processing transaction: {e}")
    
    def start(self):
        logger.info("Starting Fraud Scoring Service")
        
        try:
            # Load model
            self.load_model()
            
            # Setup Kafka
            self.setup_kafka()
            
            # Start processing
            logger.info("Starting to consume messages...")
            self.consumer.consume_messages(self.process_transaction)
            
        except KeyboardInterrupt:
            logger.info("Service interrupted by user")
        except Exception as e:
            logger.error(f"Error in service: {e}")
        finally:
            if self.consumer:
                self.consumer.stop()
            if self.producer:
                self.producer.flush()
            logger.info("Service stopped")
            
if __name__ == "__main__":
    # Get configuration from environment variables with defaults
    bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    input_topic = os.environ.get('KAFKA_INPUT_TOPIC', 'transactions')
    output_topic = os.environ.get('KAFKA_OUTPUT_TOPIC', 'scores')
    group_id = os.environ.get('KAFKA_GROUP_ID', 'fraud-scoring-service')
    model_path = os.environ.get('MODEL_PATH', 'model/catboost_model.cbm')
    
    # Create and start service
    service = FraudScoringService(
        bootstrap_servers=bootstrap_servers,
        input_topic=input_topic,
        output_topic=output_topic,
        group_id=group_id,
        model_path=model_path
    )
    
    service.start() 