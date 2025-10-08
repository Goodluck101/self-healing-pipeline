# # 

# from flask import Flask, jsonify, request
# import random
# import logging
# import sys
# import os  # Add this import

# app = Flask(__name__)

# # Set up logging to stdout for CloudWatch
# logging.basicConfig(stream=sys.stdout, level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Read the BUG_ENABLED flag from environment variable at runtime
# def is_bug_enabled():
#     return os.getenv('BUG_ENABLED', 'False').lower() == 'true'

# @app.route('/')
# def home():
#     logger.info("Home endpoint was called successfully.")
#     return jsonify({"message": "Welcome to Simple Bank API v1.0", "status": "healthy"})

# @app.route('/balance')
# def balance():
#     account_id = request.args.get('account_id', 'default_account')
#     bal = random.randint(100, 9999)
#     logger.info(f"Balance of {account_id} is ${bal}.")
#     return jsonify({"account_id": account_id, "balance": bal})

# @app.route('/withdraw')
# def withdraw():
#     # Check if the bug is enabled at runtime
#     if is_bug_enabled():
#         account_id = request.args.get('account_id', 'default_account')
#         logger.error(f"CRITICAL BUG: Unable to process withdrawal for {account_id}. Database connection failed!")
#         return jsonify({"error": "Internal Server Error: Cannot connect to database."}), 500
    
# @app.route("/api/health", methods=["GET"])
# def health():
#     return jsonify({"status": "ok"}), 200

#     # Normal successful operation
#     account_id = request.args.get('account_id', 'default_account')
#     amount = int(request.args.get('amount', 50))
#     logger.info(f"Withdrawal of ${amount} for {account_id} processed successfully.")
#     return jsonify({"account_id": account_id, "withdrawn": amount, "status": "success"})

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)

####
from flask import Flask, jsonify, request
import random
import logging
import sys
import os

app = Flask(__name__)

# Set up logging to stdout for CloudWatch
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory variable to override the environment flag dynamically
bug_enabled_runtime = None

# Updated function to respect runtime override
def is_bug_enabled():
    global bug_enabled_runtime
    if bug_enabled_runtime is not None:
        return bug_enabled_runtime
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
    account_id = request.args.get('account_id', 'default_account')
    amount = int(request.args.get('amount', 50))

    # Simulate a bug when BUG_ENABLED is true
    if is_bug_enabled():
        logger.error(f"CRITICAL BUG: Unable to process withdrawal for {account_id}. Database connection failed!")
        return jsonify({"error": "Internal Server Error: Cannot connect to database."}), 500

    # Normal successful operation
    logger.info(f"Withdrawal of ${amount} for {account_id} processed successfully.")
    return jsonify({"account_id": account_id, "withdrawn": amount, "status": "success"})

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/debug/bug-flag")
def debug_bug_flag():
    return jsonify({"BUG_ENABLED": is_bug_enabled()})

# New route to toggle the bug flag dynamically (no restart needed)
@app.route("/toggle-bug", methods=["POST", "GET"])
def toggle_bug():
    global bug_enabled_runtime

    enable = request.args.get('enable', '').lower()
    if enable in ['true', '1', 'yes']:
        bug_enabled_runtime = True
        logger.warning("Runtime BUG_ENABLED flag set to TRUE (Simulating system failure).")
        return jsonify({"message": "BUG_ENABLED set to True (bug simulated)."})
    elif enable in ['false', '0', 'no']:
        bug_enabled_runtime = False
        logger.info("Runtime BUG_ENABLED flag set to FALSE (System stabilized).")
        return jsonify({"message": "BUG_ENABLED set to False (system healed)."})
    else:
        return jsonify({"error": "Invalid value. Use ?enable=true or ?enable=false."}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
