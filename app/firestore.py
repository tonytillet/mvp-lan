import os
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path

def initialize_firebase():
    """Initialize Firebase app with proper error handling"""
    try:
        # Check if Firebase is already initialized
        if len(firebase_admin._apps) > 0:
            return firestore.client()
        
        # Get service account key path from environment or use default
        key_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY', 'serviceAccountKey.json')
        
        # Check if file exists
        if not Path(key_path).exists():
            raise FileNotFoundError(f"Service account key file not found: {key_path}")
        
        # Initialize Firebase
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        
        return firestore.client()
        
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        raise

# Initialize Firebase and get database client
db = initialize_firebase()
