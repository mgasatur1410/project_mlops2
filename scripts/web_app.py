import os
import logging
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template, Response, jsonify

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FraudDashboardApp:
    def __init__(self, db_host, db_port, db_name, db_user, db_password):
        self.app = Flask(__name__, template_folder='templates')
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.db_connection = None
        
        # Initialize routes
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html')
            
        @self.app.route('/api/fraud-transactions')
        def fraud_transactions():
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                query = """
                SELECT transaction_id, score, fraud_flag, created_at
                FROM transaction_scores
                WHERE fraud_flag = 1
                ORDER BY created_at DESC
                LIMIT 10;
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    results.append({
                        'transaction_id': row[0],
                        'score': float(row[1]),
                        'fraud_flag': row[2],
                        'created_at': row[3].strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                cursor.close()
                
                return jsonify(results)
            except Exception as e:
                logger.error(f"Error getting fraud transactions: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/score-histogram')
        def score_histogram():
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                query = """
                SELECT score
                FROM transaction_scores
                ORDER BY created_at DESC
                LIMIT 100;
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                scores = [float(row[0]) for row in rows]
                cursor.close()
                
                if not scores:
                    return jsonify({'error': 'No data available for histogram'}), 404
                
                # Generate histogram
                plt.figure(figsize=(10, 5))
                plt.hist(scores, bins=20, alpha=0.7)
                plt.title('Distribution of scores (last 100 transactions)')
                plt.xlabel('Score')
                plt.ylabel('Frequency')
                plt.grid(True, alpha=0.3)
                
                # Convert plot to PNG
                img = io.BytesIO()
                plt.savefig(img, format='png')
                plt.close()
                img.seek(0)
                
                return Response(
                    img.getvalue(),
                    mimetype='image/png'
                )
            except Exception as e:
                logger.error(f"Error generating histogram: {e}")
                return jsonify({'error': str(e)}), 500
    
    def get_db_connection(self):
        if self.db_connection is None:
            try:
                self.db_connection = psycopg2.connect(
                    host=self.db_host,
                    port=self.db_port,
                    dbname=self.db_name,
                    user=self.db_user,
                    password=self.db_password
                )
            except Exception as e:
                logger.error(f"Failed to connect to the database: {e}")
                raise
        return self.db_connection
    
    def start(self, host='0.0.0.0', port=5000):
        self.app.run(host=host, port=port)

# Create templates directory if it doesn't exist
def setup_templates():
    os.makedirs('templates', exist_ok=True)
    
    # Create index.html
    with open('templates/index.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fraud Transaction Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .card {
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        .btn {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
        }
        .btn:hover {
            background-color: #2980b9;
        }
        .histogram {
            width: 100%;
            max-height: 400px;
        }
        .loading {
            text-align: center;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Fraud Transaction Dashboard</h1>
            <p>Monitor and analyze fraud transactions in real-time</p>
        </div>
        
        <div class="card">
            <h2>Actions</h2>
            <button id="loadDataBtn" class="btn">Посмотреть результаты</button>
        </div>
        
        <div class="card">
            <h2>Recent Fraud Transactions</h2>
            <div id="fraudTable">
                <p class="loading">Click "Посмотреть результаты" to load data</p>
            </div>
        </div>
        
        <div class="card">
            <h2>Score Distribution (Last 100 Transactions)</h2>
            <div id="histogram">
                <p class="loading">Click "Посмотреть результаты" to load data</p>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const loadDataBtn = document.getElementById('loadDataBtn');
            const fraudTable = document.getElementById('fraudTable');
            const histogram = document.getElementById('histogram');
            
            loadDataBtn.addEventListener('click', function() {
                loadFraudTransactions();
                loadHistogram();
            });
            
            function loadFraudTransactions() {
                fraudTable.innerHTML = '<p class="loading">Loading fraud transactions...</p>';
                
                fetch('/api/fraud-transactions')
                    .then(response => response.json())
                    .then(data => {
                        if (data.length === 0) {
                            fraudTable.innerHTML = '<p>No fraud transactions found.</p>';
                            return;
                        }
                        
                        let tableHTML = `
                            <table>
                                <thead>
                                    <tr>
                                        <th>Transaction ID</th>
                                        <th>Fraud Score</th>
                                        <th>Timestamp</th>
                                    </tr>
                                </thead>
                                <tbody>
                        `;
                        
                        data.forEach(item => {
                            tableHTML += `
                                <tr>
                                    <td>${item.transaction_id}</td>
                                    <td>${item.score.toFixed(4)}</td>
                                    <td>${item.created_at}</td>
                                </tr>
                            `;
                        });
                        
                        tableHTML += `
                                </tbody>
                            </table>
                        `;
                        
                        fraudTable.innerHTML = tableHTML;
                    })
                    .catch(error => {
                        fraudTable.innerHTML = `<p>Error loading data: ${error}</p>`;
                    });
            }
            
            function loadHistogram() {
                histogram.innerHTML = '<p class="loading">Generating histogram...</p>';
                
                // Use a timestamp to prevent caching
                const timestamp = new Date().getTime();
                const img = new Image();
                img.onload = function() {
                    histogram.innerHTML = '';
                    img.className = 'histogram';
                    histogram.appendChild(img);
                };
                img.onerror = function() {
                    histogram.innerHTML = '<p>No data available for histogram or error loading image</p>';
                };
                img.src = `/api/score-histogram?t=${timestamp}`;
            }
        });
    </script>
</body>
</html>
        ''')

if __name__ == "__main__":
    # Setup templates
    setup_templates()
    
    # Get configuration from environment variables
    db_host = os.environ.get('DB_HOST', 'postgres')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'frauddb')
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD', 'postgres')
    
    web_host = os.environ.get('WEB_HOST', '0.0.0.0')
    web_port = int(os.environ.get('WEB_PORT', '5000'))
    
    # Create and start app
    app = FraudDashboardApp(
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password
    )
    
    app.start(host=web_host, port=web_port) 