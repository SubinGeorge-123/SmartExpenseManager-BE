# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
import uuid
from datetime import datetime
from decimal import Decimal
import requests
 
# --- CONFIG ---
AWS_REGION = "us-east-1"
S3_BUCKET = "compressed-image-for-expense-manger"
DYNAMO_TABLE = "ExpenseManager"
TRIP_API_URL = "https://p0qyqh56t8.execute-api.us-east-1.amazonaws.com/dev/plan-trip"
CHART_API_URL = "https://c2n5uhe770.execute-api.us-east-1.amazonaws.com/Prod/chart"
 
# --- INIT ---
app = Flask(__name__)
CORS(app)  # allow requests from React
 
s3 = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMO_TABLE)
 
 
# --- POST /submit-expense ---
@app.route("/submit-expense", methods=["POST"])
def submit_expense():
    try:
        # --- GET FORM DATA ---
        image_file = request.files.get("image")  # file
        category = request.form.get("category")
        amount = request.form.get("amount")
        location = request.form.get("location")
 
        # --- VALIDATION ---
        if not category or not amount:
            return jsonify({"error": "Category and amount are required"}), 400
 
        # --- GENERATE UNIQUE ID ---
        expense_id = str(uuid.uuid4())
        image_url = ""
 
        # --- UPLOAD IMAGE TO S3 ---
        if image_file:
            s3_key = f"expenses/{expense_id}_{image_file.filename}"
            s3.upload_fileobj(
            image_file,
            S3_BUCKET,
            s3_key,
            ExtraArgs={"ContentType": image_file.content_type}
            )
            image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}"
 
        # --- SAVE TO DYNAMODB ---
        item = {
            "expense_id": expense_id,
            "category": category,
            "amount": Decimal(str(amount)),
            "location": location,
            "image_url": image_url,
            "created_at": datetime.utcnow().isoformat()
        }
 
        table.put_item(Item=item)
 
        return jsonify({"message": "Expense saved successfully", "expense_id": expense_id, "data": item})
 
    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
 
# --- GET /expenses ---
@app.route("/expenses", methods=["GET"])
def get_expenses():
    try:
        response = table.scan()
        items = response.get("Items", [])
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
@app.route("/expense/<expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    try:
        # get item first
        response = table.get_item(Key={"expense_id": expense_id})
        item = response.get("Item")
 
        if not item:
            return jsonify({"error": "Expense not found"}), 404
 
        # delete image from S3 if exists    
        image_url = item.get("image_url")
 
        if image_url:
            s3_key = image_url.split(".com/")[1]
            s3.delete_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            ExpectedBucketOwner='YOUR_AWS_ACCOUNT_ID'  
            )
 
        # delete from DynamoDB
        table.delete_item(Key={"expense_id": expense_id})
 
        return jsonify({"message": "Expense deleted successfully"})
 
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# --- POST /plan-trip ---
@app.route("/plan-trip", methods=["POST"])
def plan_trip():
    try:
        data = request.json  # get JSON from React
 
        # call friend's API
        response = requests.post(TRIP_API_URL, json=data)
 
        # return response from friend's API
        return jsonify({
            "status": "success",
            "trip_plan": response.json()
        }), response.status_code
 
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# --- POST /generate-chart ---
@app.route("/generate-chart", methods=["POST"])
def generate_chart():
    try:
        data = request.json  # get JSON from React
 
        headers = {
            "Content-Type": "application/json"
        }
 
        # call external chart API
        response = requests.post(
            CHART_API_URL,
            json=data,
            headers=headers
        )
 
        return jsonify({
            "status": "success",
            "chart_response": response.json()
        }), response.status_code
 
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# --- RUN ---
if __name__ == "__main__":
    import os
    host = os.environ.get('FLASK_HOST', '127.0.0.1')  # Default to localhost only
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host=host, port=port, debug=debug)