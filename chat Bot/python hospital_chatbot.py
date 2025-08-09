import os
from datetime import datetime
from typing import Dict, List, Optional, Union
from pymongo import MongoClient, errors
from difflib import get_close_matches
import spacy
from termcolor import colored
import sys
import csv
from bson import ObjectId

# Load English language model for NLP
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print(colored("\nERROR: SpaCy English language model not found.", "red"))
    print(colored("Please install it by running:", "yellow"))
    print(colored("python -m spacy download en_core_web_sm\n", "cyan"))
    sys.exit(1)

class HospitalChatbot:
    def __init__(self):
        self.db = self.get_db_connection()
        self.current_user = None
        self.user_type = None
        self.setup_commands()
        self.setup_responses()

    def get_db_connection(self):
        """Establish connection to MongoDB with error handling"""
        try:
            client = MongoClient(
                "mongodb://localhost:27017/",
                serverSelectionTimeoutMS=5000,
                socketTimeoutMS=30000,
                connectTimeoutMS=10000
            )
            client.admin.command('ping')
            print(colored("✓ Connected to MongoDB", "green"))
            return client["hospital_a_db"]
        except errors.ServerSelectionTimeoutError:
            print(colored("\nERROR: Could not connect to MongoDB.", "red"))
            print(colored("1. Ensure MongoDB is running ('mongod' in command prompt)", "yellow"))
            print(colored("2. Check port 27017 is not blocked by firewall\n", "yellow"))
            return None

    def setup_commands(self):
        """Initialize the command structure"""
        self.commands = {
            "common": {
                "help": ["help", "commands", "what can you do"],
                "login": ["login", "sign in"],
                "logout": ["logout", "sign out"],
                "exit": ["exit", "quit", "goodbye"]
            },
            "doctor": {
                "search_patient": ["find patient", "search patient", "lookup patient"],
                "patient_details": ["patient details", "get patient info"],
                "admission_history": ["admission history", "patient admissions"],
                "create_prescription": ["new prescription", "prescribe medication"],
                "view_schedule": ["my schedule", "today's appointments"],
                "add_note": ["add note", "write note"]
            },
            "nurse": {
                "medication_list": ["medication list", "todays medications"],
                "record_administration": ["record medication", "give medication"],
                "patient_vitals": ["record vitals", "patient vitals"],
                "view_applications": ["view tests", "test applications"]
            },
            "admin": {
                "add_staff": ["add staff", "new staff"],
                "generate_report": ["generate report", "create report"]
            }
        }

    def setup_responses(self):
        """Predefined responses for common queries"""
        self.responses = {
            "greetings": ["hello", "hi", "hey", "good morning", "good afternoon"],
            "farewells": ["bye", "goodbye", "see you", "exit", "quit"],
            "thanks": ["thank you", "thanks", "appreciate"],
            "apologies": ["sorry", "apologize", "my bad"]
        }

    def start(self):
        """Main chatbot interface"""
        print(colored("\n🏥 Hospital Management System Chatbot", "blue", attrs=["bold"]))
        print(colored("Type 'help' for assistance or 'exit' to quit\n", "cyan"))
        
        while True:
            try:
                user_input = input(colored("You: ", "green")).strip().lower()
                
                if not user_input:
                    continue
                
                if self.check_response_type(user_input, "farewells"):
                    self.handle_exit()
                    break
                
                if self.check_response_type(user_input, "greetings"):
                    print(colored("Chatbot: Hello! How can I assist you today?", "yellow"))
                    continue
                
                if self.check_response_type(user_input, "thanks"):
                    print(colored("Chatbot: You're welcome! Is there anything else I can help with?", "yellow"))
                    continue
                
                if self.check_response_type(user_input, "apologies"):
                    print(colored("Chatbot: No problem at all. How can I assist you?", "yellow"))
                    continue
                
                if "help" in user_input:
                    self.show_help()
                    continue
                
                if "login" in user_input:
                    self.handle_login()
                    continue
                
                if "logout" in user_input:
                    self.handle_logout()
                    continue
                
                if not self.current_user:
                    print(colored("Chatbot: Please login first. Type 'login' to begin.", "yellow"))
                    continue
                
                self.process_command(user_input)
                
            except KeyboardInterrupt:
                self.handle_exit()
                break
            except Exception as e:
                print(colored(f"\nERROR: {str(e)}", "red"))

    def check_response_type(self, text: str, response_type: str) -> bool:
        """Check if text matches any predefined responses"""
        return any(word in text for word in self.responses.get(response_type, []))

    def show_help(self):
        """Show help information"""
        print(colored("\nAvailable commands:", "cyan", attrs=["bold"]))
        print(colored("------------------", "cyan"))
        
        # General commands
        print(colored("\nGeneral commands:", "yellow"))
        for cmd, phrases in self.commands["common"].items():
            print(f"- {cmd}: {', '.join(phrases[:3])}...")
        
        # Role-specific commands
        if self.current_user:
            print(colored(f"\n{self.user_type.capitalize()} commands:", "yellow"))
            for cmd, phrases in self.commands.get(self.user_type, {}).items():
                print(f"- {cmd}: {', '.join(phrases[:2])}...")
        print()

    def handle_login(self):
        """Handle user login"""
        if self.current_user:
            print(colored("You are already logged in. Type 'logout' first.", "yellow"))
            return
            
        print(colored("\nLogin Process", "blue", attrs=["bold"]))
        print(colored("-------------", "blue"))
        
        staff_id = input(colored("Staff ID (e.g., DOC_001 or NUR_001): ", "green")).strip().upper()
        name = input(colored("Your full name: ", "green")).strip().title()
        
        if not staff_id or not name:
            print(colored("Both fields are required.", "yellow"))
            return
        
        # Determine user type and verify credentials
        if staff_id.startswith("DOC_"):
            collection = "doctors"
            self.user_type = "doctor"
        elif staff_id.startswith("NUR_"):
            collection = "nurses"
            self.user_type = "nurse"
        elif staff_id.startswith("ADM_"):
            collection = "administrators"
            self.user_type = "admin"
        else:
            print(colored("Invalid staff ID format. Must start with DOC_, NUR_, or ADM_.", "yellow"))
            return
        
        staff = self.db[collection].find_one({
            f"{self.user_type}_id": staff_id,
            "name": name
        })
        
        if staff:
            self.current_user = {
                "id": staff_id,
                "name": name,
                "type": self.user_type,
                "department": staff.get("department", "Unknown"),
                "contact": staff.get("contact", "N/A")
            }
            print(colored(f"\nWelcome, {name}! You're logged in as {self.user_type}.", "green"))
            self.show_help()
        else:
            print(colored("\nAuthentication failed. Please check your credentials.", "red"))

    def handle_logout(self):
        """Handle user logout"""
        if self.current_user:
            print(colored(f"Goodbye, {self.current_user['name']}! You've been logged out.", "yellow"))
            self.current_user = None
            self.user_type = None
        else:
            print(colored("No user is currently logged in.", "yellow"))

    def handle_exit(self):
        """Clean up before exiting"""
        if self.current_user:
            self.handle_logout()
        print(colored("\nThank you for using the Hospital Management System. Goodbye!\n", "blue"))
        sys.exit(0)

    def process_command(self, user_input: str):
        """Process user input and execute appropriate command"""
        # First check common commands
        for cmd, phrases in self.commands["common"].items():
            if any(phrase in user_input for phrase in phrases):
                getattr(self, f"cmd_{cmd}")(user_input)
                return
        
        # Check role-specific commands if logged in
        if self.current_user:
            for cmd, phrases in self.commands.get(self.user_type, {}).items():
                if any(phrase in user_input for phrase in phrases):
                    getattr(self, f"cmd_{cmd}")(user_input)
                    return
        
        # If no command matched
        print(colored("I didn't understand that. Type 'help' for available commands.", "yellow"))

    def calculate_similarity(self, input_text: str, command_text: str) -> float:
        """Calculate similarity between user input and command phrases"""
        input_doc = nlp(input_text)
        command_doc = nlp(command_text)
        return input_doc.similarity(command_doc)

    # Doctor commands
    def cmd_search_patient(self, _):
        """Search for patients by name"""
        if not self.verify_role("doctor"):
            return
            
        name = input(colored("Enter patient name to search: ", "green")).strip()
        
        if not name:
            print(colored("Please enter a name to search.", "yellow"))
            return
        
        patients = list(self.db.patients.find({
            "name": {"$regex": name, "$options": "i"}
        }).limit(5))
        
        if not patients:
            print(colored("No patients found with that name.", "yellow"))
            return
        
        print(colored("\nSearch Results:", "cyan", attrs=["bold"]))
        for idx, patient in enumerate(patients, 1):
            print(f"{idx}. {patient['name']} (ID: {patient['patient_id']}, DOB: {patient['dob'].strftime('%Y-%m-%d') if patient.get('dob') else 'N/A'})")
        
        self.select_patient_details(patients)

    def verify_role(self, required_role: str) -> bool:
        """Verify the current user has the required role"""
        if not self.current_user:
            print(colored("Please login first.", "yellow"))
            return False
        if self.user_type != required_role:
            print(colored(f"This command is only available for {required_role}s.", "yellow"))
            return False
        return True

    def select_patient_details(self, patients: List[Dict]):
        """Helper to select a patient for detailed view"""
        selection = input(colored("\nEnter number to view details (or press Enter to skip): ", "green")).strip()
        if selection and selection.isdigit():
            selected_idx = int(selection) - 1
            if 0 <= selected_idx < len(patients):
                self.cmd_patient_details(patients[selected_idx]["patient_id"])

    def cmd_patient_details(self, patient_id: str = None):
        """View detailed patient information"""
        if not self.verify_role("doctor"):
            return
            
        if not patient_id:
            patient_id = input(colored("Enter patient ID: ", "green")).strip().upper()
            if not patient_id.startswith("PAT_"):
                print(colored("Invalid patient ID format. Should start with PAT_.", "yellow"))
                return
        
        patient = self.db.patients.find_one({"patient_id": patient_id})
        if not patient:
            print(colored("Patient not found.", "yellow"))
            return
        
        print(colored("\nPatient Details", "blue", attrs=["bold"]))
        print(colored("--------------", "blue"))
        print(f"Name: {patient['name']}")
        print(f"Gender: {patient.get('gender', 'N/A')}")
        print(f"Date of Birth: {patient['dob'].strftime('%Y-%m-%d') if patient.get('dob') else 'N/A'}")
        print(f"Contact: {patient.get('contact', 'N/A')}")
        
        self.show_medical_history(patient_id)

    def show_medical_history(self, patient_id: str):
        """Helper to display patient medical history"""
        admissions = list(self.db.admissions.find({"patient_id": patient_id}))
        
        if admissions:
            print(colored("\nMedical History:", "cyan", attrs=["bold"]))
            for adm in admissions:
                print(f"\nAdmission: {adm['admission_date'].strftime('%Y-%m-%d') if adm.get('admission_date') else 'N/A'}")
                print(f"Department: {adm.get('department', 'N/A')}")
                print(f"Doctor: {adm.get('doctor', 'N/A')}")
                
                diagnoses = list(self.db.diagnoses.find({"admission_id": adm['admission_id']}))
                if diagnoses:
                    print("Diagnoses:")
                    for diag in diagnoses:
                        print(f"- {diag.get('description', 'N/A')} ({diag.get('icd_code', 'N/A')})")

                prescriptions = list(self.db.prescriptions.find({"admission_id": adm['admission_id']}))
                if prescriptions:
                    print("Prescriptions:")
                    for rx in prescriptions:
                        print(f"- {rx.get('drug_name', 'N/A')} {rx.get('dosage', 'N/A')} {rx.get('frequency', 'N/A')}")

    def cmd_admission_history(self, _):
        """View admission history for a patient"""
        if not self.verify_role("doctor"):
            return
            
        patient_id = input(colored("Enter patient ID: ", "green")).strip().upper()
        if not patient_id.startswith("PAT_"):
            print(colored("Invalid patient ID format. Should start with PAT_.", "yellow"))
            return
        
        admissions = list(self.db.admissions.find({"patient_id": patient_id}).sort("admission_date", -1))
        
        if not admissions:
            print(colored("No admissions found for this patient.", "yellow"))
            return
        
        print(colored("\nAdmission History", "blue", attrs=["bold"]))
        print(colored("----------------", "blue"))
        for adm in admissions:
            print(f"\nAdmission ID: {adm['admission_id']}")
            print(f"Date: {adm['admission_date'].strftime('%Y-%m-%d') if adm.get('admission_date') else 'N/A'}")
            print(f"Department: {adm.get('department', 'N/A')}")
            print(f"Doctor: {adm.get('doctor', 'N/A')}")
            
            diagnoses = list(self.db.diagnoses.find({"admission_id": adm['admission_id']}))
            if diagnoses:
                print(colored("\nDiagnoses:", "cyan"))
                for diag in diagnoses:
                    print(f"- {diag.get('description', 'N/A')} ({diag.get('icd_code', 'N/A')})")

    def cmd_create_prescription(self, _):
        """Create a new prescription"""
        if not self.verify_role("doctor"):
            return
            
        print(colored("\nNew Prescription", "blue", attrs=["bold"]))
        print(colored("---------------", "blue"))
        
        patient_id = input(colored("Patient ID: ", "green")).strip().upper()
        if not patient_id.startswith("PAT_"):
            print(colored("Invalid patient ID format.", "yellow"))
            return
        
        patient = self.db.patients.find_one({"patient_id": patient_id})
        if not patient:
            print(colored("Patient not found.", "yellow"))
            return
        
        admission_id = input(colored("Admission ID: ", "green")).strip().upper()
        if not admission_id.startswith("ADM_"):
            print(colored("Invalid admission ID format.", "yellow"))
            return
        
        admission = self.db.admissions.find_one({
            "admission_id": admission_id,
            "patient_id": patient_id
        })
        if not admission:
            print(colored("Admission not found for this patient.", "yellow"))
            return
        
        drug_name = input(colored("Drug name: ", "green")).strip()
        dosage = input(colored("Dosage: ", "green")).strip()
        frequency = input(colored("Frequency: ", "green")).strip()
        
        # Generate new prescription ID
        last_prescription = self.db.prescriptions.find_one(sort=[("prescription_id", -1)])
        last_id = int(last_prescription["prescription_id"][3:]) if last_prescription else 0
        new_id = f"PR_{last_id + 1:03d}"
        
        prescription = {
            "prescription_id": new_id,
            "admission_id": admission_id,
            "patient_id": patient_id,
            "drug_name": drug_name,
            "dosage": dosage,
            "frequency": frequency,
            "prescribed_by": self.current_user["name"],
            "prescribed_at": datetime.now()
        }
        
        try:
            self.db.prescriptions.insert_one(prescription)
            print(colored(f"\n✅ Prescription {new_id} created successfully!", "green"))
            print(colored("Prescription Details:", "cyan"))
            print(f"Patient: {patient['name']}")
            print(f"Drug: {drug_name}")
            print(f"Dosage: {dosage}")
            print(f"Frequency: {frequency}")
        except Exception as e:
            print(colored(f"❌ Error creating prescription: {str(e)}", "red"))

    def cmd_view_schedule(self, _):
        """Show doctor's schedule/appointments"""
        if not self.verify_role("doctor"):
            return
        
        today = datetime.now().strftime("%Y-%m-%d")
        admissions = list(self.db.admissions.find({
            "doctor": self.current_user["name"],
            "admission_date": {"$gte": datetime.strptime(today, "%Y-%m-%d")}
        }).sort("admission_date", 1))
        
        if not admissions:
            print(colored("No upcoming admissions scheduled for you.", "yellow"))
            return
        
        print(colored("\nYour Schedule", "blue", attrs=["bold"]))
        print(colored("------------", "blue"))
        for adm in admissions:
            patient = self.db.patients.find_one({"patient_id": adm["patient_id"]})
            print(f"\nDate: {adm['admission_date'].strftime('%Y-%m-%d') if adm.get('admission_date') else 'N/A'}")
            print(f"Patient: {patient['name'] if patient else 'Unknown'} (ID: {adm['patient_id']})")
            print(f"Department: {adm.get('department', 'N/A')}")
            
            diagnosis = self.db.diagnoses.find_one({"admission_id": adm["admission_id"]})
            if diagnosis:
                print(f"Diagnosis: {diagnosis.get('description', 'N/A')} ({diagnosis.get('icd_code', 'N/A')})")

    def cmd_add_note(self, _):
        """Add a clinical note for a patient"""
        if not self.verify_role("doctor"):
            return
            
        print(colored("\nAdd Clinical Note", "blue", attrs=["bold"]))
        print(colored("----------------", "blue"))
        
        admission_id = input(colored("Admission ID: ", "green")).strip().upper()
        if not admission_id.startswith("ADM_"):
            print(colored("Invalid admission ID format.", "yellow"))
            return
        
        admission = self.db.admissions.find_one({"admission_id": admission_id})
        if not admission:
            print(colored("Admission not found.", "yellow"))
            return
        
        note_text = input(colored("Note text: ", "green")).strip()
        if not note_text:
            print(colored("Note text cannot be empty.", "yellow"))
            return
        
        # Generate new note ID
        last_note = self.db.note_events.find_one(sort=[("note_id", -1)])
        last_id = int(last_note["note_id"][5:]) if last_note else 0
        new_id = f"NOTE_{last_id + 1:03d}"
        
        note = {
            "note_id": new_id,
            "admission_id": admission_id,
            "patient_id": admission["patient_id"],
            "doctor_id": self.current_user["id"],
            "doctor_name": self.current_user["name"],
            "note_text": note_text,
            "timestamp": datetime.now()
        }
        
        try:
            self.db.note_events.insert_one(note)
            print(colored(f"\n✅ Note {new_id} added successfully!", "green"))
        except Exception as e:
            print(colored(f"❌ Error adding note: {str(e)}", "red"))

    # Nurse commands
    def cmd_medication_list(self, _):
        """Show medications to be administered"""
        if not self.verify_role("nurse"):
            return
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Get patients in the nurse's department
        patients = list(self.db.admissions.find({
            "department": self.current_user["department"],
            "admission_date": {"$lte": datetime.now()},
            "discharge_date": {"$exists": False}  # Only active admissions
        }))
        
        if not patients:
            print(colored("No active patients in your department.", "yellow"))
            return
        
        print(colored("\nMedication Administration List", "blue", attrs=["bold"]))
        print(colored("----------------------------", "blue"))
        
        for patient in patients:
            patient_info = self.db.patients.find_one({"patient_id": patient["patient_id"]})
            prescriptions = list(self.db.prescriptions.find({
                "admission_id": patient["admission_id"]
            }))
            
            if prescriptions:
                print(f"\nPatient: {patient_info['name']} (Room: {patient.get('room', 'N/A')})")
                for rx in prescriptions:
                    administered = self.db.medication_administration.find_one({
                        "patient_id": patient["patient_id"],
                        "prescription_id": rx["prescription_id"],
                        "timestamp": {"$gte": datetime.strptime(today, "%Y-%m-%d")}
                    })
                    
                    status = colored("✅ Given", "green") if administered else colored("❌ Pending", "red")
                    print(f"- {rx['drug_name']} {rx['dosage']} {rx['frequency']} {status}")

    def cmd_record_administration(self, _):
        """Record medication administration"""
        if not self.verify_role("nurse"):
            return
        
        print(colored("\nMedication Administration", "blue", attrs=["bold"]))
        print(colored("------------------------", "blue"))
        
        patient_id = input(colored("Patient ID: ", "green")).strip().upper()
        if not patient_id.startswith("PAT_"):
            print(colored("Invalid patient ID format.", "yellow"))
            return
        
        patient = self.db.patients.find_one({"patient_id": patient_id})
        if not patient:
            print(colored("Patient not found.", "yellow"))
            return
        
        admission = self.db.admissions.find_one({
            "patient_id": patient_id,
            "department": self.current_user["department"],
            "discharge_date": {"$exists": False}
        })
        if not admission:
            print(colored("Patient not currently admitted to your department.", "yellow"))
            return
        
        prescriptions = list(self.db.prescriptions.find({
            "admission_id": admission["admission_id"]
        }))
        
        if not prescriptions:
            print(colored("No prescriptions found for this patient.", "yellow"))
            return
        
        print(colored("\nAvailable Prescriptions:", "cyan"))
        for idx, rx in enumerate(prescriptions, 1):
            print(f"{idx}. {rx['drug_name']} {rx['dosage']} {rx['frequency']} (ID: {rx['prescription_id']})")
        
        selection = input(colored("\nSelect prescription to administer (number): ", "green")).strip()
        if not selection.isdigit() or not (1 <= int(selection) <= len(prescriptions)):
            print(colored("Invalid selection.", "yellow"))
            return
        
        selected_rx = prescriptions[int(selection) - 1]
        
        # Generate administration record
        last_admin = self.db.medication_administration.find_one(sort=[("event_id", -1)])
        last_id = int(last_admin["event_id"][4:]) if last_admin else 0
        new_id = f"MME_{last_id + 1:03d}"
        
        admin_record = {
            "event_id": new_id,
            "patient_id": patient_id,
            "prescription_id": selected_rx["prescription_id"],
            "medication_name": selected_rx["drug_name"],
            "event_type": "Administration",
            "dosage": selected_rx["dosage"],
            "timestamp": datetime.now(),
            "staff_id": self.current_user["id"],
            "staff_name": self.current_user["name"],
            "staff_type": "Nurse"
        }
        
        try:
            self.db.medication_administration.insert_one(admin_record)
            print(colored(f"\n✅ Medication administered successfully! Record ID: {new_id}", "green"))
        except Exception as e:
            print(colored(f"❌ Error recording administration: {str(e)}", "red"))

    def cmd_patient_vitals(self, _):
        """Record patient vitals"""
        if not self.verify_role("nurse"):
            return
            
        print(colored("\nRecord Patient Vitals", "blue", attrs=["bold"]))
        print(colored("-------------------", "blue"))
        
        patient_id = input(colored("Patient ID: ", "green")).strip().upper()
        if not patient_id.startswith("PAT_"):
            print(colored("Invalid patient ID format.", "yellow"))
            return
        
        patient = self.db.patients.find_one({"patient_id": patient_id})
        if not patient:
            print(colored("Patient not found.", "yellow"))
            return
        
        print(colored("\nEnter Vitals:", "cyan"))
        temperature = input(colored("Temperature (°C): ", "green")).strip()
        blood_pressure = input(colored("Blood Pressure (mmHg): ", "green")).strip()
        pulse = input(colored("Pulse (bpm): ", "green")).strip()
        oxygen = input(colored("Oxygen Saturation (%): ", "green")).strip()
        notes = input(colored("Additional Notes: ", "green")).strip()
        
        # Generate vitals record
        vitals = {
            "patient_id": patient_id,
            "patient_name": patient["name"],
            "temperature": float(temperature) if temperature else None,
            "blood_pressure": blood_pressure,
            "pulse": int(pulse) if pulse else None,
            "oxygen_saturation": int(oxygen) if oxygen else None,
            "notes": notes,
            "recorded_by": self.current_user["name"],
            "recorded_at": datetime.now()
        }
        
        try:
            self.db.patient_vitals.insert_one(vitals)
            print(colored("\n✅ Vitals recorded successfully!", "green"))
        except Exception as e:
            print(colored(f"❌ Error recording vitals: {str(e)}", "red"))

    def cmd_view_applications(self, _):
        """View test applications"""
        if not self.verify_role("nurse"):
            return
            
        print(colored("\nTest Applications", "blue", attrs=["bold"]))
        print(colored("----------------", "blue"))
        
        status = input(colored("Filter by status (Pending/Approved/Completed or leave blank for all): ", "green")).strip().capitalize()
        
        query = {}
        if status in ["Pending", "Approved", "Completed"]:
            query["status"] = status
        
        applications = list(self.db.applications.find(query).sort("created_at", -1).limit(10))
        
        if not applications:
            print(colored("No test applications found.", "yellow"))
            return
        
        for app in applications:
            patient = self.db.patients.find_one({"patient_id": app["patient_id"]})
            print(f"\nApplication ID: {app['application_id']}")
            print(f"Patient: {patient['name'] if patient else 'Unknown'} (ID: {app['patient_id']})")
            print(f"Test Type: {app['test_type']}")
            print(f"Status: {app['status']}")
            print(f"Created: {app['created_at'].strftime('%Y-%m-%d %H:%M') if app.get('created_at') else 'N/A'}")

    # Admin commands
    def cmd_add_staff(self, _):
        """Add new staff member"""
        if not self.verify_role("admin"):
            return
            
        print(colored("\nAdd New Staff Member", "blue", attrs=["bold"]))
        print(colored("-------------------", "blue"))
        
        staff_type = input(colored("Staff type (doctor/nurse/admin): ", "green")).strip().lower()
        if staff_type not in ["doctor", "nurse", "admin"]:
            print(colored("Invalid staff type. Must be doctor, nurse, or admin.", "yellow"))
            return
        
        name = input(colored("Full name: ", "green")).strip().title()
        department = input(colored("Department: ", "green")).strip()
        contact = input(colored("Contact number: ", "green")).strip()
        experience = input(colored("Years of experience: ", "green")).strip()
        
        # Generate staff ID
        last_staff = self.db[staff_type + "s"].find_one(sort=[(f"{staff_type}_id", -1)])
        last_id = int(last_staff[f"{staff_type}_id"][4:]) if last_staff else 0
        new_id = f"{staff_type[:3].upper()}_{last_id + 1:03d}"
        
        staff_data = {
            f"{staff_type}_id": new_id,
            "name": name,
            "department": department,
            "contact": contact,
            "years_of_experience": int(experience) if experience.isdigit() else 0
        }
        
        try:
            self.db[staff_type + "s"].insert_one(staff_data)
            print(colored(f"\n✅ {staff_type.capitalize()} added successfully! ID: {new_id}", "green"))
        except Exception as e:
            print(colored(f"❌ Error adding staff: {str(e)}", "red"))

    def cmd_generate_report(self, _):
        """Generate system report"""
        if not self.verify_role("admin"):
            return
            
        print(colored("\nGenerate System Report", "blue", attrs=["bold"]))
        print(colored("---------------------", "blue"))
        
        report_type = input(colored("Report type (patients/admissions/tests): ", "green")).strip().lower()
        
        if report_type == "patients":
            self.generate_patient_report()
        elif report_type == "admissions":
            self.generate_admission_report()
        elif report_type == "tests":
            self.generate_test_report()
        else:
            print(colored("Invalid report type. Must be patients, admissions, or tests.", "yellow"))

    def generate_patient_report(self):
        """Generate patient statistics report"""
        total_patients = self.db.patients.count_documents({})
        gender_dist = list(self.db.patients.aggregate([
            {"$group": {"_id": "$gender", "count": {"$sum": 1}}}
        ]))
        
        print(colored("\nPatient Statistics Report", "blue", attrs=["bold"]))
        print(colored("-------------------------", "blue"))
        print(f"Total Patients: {total_patients}")
        print("\nGender Distribution:")
        for g in gender_dist:
            print(f"- {g['_id'] or 'Unknown'}: {g['count']}")
        
        # Save to CSV
        filename = f"patient_report_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Patient ID", "Name", "Gender", "Date of Birth", "Contact"])
            for patient in self.db.patients.find():
                writer.writerow([
                    patient["patient_id"],
                    patient["name"],
                    patient.get("gender", ""),
                    patient["dob"].strftime('%Y-%m-%d') if patient.get("dob") else "",
                    patient.get("contact", "")
                ])
        print(colored(f"\nReport saved to {filename}", "green"))

    def generate_admission_report(self):
        """Generate admission statistics report"""
        total_admissions = self.db.admissions.count_documents({})
        dept_dist = list(self.db.admissions.aggregate([
            {"$group": {"_id": "$department", "count": {"$sum": 1}}}
        ]))
        
        print(colored("\nAdmission Statistics Report", "blue", attrs=["bold"]))
        print(colored("---------------------------", "blue"))
        print(f"Total Admissions: {total_admissions}")
        print("\nDepartment Distribution:")
        for d in dept_dist:
            print(f"- {d['_id'] or 'Unknown'}: {d['count']}")
        
        # Save to CSV
        filename = f"admission_report_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Admission ID", "Patient ID", "Department", "Doctor", "Admission Date"])
            for adm in self.db.admissions.find():
                writer.writerow([
                    adm["admission_id"],
                    adm["patient_id"],
                    adm.get("department", ""),
                    adm.get("doctor", ""),
                    adm["admission_date"].strftime('%Y-%m-%d') if adm.get("admission_date") else ""
                ])
        print(colored(f"\nReport saved to {filename}", "green"))

    def generate_test_report(self):
        """Generate test statistics report"""
        total_tests = self.db.applications.count_documents({})
        status_dist = list(self.db.applications.aggregate([
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]))
        type_dist = list(self.db.applications.aggregate([
            {"$group": {"_id": "$test_type", "count": {"$sum": 1}}}
        ]))
        
        print(colored("\nTest Statistics Report", "blue", attrs=["bold"]))
        print(colored("---------------------", "blue"))
        print(f"Total Tests: {total_tests}")
        print("\nStatus Distribution:")
        for s in status_dist:
            print(f"- {s['_id'] or 'Unknown'}: {s['count']}")
        print("\nTest Type Distribution:")
        for t in type_dist:
            print(f"- {t['_id'] or 'Unknown'}: {t['count']}")
        
        # Save to CSV
        filename = f"test_report_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Application ID", "Patient ID", "Test Type", "Status", "Created At"])
            for app in self.db.applications.find():
                writer.writerow([
                    app["application_id"],
                    app["patient_id"],
                    app["test_type"],
                    app["status"],
                    app["created_at"].strftime('%Y-%m-%d %H:%M') if app.get("created_at") else ""
                ])
        print(colored(f"\nReport saved to {filename}", "green"))

if __name__ == "__main__":
    try:
        chatbot = HospitalChatbot()
        chatbot.start()
    except Exception as e:
        print(colored(f"\nFATAL ERROR: {str(e)}", "red"))
        sys.exit(1)
