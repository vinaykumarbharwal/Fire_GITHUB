
import os
import asyncio
import numpy as np
from PIL import Image
import io
from api.services.onnx_inference import OnnxInferenceService

async def test_inference():
    # Path to the model
    base_dir = 'c:/Users/cuhp/Fire_GITHUB/Project_Fire/backend'
    model_path = os.path.join(base_dir, "api", "assets", "models", "fire_model.onnx")
    
    print(f"Checking model at: {model_path}")
    if not os.path.exists(model_path):
        print("❌ Model file not found!")
        return

    service = OnnxInferenceService(model_path)
    
    if not service.session:
        print("❌ Service failed to load model session.")
        return

    print("✅ Model session loaded successfully!")
    print(f"Input Name: {service.input_name}")
    print(f"Input Shape: {service.input_shape}")
    
    # Create a dummy image (RGB 640x640)
    dummy_image = Image.new('RGB', (640, 640), color=(255, 0, 0))
    img_byte_arr = io.BytesIO()
    dummy_image.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    
    print("Running inference...")
    try:
        results = await service.run_inference(img_bytes)
        print(f"Success! Results: {results}")
    except Exception as e:
        print(f"❌ Inference failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_inference())
