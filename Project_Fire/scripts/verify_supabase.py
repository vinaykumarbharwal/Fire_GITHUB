
import os
import asyncio
from api.services.supabase_service import SupabaseService
from dotenv import load_dotenv

# Load env from the backend directory
load_dotenv('c:/Users/cuhp/Fire_GITHUB/Project_Fire/backend/.env')

async def test_upload():
    service = SupabaseService()
    # Manual override to ensure credentials are used if script runs from different CWD
    service.url = os.getenv("SUPABASE_URL")
    service.key = os.getenv("SUPABASE_ANON_KEY")
    
    # Use a dummy file for testing
    test_file = 'c:/Users/cuhp/Fire_GITHUB/Project_Fire/frontend_website/assets/images/placeholder.jpg'
    dest_path = f'test/verify_{os.urandom(4).hex()}.jpg'
    
    print(f"URL: {service.url}")
    
    try:
        url = await service.upload_image(test_file, dest_path)
        print(f"✅ Upload Success! URL: {url}")
    except Exception as e:
        print(f"❌ Upload Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_upload())
