import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import base64
import binascii

cred_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "firebase_credentials.json"))

def _parse_env_credentials(firebase_env: str):
    # Support direct path to JSON file
    if os.path.exists(firebase_env):
        return credentials.Certificate(firebase_env)

    # Support raw JSON and escaped JSON strings
    parse_candidates = [firebase_env]
    if "\\n" in firebase_env:
        parse_candidates.append(firebase_env.replace("\\n", "\n"))

    for candidate in parse_candidates:
        try:
            return credentials.Certificate(json.loads(candidate))
        except (TypeError, json.JSONDecodeError):
            continue

    # Support base64-encoded JSON payloads
    try:
        decoded = base64.b64decode(firebase_env).decode("utf-8")
        return credentials.Certificate(json.loads(decoded))
    except (binascii.Error, UnicodeDecodeError, TypeError, json.JSONDecodeError):
        pass

    raise ValueError("FIREBASE_CREDENTIALS is set but not a valid JSON/path/base64-JSON credential.")


def _get_or_init_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        firebase_env = os.environ.get("FIREBASE_CREDENTIALS")
        if firebase_env:
            cred = _parse_env_credentials(firebase_env)
        elif os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            raise FileNotFoundError(f"Firebase credentials not found at {cred_path} and FIREBASE_CREDENTIALS env var missing.")

        try:
            return firebase_admin.initialize_app(cred)
        except ValueError:
            # Handles concurrent first-time initialization races
            return firebase_admin.get_app()


def get_db():
    app = _get_or_init_firebase_app()
    db = firestore.client(app=app)
    yield db

# Dummy Base to avoid instant import errors while refactoring
Base = object()
