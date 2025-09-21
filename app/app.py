# 

from flask import Flask, jsonify, request
import random
import logging
import sys
import os  # Add this import

app = Flask(__name__)

# Set up logging to stdout for CloudWatch
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

# Read the BUG_ENABLED flag from environment variable at runtime
def is_bug_enabled():
    return os.getenv('BUG_ENABLED', 'False').lower() == 'true'

@app.route('/')
def home():
    logger.info("Home endpoint was called successfully.")
    return jsonify({"message": "Welcome to Simple Bank API v1.0", "status": "healthy"})

@app.route('/balance')
def balance():
    account_id = request.args.get('account_id', 'default_account')
    bal = random.randint(100, 9999)
    logger.info(f"Balance of {account_id} is ${bal}.")
    return jsonify({"account_id": account_id, "balance": bal})

@app.route('/withdraw')
def withdraw():
    # Check if the bug is enabled at runtime
    if is_bug_enabled():
        account_id = request.args.get('account_id', 'default_account')
        logger.error(f"CRITICAL BUG: Unable to process withdrawal for {account_id}. Database connection failed!")
        return jsonify({"error": "Internal Server Error: Cannot connect to database."}), 500

    # Normal successful operation
    account_id = request.args.get('account_id', 'default_account')
    amount = int(request.args.get('amount', 50))
    logger.info(f"Withdrawal of ${amount} for {account_id} processed successfully.")
    return jsonify({"account_id": account_id, "withdrawn": amount, "status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)