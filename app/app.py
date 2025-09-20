from flask import Flask, jsonify, request
import random
import logging
import sys

app = Flask(__name__)

# Set up logging to stdout for CloudWatch
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to simulate a bad deployment
# We will change this from False to True to introduce a bug
BUG_ENABLED = False

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
    global BUG_ENABLED
    account_id = request.args.get('account_id', 'default_account')
    amount = int(request.args.get('amount', 50))

    # SIMULATE A BAD DEPLOYMENT BUG
    if BUG_ENABLED:
        logger.error(f"CRITICAL BUG: Unable to process withdrawal for {account_id}. Database connection failed!")
        return jsonify({"error": "Internal Server Error: Cannot connect to database."}), 500

    # Normal successful operation
    logger.info(f"Withdrawal of ${amount} for {account_id} processed successfully.")
    return jsonify({"account_id": account_id, "withdrawn": amount, "status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
