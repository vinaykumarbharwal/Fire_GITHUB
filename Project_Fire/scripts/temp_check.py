
import firebase_admin
from firebase_admin import credentials, firestore

def check_images():
    try:
        cred = credentials.Certificate('c:/Users/cuhp/Fire_GITHUB/Project_Fire/backend/firebase-credentials.json')
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        
        detections = db.collection('detections').order_by('timestamp', direction='DESCENDING').limit(5).stream()
        
        print("\n--- Recent Detections ---")
        for doc in detections:
            data = doc.to_dict()
            print(f"ID: {data.get('id')}")
            print(f"Image URL: {data.get('image_url')}")
            print(f"Timestamp: {data.get('timestamp')}")
            print("-" * 30)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_images()
