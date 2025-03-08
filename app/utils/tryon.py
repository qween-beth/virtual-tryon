#tryon.py
from flask import Flask, render_template, request, url_for, send_from_directory, current_app
import asyncio
import fal_client
from app.utils.helpers import normalize_category
from app.utils.constants import TryOnCategory
import os
import requests
from base64 import b64encode
from dotenv import load_dotenv
import jsonify
from werkzeug.utils import secure_filename
from enum import Enum
from typing import Optional
import time


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



async def process_customer_tryon(model_image, garment_image, category):
    """
    Process a new TryOn request.
    
    Args:
        model_image: FileStorage object for model image
        garment_image: FileStorage object for garment image
        category: String indicating garment category
        
    Returns:
        str: Path to output image relative to static folder, or None if failed
    """
    try:
        current_app.logger.debug(f"Starting TryOn processing for category: {category}")
        
        model_filename = secure_filename(f"model_{category}_{model_image.filename}")
        garment_filename = secure_filename(f"garment_{category}_{garment_image.filename}")

        # Use the UPLOAD_FOLDER path directly
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
        model_path = os.path.join(upload_folder, model_filename)
        garment_path = os.path.join(upload_folder, garment_filename)

        # Ensure upload directory exists
        os.makedirs(upload_folder, exist_ok=True)
        current_app.logger.debug(f"Saving files to: {upload_folder}")

        # Save uploaded files
        save_file(model_image, upload_folder, model_filename)
        save_file(garment_image, upload_folder, garment_filename)

        try:
            # Create a dedicated folder for try-on results within static folder
            tryon_results_folder = 'tryon-images'
            full_tryon_results_path = os.path.join(current_app.static_folder, tryon_results_folder)
            os.makedirs(full_tryon_results_path, exist_ok=True)
            current_app.logger.debug(f"TryOn results folder: {full_tryon_results_path}")

            # Process the try-on request with specified output folder
            try:
                # Use a task to better manage the event loop
                result = await process_tryon(model_path, garment_path, category, output_folder=full_tryon_results_path)
                current_app.logger.debug(f"Raw result from process_tryon: {result}")
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    current_app.logger.error("Event loop was closed. Creating new event loop.")
                    # Get new event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Try again with the new loop
                    result = await process_tryon(model_path, garment_path, category, output_folder=full_tryon_results_path)
                    current_app.logger.debug(f"Result from new event loop: {result}")
                else:
                    raise
            
            if not result:
                current_app.logger.error("TryOn processing returned None")
                raise ValueError("TryOn processing failed")
                
            # Make sure result is a relative path to the static folder
            result = normalize_static_path(result)
            current_app.logger.debug(f"Normalized result path: {result}")
                    
            # Verify the file exists
            result_full_path = os.path.join(current_app.static_folder, result)
            current_app.logger.debug(f"Checking file existence at: {result_full_path}")
            
            if not os.path.exists(result_full_path):
                current_app.logger.error(f"Result file does not exist: {result_full_path}")
                return None
                
            if not os.access(result_full_path, os.R_OK):
                current_app.logger.error(f"Result file is not readable: {result_full_path}")
                return None

            # Create TryOn record
            tryon = TryOn(
                user_id=current_user.id,
                store_id=current_user.store_id,
                category=category,
                model_image=normalize_static_path(model_path),
                garment_image=normalize_static_path(garment_path),
                result_image=result,
                credits_source='user' if current_user.credit_balance >= 1 else 'store'
            )
            db.session.add(tryon)
            db.session.commit()
            current_app.logger.debug(f"TryOn record created with ID: {tryon.id}")

            return result

        finally:
            # Cleanup temporary files - Commented out to avoid issues with file access
            # for path in [model_path, garment_path]:
            #     try:
            #         if os.path.exists(path):
            #             os.remove(path)
            #     except Exception as e:
            #         current_app.logger.warning(f"Failed to cleanup {path}: {str(e)}")
            pass

    except Exception as e:
        current_app.logger.error(f"TryOn processing error: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return None

async def process_tryon(model_image_path, garment_image_path, category, output_folder=None):
    """
    Process the TryOn request with category validation.
    
    Args:
        model_image_path: Path to model image file
        garment_image_path: Path to garment image file
        category: Category of garment
        output_folder: Optional folder to save result image (defaults to static/tryon-images)
        
    Returns:
        str: Relative path to the result image within static folder
    """
    try:
        # Set default output folder if not provided
        if not output_folder:
            output_folder = os.path.join(current_app.static_folder, 'tryon-images')
        
        # Ensure output directory exists
        os.makedirs(output_folder, exist_ok=True)
            
        # Normalize the category using the shared function
        normalized_category = normalize_category(category)
        if not normalized_category:
            raise ValueError(f"Invalid category: {category}. Allowed categories: {[c.value for c in TryOnCategory]}")
        
        # Map our internal categories to FAL API categories if needed
        fal_category_map = {
            TryOnCategory.TOPS.value: "tops",
            TryOnCategory.BOTTOMS.value: "bottoms",
            TryOnCategory.DRESSES.value: "one-pieces",
            TryOnCategory.OUTERWEAR.value: "tops"  # FAL might not have outerwear, so map to tops
        }
        
        fal_category = fal_category_map.get(normalized_category)
        model_image_base64 = encode_image_to_base64(model_image_path)
        garment_image_base64 = encode_image_to_base64(garment_image_path)
        
        def on_queue_update(update):
            if isinstance(update, fal_client.InProgress):
                for log in update.logs:
                    current_app.logger.debug(f"TryOn Progress: {log['message']}")
        
        # Handle event loop issues
        try:
            result = await fal_client.subscribe_async(
                "fashn/tryon",
                arguments={
                    "model_image": model_image_base64,
                    "garment_image": garment_image_base64,
                    "category": fal_category,  # Use mapped category for FAL API
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
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                # Create a new event loop and try again
                current_app.logger.warning("Event loop closed during FAL API call, creating new loop")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Retry with new loop
                result = await fal_client.subscribe_async(
                    "fashn/tryon",
                    arguments={
                        "model_image": model_image_base64,
                        "garment_image": garment_image_base64,
                        "category": fal_category,
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
            else:
                raise
        
        if result and 'images' in result and len(result['images']) > 0:
            image_url = result['images'][0]['url']
            
            # Generate unique filename with timestamp
            import uuid
            timestamp = int(time.time())
            random_id = uuid.uuid4().hex[:8]
            filename = f"tryon_result_{timestamp}_{random_id}.png"
            
            # Full path where image will be saved
            full_save_path = os.path.join(output_folder, filename)
            
            # Download and save the image
            response = requests.get(image_url)
            response.raise_for_status()
            
            with open(full_save_path, 'wb') as f:
                f.write(response.content)
            
            # Verify file was saved
            if not os.path.exists(full_save_path):
                raise ValueError(f"Failed to save image to {full_save_path}")
                
            current_app.logger.debug(f"TryOn result saved to: {full_save_path}")
            
            # Return path relative to static folder
            static_folder = current_app.static_folder
            if full_save_path.startswith(static_folder):
                relative_path = os.path.relpath(full_save_path, static_folder)
            else:
                relative_path = os.path.join('tryon-images', filename)
                
            current_app.logger.debug(f"Relative path for static URL: {relative_path}")
            return relative_path
            
        return None
        
    except Exception as e:
        current_app.logger.error(f"Error in process_tryon: {str(e)}")
        return None