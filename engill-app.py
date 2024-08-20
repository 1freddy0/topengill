from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from datetime import datetime
import json
import traceback
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///engilla.db'
app.config['SECRET_KEY'] = '5236789eea3265b7eb1ec73b585380313846993c16b6a80f370245c72d14b777'
db = SQLAlchemy(app)

# Flutterwave Configuration
FLUTTERWAVE_SECRET_KEY = 'FLWSECK_TEST-214b0d836324dd9be7567f09a8a37282-X'  # Replace with your actual secret key

# Models
class UserLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_inputs = db.Column(db.Text)
    clicks = db.Column(db.Integer)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    content = db.Column(db.Text)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    transaction_id = db.Column(db.String(255), unique=True)
    amount = db.Column(db.Float)
    currency = db.Column(db.String(3))
    status = db.Column(db.String(20))

class UserVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_ip = db.Column(db.String(50), unique=True)
    visit_count = db.Column(db.Integer, default=1)
    last_visit = db.Column(db.DateTime, default=datetime.utcnow)

# Admin views
class UserLogView(ModelView):
    column_list = ('timestamp', 'user_inputs', 'clicks')
    column_searchable_list = ['user_inputs']
    column_filters = ['timestamp']

class FeedbackView(ModelView):
    column_list = ('timestamp', 'content')
    column_searchable_list = ['content']
    column_filters = ['timestamp']

class PaymentView(ModelView):
    column_list = ('timestamp', 'transaction_id', 'amount', 'currency', 'status')
    column_searchable_list = ['transaction_id']
    column_filters = ['timestamp', 'status']

class UserVisitView(ModelView):
    column_list = ('user_ip', 'visit_count', 'last_visit')
    column_searchable_list = ['user_ip']
    column_filters = ['last_visit']

admin = Admin(app, name='Engilla Admin', template_mode='bootstrap3')
admin.add_view(UserLogView(UserLog, db.session))
admin.add_view(FeedbackView(Feedback, db.session))
admin.add_view(PaymentView(Payment, db.session))
admin.add_view(UserVisitView(UserVisit, db.session))

recommendations = {
    "dusty": {
        "recommendation": "API SM, SN OR API SN PLUS 5W-30, 0W-40, 15W-40",
        "response": "High viscosity oils, better protection against contaminants and engine wear. Viscosity grades offer a good balance between flow characteristics at low temperature and protection at high temperature essential for dusty conditions."
    },
    "heavy_traffic": {
        "recommendation": "API SM, SN 5W-30, 10W-30, 0W-40 10W-40 15W-40, (SYNTHETIC: OPTIONAL),(OIL BRAND: OPTIONAL)",
        "response": "High viscosity index enhancer and detergent additives. These oils offer better engine protection, Temperature stability, engine cleanness, corrosion prevention and engine better seal conditioning."
    },
    "cold": {
        "recommendation": "API SM, SN 0W-40, 5W-40, (0W-50 EXTREME COLD)",
        "response": "Suitable for both cold starts and high temperature operation, good flow in cold weather while maintaining stability at high temperature. SYNTHETIC: OPTIONAL | OIL BRAND: OPTIONAL"
    },
    
    "heavy_load": {
        "recommendation": "API SM, API SN 10W-40, 15W-40, 20W-50, SAE 40, High viscosity oils",
        "response": "(Trucks and Buses and Towing vehicle) good cold start capabilities formulated with additives to withstand additional stress and heat generated by heavy loads and extended driving period."
    },
    "long_trips": {
        "recommendation": "API SM/API SN 5W-30, 10W-40, 15w 40. High viscosity oils.",
        "response": "Driving for extended period offers good flow characteristics at low temperature while providing adequate viscosity at higher temperature to maintain proper lubrication for better protection against heat and engine wear during extended periods of driving. SYNTHETIC OIL: OPTIONAL | OIL BRAND: OPTIONAL"
    },
    "short_trips": {
        "recommendation": "API SM, API SN 5W-30, 5W-40, 10W-30",
        "response": "Frequent short trips can lead to increased moisture build up in the oil. Lower viscosity oil with good detergent properties is required to combat sludge formation and ensure proper lubrication during cold start and short operating cycles. 5w-30 oil is perfect, flows well at lower temperatures providing adequate protection during short trips, frequent starts and stops."
    },
    "smokey": {
        "recommendation": "API SM, API SN 10W-30, 10W-40, 20W-50, SAE 40",
        "response": "high viscosity oils to reduce oil consumption and smoke, compensate for engine wear, and maintain proper lubrication. Good flow characteristics at low temperature, provides adequate protection under normal driving conditions. Engine diagnosis may be your best option."
    }
    
    # ... (existing recommendations dictionary)
}

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/verify-payment', methods=['GET'])
def verify_payment():
    transaction_id = request.args.get('transaction_id')
    
    # Verify the transaction with Flutterwave
    url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {FLUTTERWAVE_SECRET_KEY}'
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'success':
            # Payment successful, save to database
            payment = Payment(
                transaction_id=transaction_id,
                amount=data['data']['amount'],
                currency=data['data']['currency'],
                status='success'
            )
            db.session.add(payment)
            db.session.commit()
            return jsonify({"status": "success", "message": "Payment verified successfully"})
    
    return jsonify({"status": "error", "message": "Payment verification failed"}), 400

@app.route('/recommend', methods=['POST'])
def recommend_oil():
    data = request.json
    user_ip = request.remote_addr

    # Check if user is a first-time visitor
    user_visit = UserVisit.query.filter_by(user_ip=user_ip).first()
    is_first_visit = user_visit is None

    if is_first_visit:
        # Create new user visit record
        new_visit = UserVisit(user_ip=user_ip)
        db.session.add(new_visit)
        db.session.commit()
    else:
        # Update existing user visit record
        user_visit.visit_count += 1
        user_visit.last_visit = datetime.utcnow()
        db.session.commit()

        # Check payment for non-first-time users
        transaction_id = data.get('transaction_id')
        payment = Payment.query.filter_by(transaction_id=transaction_id, status='success').first()
        if not payment:
            return jsonify({"error": "Payment required", "message": "Please make a payment to receive a recommendation"}), 400

    conditions = data.get('conditions', [])
    
    # Log user inputs
    user_log = UserLog(
        user_inputs=json.dumps(data),
        clicks=len(conditions)
    )
    db.session.add(user_log)
    db.session.commit()
    if not conditions:
        return jsonify({
            "recommendation": "Go with Manufacturer's specification",
            "response": "No specific conditions selected. Please refer to your vehicle's manual for the recommended oil type."
        })

    if len(conditions) >= 2:
        if set(conditions) == {"dusty", "heavy_traffic", "cold", "high_mileage"}:
            return jsonify({
                "recommendation": "API SM, SN 5w-30, 10w-30, 5w-40",
                "response": "High viscosity oils, better engine protection against contaminants and wares. Good flow characteristics at low and high operating temperature in dusty, heavy traffic and engine stress conditions. Detergent additives in 5w-30 makes it more suitable to keep engine clean, and protect it against sludge buildup."
            })
        elif set(conditions) == {"heavy_load", "long_trips", "short_trips", "smokey"}:
            return jsonify({
                "recommendation": "API SM, SN Thicker Engine oils: 10w-40, 15w-40. (Smokey: 20w 50, SAE 40)",
                "response": "These oils are suitable for regular long or short trips. Better engine protection, Temperature stability, engine cleanness, corrosion prevention, engine better seal conditioning in a very heavy load environment. Contain additives that form protective layer on engine surface."
            })
        else:
            return jsonify({
                "recommendation": "API SM, SN 5W-30, 5W-40, 10W-40",
                "response": "High viscosity oils with good flow characteristics at low and high temperature, providing adequate protection under various operating conditions."
            })

    if len(conditions) == 1:
        condition = conditions[0]
        if condition in recommendations:
            return jsonify(recommendations[condition])

    return jsonify({
        "recommendation": "API SM, SN 5W-30, 5W-40, 10W-40",
        "response": "High viscosity oils with good flow characteristics at low and high temperature, providing adequate protection under various operating conditions."
    })


@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json
    feedback_content = data.get('feedback', '')
    
    if feedback_content:
        feedback_entry = Feedback(content=feedback_content)
        db.session.add(feedback_entry)
        db.session.commit()
        return jsonify({"status": "success", "message": "Feedback submitted successfully"})
    else:
        return jsonify({"status": "error", "message": "Feedback content cannot be empty"}), 400

@app.route('/check-first-visit')
def check_first_visit():
    user_ip = request.remote_addr
    user_visit = UserVisit.query.filter_by(user_ip=user_ip).first()
    is_first_visit = user_visit is None
    return jsonify({"is_first_visit": is_first_visit})

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify(error=str(error), stacktrace=traceback.format_exc()), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)