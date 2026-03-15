import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

cred_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "firebase_credentials.json"))

def get_db():
    try:
        app = firebase_admin.get_app()
    except ValueError:
        firebase_env = os.environ.get("FIREBASE_CREDENTIALS")
        if firebase_env:
            try:
                cred_dict = json.loads(firebase_env)
                cred = credentials.Certificate(cred_dict)
            except Exception as e:
                raise ValueError(f"Failed to parse FIREBASE_CREDENTIALS from env: {e}")
        elif os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            raise FileNotFoundError(f"Firebase credentials not found at {cred_path} and FIREBASE_CREDENTIALS env var missing.")
            
        app = firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    yield db

# Dummy Base to avoid instant import errors while refactoring
Base = object()
