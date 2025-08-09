import csv
from pymongo import MongoClient, errors
from datetime import datetime
import sys
from typing import Dict, Any, List, Optional

def get_mongodb_connection() -> MongoClient:
    """Establish connection to MongoDB with error handling"""
    try:
        client = MongoClient(
            "mongodb://localhost:27017/",
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=30000,
            connectTimeoutMS=10000
        )
        # Test the connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB")
        return client
    except errors.ServerSelectionTimeoutError as err:
        print("❌ Could not connect to MongoDB:", err)
        print("\nTroubleshooting tips:")
        print("1. Make sure MongoDB is running (try 'mongod' in command prompt)")
        print("2. Check if port 27017 is not blocked by firewall")
        print("3. Verify MongoDB service is started (services.msc)")
        sys.exit(1)

def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> Optional[datetime]:
    """Parse date string to datetime object"""
    try:
        return datetime.strptime(date_str, fmt) if date_str else None
    except (ValueError, TypeError):
        return None

def parse_csv_row(row: Dict[str, Any], date_fields: List[str] = None, 
                 datetime_fields: List[str] = None) -> Dict[str, Any]:
    """Convert date/datetime fields in a CSV row"""
    if date_fields:
        for field in date_fields:
            if field in row:
                row[field] = parse_date(row[field])
    
    if datetime_fields:
        for field in datetime_fields:
            if field in row:
                row[field] = parse_date(row[field], "%Y-%m-%d %H:%M:%S")
    
    # Convert empty strings to None and strip whitespace
    for k, v in row.items():
        if isinstance(v, str):
            row[k] = v.strip() if v.strip() else None
    
    return row

def import_csv_to_mongodb(collection_name: str, csv_file: str, 
                         date_fields: List[str] = None, 
                         datetime_fields: List[str] = None,
                         index_fields: List[str] = None) -> None:
    """Import CSV data into MongoDB collection"""
    try:
        client = get_mongodb_connection()
        db = client["hospital_a_db"]
        collection = db[collection_name]
        
        # Clear existing data only if collection exists
        if collection_name in db.list_collection_names():
            collection.drop()
            print(f"♻️ Cleared existing {collection_name} collection")
        
        inserted_count = 0
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    # Process the row
                    processed_row = parse_csv_row(row, date_fields, datetime_fields)
                    
                    # Insert into MongoDB
                    collection.insert_one(processed_row)
                    inserted_count += 1
                except Exception as e:
                    print(f"⚠️ Error inserting document: {e}")
                    continue
        
        print(f"✅ Imported {inserted_count} documents into {collection_name}")
        
        # Create indexes if specified
        if index_fields:
            for field in index_fields:
                try:
                    collection.create_index(field)
                    print(f"  ➡ Created index on {field}")
                except Exception as e:
                    print(f"⚠️ Error creating index on {field}: {e}")
        
    except FileNotFoundError:
        print(f"❌ File not found: {csv_file}")
    except Exception as e:
        print(f"❌ Error importing {collection_name}: {e}")
    finally:
        if 'client' in locals():
            client.close()

def main():
    print("\n🏥 Hospital Management System - MongoDB Data Importer\n")
    
    # Define import configurations for all CSV files
    import_configs = [
        # Patients data
        {
            "collection": "patients",
            "file": "patients.csv",
            "date_fields": ["dob"],
            "index_fields": ["patient_id"]
        },
        # Admissions data
        {
            "collection": "admissions",
            "file": "admissions.csv",
            "date_fields": ["admission_date"],
            "index_fields": ["admission_id", "patient_id", "doctor"]
        },
        # Diagnoses data
        {
            "collection": "diagnoses",
            "file": "diagnoses_icd.csv",
            "date_fields": ["diagnosis_date"],
            "index_fields": ["diagnosis_id", "admission_id", "icd_code"]
        },
        # Doctors data
        {
            "collection": "doctors",
            "file": "doctors.csv",
            "index_fields": ["doctor_id", "department"]
        },
        # Nurses data
        {
            "collection": "nurses",
            "file": "nurses.csv",
            "index_fields": ["nurse_id", "department"]
        },
        # Lab items data
        {
            "collection": "lab_items",
            "file": "d_labitems.csv",
            "index_fields": ["lab_item_id"]
        },
        # Lab events data
        {
            "collection": "lab_events",
            "file": "labevents.csv",
            "datetime_fields": ["timestamp"],
            "index_fields": ["event_id", "admission_id", "lab_item_id"]
        },
        # Test applications data
        {
            "collection": "applications",
            "file": "applications.csv",
            "datetime_fields": ["created_at"],
            "index_fields": ["application_id", "patient_id", "test_type"]
        },
        # Prescriptions data
        {
            "collection": "prescriptions",
            "file": "prescriptions.csv",
            "index_fields": ["prescription_id", "admission_id", "drug_name"]
        },
        # Medication administration data
        {
            "collection": "medication_administration",
            "file": "mme.csv",
            "datetime_fields": ["timestamp"],
            "index_fields": ["event_id", "patient_id", "medication_name"]
        },
        # Note events data
        {
            "collection": "note_events",
            "file": "noteevents.csv",
            "datetime_fields": ["timestamp"],
            "index_fields": ["note_id", "admission_id", "doctor_id"]
        }
    ]
    
    # Execute all imports
    for config in import_configs:
        print(f"\n📁 Importing {config['collection']}...")
        import_csv_to_mongodb(
            collection_name=config["collection"],
            csv_file=config["file"],
            date_fields=config.get("date_fields"),
            datetime_fields=config.get("datetime_fields"),
            index_fields=config.get("index_fields")
        )
    
    print("\n✨ All data imported successfully!")

if __name__ == "__main__":
    main()
