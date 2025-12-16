# Google Cloud Storage setup for persistent user data
import os
import json
from datetime import datetime

# Auto-detect if running on GCP
def _is_running_on_gcp():
    """Detect if the application is running on Google Cloud Platform."""
    # Check for Cloud Run environment variable
    if os.environ.get('K_SERVICE'):
        return True
    # Check for explicit GCS flag
    if os.environ.get('USE_GCS', '').lower() == 'true':
        return True
    # Check for GCP metadata server (works for Cloud Run, App Engine, GCE)
    try:
        import socket
        socket.setdefaulttimeout(0.1)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(('metadata.google.internal', 80))
        return True
    except:
        pass
    return False

# Initialize GCS client only if running on GCP
USE_GCS = _is_running_on_gcp()
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', '')

if USE_GCS:
    print("🌩️  Detected GCP environment - using Cloud Storage")
    try:
        from google.cloud import storage
        
        # Check for custom credentials file
        credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path and os.path.exists(credentials_path):
            print(f"📝 Using credentials from: {credentials_path}")
            storage_client = storage.Client.from_service_account_json(credentials_path)
        else:
            # Use default credentials (application default or Cloud Run service account)
            storage_client = storage.Client()
        
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize GCS: {e}")
        print("📁 Falling back to local storage")
        USE_GCS = False
else:
    print("💻 Running locally - using local file storage")

def get_user_filepath(email):
    """Generate filepath for user data."""
    username = email.split('@')[0].replace('.', '_')
    return f"users/{username}_wrapped_2025.json"

def save_to_storage(email, data):
    """Save user data to GCS or local filesystem."""
    filepath = get_user_filepath(email)
    
    wrapped_data = {
        'generated_at': datetime.now().isoformat(),
        'email': email,
        'data': data
    }
    
    if USE_GCS:
        try:
            blob = bucket.blob(filepath)
            blob.upload_from_string(
                json.dumps(wrapped_data, indent=2),
                content_type='application/json'
            )
            print(f"✅ Saved to GCS: {filepath}")
            return True
        except Exception as e:
            print(f"❌ GCS save error: {e}")
            return False
    else:
        # Fallback to local storage
        os.makedirs('users', exist_ok=True)
        try:
            with open(filepath, 'w') as f:
                json.dump(wrapped_data, f, indent=2)
            print(f"✅ Saved locally: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Local save error: {e}")
            return False

def load_from_storage(email):
    """Load user data from GCS or local filesystem."""
    filepath = get_user_filepath(email)
    
    if USE_GCS:
        try:
            blob = bucket.blob(filepath)
            if blob.exists():
                data = json.loads(blob.download_as_text())
                print(f"✅ Loaded from GCS: {filepath}")
                return data.get('data')
        except Exception as e:
            print(f"❌ GCS load error: {e}")
            return None
    else:
        # Fallback to local storage
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                print(f"✅ Loaded locally: {filepath}")
                return data.get('data')
        except Exception as e:
            print(f"❌ Local load error: {e}")
            return None
    
    return None

def delete_from_storage(email):
    """Delete user data from GCS or local filesystem."""
    filepath = get_user_filepath(email)
    
    if USE_GCS:
        try:
            blob = bucket.blob(filepath)
            if blob.exists():
                blob.delete()
                print(f"✅ Deleted from GCS: {filepath}")
                return True
        except Exception as e:
            print(f"❌ GCS delete error: {e}")
            return False
    else:
        # Fallback to local storage
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"✅ Deleted locally: {filepath}")
                return True
        except Exception as e:
            print(f"❌ Local delete error: {e}")
            return False
    
    return False

def get_insights_filepath(email):
    """Generate filepath for insights data."""
    username = email.split('@')[0].replace('.', '_')
    return f"insights/{username}_insights_2025.json"

def save_insights_to_storage(email, data):
    """Save AI insights to GCS or local filesystem."""
    filepath = get_insights_filepath(email)
    
    if USE_GCS:
        try:
            blob = bucket.blob(filepath)
            blob.upload_from_string(
                json.dumps(data, indent=2),
                content_type='application/json'
            )
            print(f"✅ Saved insights to GCS: {filepath}")
            return True
        except Exception as e:
            print(f"❌ GCS insights save error: {e}")
            return False
    else:
        # Fallback to local storage
        os.makedirs('insights', exist_ok=True)
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"✅ Saved insights locally: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Local insights save error: {e}")
            return False

def load_insights_from_storage(email):
    """Load AI insights from GCS or local filesystem."""
    filepath = get_insights_filepath(email)
    
    if USE_GCS:
        try:
            blob = bucket.blob(filepath)
            if blob.exists():
                data = json.loads(blob.download_as_text())
                print(f"✅ Loaded insights from GCS: {filepath}")
                return data
        except Exception as e:
            print(f"❌ GCS insights load error: {e}")
            return None
    else:
        # Fallback to local storage
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                print(f"✅ Loaded insights locally: {filepath}")
                return data
        except Exception as e:
            print(f"❌ Local insights load error: {e}")
            return None
    
    return None

def delete_insights_from_storage(email):
    """Delete AI insights from GCS or local filesystem."""
    filepath = get_insights_filepath(email)
    
    if USE_GCS:
        try:
            blob = bucket.blob(filepath)
            if blob.exists():
                blob.delete()
                print(f"✅ Deleted insights from GCS: {filepath}")
                return True
        except Exception as e:
            print(f"❌ GCS insights delete error: {e}")
            return False
    else:
        # Fallback to local storage
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"✅ Deleted insights locally: {filepath}")
                return True
        except Exception as e:
            print(f"❌ Local insights delete error: {e}")
            return False
    
    return False
