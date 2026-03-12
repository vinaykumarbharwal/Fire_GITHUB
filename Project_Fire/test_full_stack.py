import requests
import os

# Configuration
API_URL = "http://localhost:8000/api/detections/report"
TEST_IMAGE_URL = "https://raw.githubusercontent.com/vinaykumarbharwal/Fire_GITHUB/main/Project_Fire/mobile_app/flutter_app/assets/images/placeholder_fire.jpg"

def test_full_stack():
    print("🚀 Starting End-to-End Test...")
    
    # 1. Download a test image if not present
    temp_image = "test_fire.jpg"
    if not os.path.exists(temp_image):
        print("📥 Downloading test image...")
        img_data = requests.get(TEST_IMAGE_URL).content
        with open(temp_image, 'wb') as f:
            f.write(img_data)

    # 2. Simulate a fire report at a specific location (e.g., Near New Delhi)
    data = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "confidence": 0.95,
        "reported_by": "System Test Bot"
    }
    
    files = {
        "image": ("test_fire.jpg", open(temp_image, "rb"), "image/jpeg")
    }

    try:
        print(f"📡 Sending fire report to {API_URL}...")
        response = requests.post(API_URL, data=data, files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print(f"📄 Detection ID: {result.get('detection_id')}")
            print(f"🔥 Severity: {result.get('severity')}")
            print("\n👉 Now check your Dashboard at http://localhost:3000")
            print("You should see a new 'CRITICAL' alert in the New Delhi area.")
        else:
            print(f"❌ FAILED: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"💥 Error: {e}")
    finally:
        files["image"][1].close()

if __name__ == "__main__":
    test_full_stack()
