import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database Configuration
def get_db_connection():
    try:
        client = MongoClient(
            "mongodb://localhost:27017/",
            serverSelectionTimeoutMS=5000
        )
        # Verify connection
        client.admin.command('ping')
        print("✓ Connected to MongoDB successfully")
        return client["hospital_a_db"]
    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        return None

db = get_db_connection()

# Helper Functions
def validate_login_input(staff_id, name):
    if not staff_id or not name:
        return False, "Both staff ID and name are required"
    if len(staff_id) < 5 or '_' not in staff_id:
        return False, "Invalid staff ID format"
    return True, ""

# API Routes
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        staff_id = data.get('staff_id', '').upper().strip()
        name = data.get('name', '').title().strip()

        is_valid, error_msg = validate_login_input(staff_id, name)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # User type mapping
        user_types = {
            "DOC_": ("doctors", "doctor"),
            "NUR_": ("nurses", "nurse"),
            "ADM_": ("administrators", "admin")
        }

        for prefix, (collection, user_type) in user_types.items():
            if staff_id.startswith(prefix):
                staff = db[collection].find_one({
                    f"{user_type}_id": staff_id,
                    "name": name
                })
                
                if staff:
                    user_info = {
                        "id": staff_id,
                        "name": name,
                        "type": user_type,
                        "department": staff.get("department", "General"),
                        "contact": staff.get("contact", "")
                    }
                    return jsonify({"success": True, "user": user_info})

        return jsonify({"error": "Invalid credentials"}), 401

    except PyMongoError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/api/command', methods=['POST'])
def handle_command():
    try:
        if not db:
            return jsonify({"error": "Database connection failed"}), 500

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        command = data.get('command', '').lower().strip()
        params = data.get('params', {})

        # Command handlers
        if command == 'search_patient':
            name = params.get('name', '').strip()
            if not name:
                return jsonify({"error": "Name parameter is required"}), 400

            patients = list(db.patients.find(
                {"name": {"$regex": name, "$options": "i"}},
                {"_id": 0}
            ).limit(10))
            return jsonify({"result": patients})

        elif command == 'patient_details':
            patient_id = params.get('patient_id', '').strip()
            if not patient_id:
                return jsonify({"error": "Patient ID is required"}), 400

            patient = db.patients.find_one(
                {"patient_id": patient_id},
                {"_id": 0}
            )
            if not patient:
                return jsonify({"error": "Patient not found"}), 404

            related_data = {
                "admissions": list(db.admissions.find(
                    {"patient_id": patient_id}, {"_id": 0}
                )),
                "diagnoses": list(db.diagnoses.find(
                    {"patient_id": patient_id}, {"_id": 0}
                )),
                "prescriptions": list(db.prescriptions.find(
                    {"patient_id": patient_id}, {"_id": 0}
                ))
            }
            return jsonify({"patient": patient, **related_data})

        return jsonify({"error": "Invalid command"}), 400

    except PyMongoError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
