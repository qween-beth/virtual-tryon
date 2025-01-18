from flask import Flask, render_template, request, url_for, send_from_directory, current_app
import asyncio
import fal_client
import os
import requests
from base64 import b64encode
from dotenv import load_dotenv
import jsonify
from werkzeug.utils import secure_filename
from enum import Enum
from typing import Optional


load_dotenv()

FAL_KEY = os.getenv('FAL_KEY')
if not FAL_KEY:
    raise ValueError("FAL_KEY environment variable not set. Please configure it in your .env file.")

fal_client.api_key = FAL_KEY



UPLOAD_FOLDER = 'static/uploads'
TRYON_FOLDER = 'static/tryon-images'
for folder in [UPLOAD_FOLDER, TRYON_FOLDER]:
    os.makedirs(folder, exist_ok=True)

def encode_image_to_base64(file_path):
    with open(file_path, 'rb') as image_file:
        return f"data:image/{file_path.split('.')[-1]};base64," + b64encode(image_file.read()).decode('utf-8')

def download_and_save_image(url, filename):
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        file_path = os.path.join(TRYON_FOLDER, filename)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return f"tryon-images/{filename}"
    except Exception as e:
        print(f"Error downloading image: {str(e)}")
        return None

class TryOnCategory(Enum):
    TOPS = "tops"
    BOTTOMS = "bottoms"
    ONE_PIECES = "one-pieces"

def normalize_category(category: str) -> Optional[str]:
    """
    Normalizes the category input to match FAL API expectations.
    
    Args:
        category: Input category string
        
    Returns:
        Normalized category string or None if invalid
    """
    category_map = {
        'top': 'tops',
        'shirt': 'tops',
        'tshirt': 'tops',
        't-shirt': 'tops',
        'bottom': 'bottoms',
        'pants': 'bottoms',
        'skirt': 'bottoms',
        'dress': 'one-pieces',
        'jumpsuit': 'one-pieces',
        'one-piece': 'one-pieces',
        'onepiece': 'one-pieces'
    }
    
    normalized = category_map.get(category.lower())
    return normalized if normalized in [c.value for c in TryOnCategory] else None

async def process_tryon(model_image_path, garment_image_path, category):
    """
    Process the TryOn request with category validation.
    """
    try:
        # Normalize the category
        normalized_category = normalize_category(category)
        if not normalized_category:
            raise ValueError(f"Invalid category: {category}. Allowed categories: {[c.value for c in TryOnCategory]}")

        model_image_base64 = encode_image_to_base64(model_image_path)
        garment_image_base64 = encode_image_to_base64(garment_image_path)

        def on_queue_update(update):
            if isinstance(update, fal_client.InProgress):
                for log in update.logs:
                    print(f"Progress: {log['message']}")

        result = await fal_client.subscribe_async(
            "fashn/tryon",
            arguments={
                "model_image": model_image_base64,
                "garment_image": garment_image_base64,
                "category": normalized_category,  # Use normalized category
                "garment_photo_type": "auto",
                "nsfw_filter": True,
                "guidance_scale": 2,
                "timesteps": 50,
                "seed": 42,
                "num_samples": 1
            },
            with_logs=True,
            on_queue_update=on_queue_update
        )

        if result and 'images' in result and len(result['images']) > 0:
            image_url = result['images'][0]['url']
            timestamp = int(asyncio.get_event_loop().time())
            filename = f"tryon_result_{timestamp}.png"
            saved_path = download_and_save_image(image_url, filename)
            return saved_path
        return None
    
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        return None