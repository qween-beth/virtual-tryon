import os
from flask import current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
from app.core.models import User, Store, TryOn
from app.core.database import db
from app.utils.tryon import process_tryon
from app.utils.helpers import save_file, normalize_static_path
import asyncio


def get_customer_dashboard_data(user_id):
    """
    Retrieves data for the customer's dashboard.
    
    Args:
        user_id (int): ID of the user.
        
    Returns:
        dict: Dashboard data including user info and credits.
        
    Raises:
        ValueError: If user not found.
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found.")
    
    dashboard_data = {
        'user_email': user.email,
        'user_id': user_id,
        'store_name': None,
        'store_id': None,
        'remaining_credits': user.credit_balance or 0  # Default to user's credit balance
    }

    if user.store_id:
        # User is associated with a store
        store = Store.query.get(user.store_id)
        if store:
            dashboard_data['store_name'] = store.name
            dashboard_data['store_id'] = store.id
            dashboard_data['remaining_credits'] = store.credit_balance or 0  # Use store's credit balance

    return dashboard_data




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
            # Use asyncio.create_task instead of awaiting directly to prevent event loop issues
            try:
                result = await process_tryon(model_path, garment_path, category, output_folder=full_tryon_results_path)
                current_app.logger.debug(f"Raw result from process_tryon: {result}")
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    current_app.logger.error("Event loop was closed. Creating new event loop.")
                    # Get a new event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    # Try again with the new loop
                    result = await process_tryon(model_path, garment_path, category, output_folder=full_tryon_results_path)
                    current_app.logger.debug(f"Result from new event loop: {result}")
                else:
                    # Re-raise other runtime errors
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
    

def get_customer_tryons(store_id, page, per_page):
    """
    Get paginated TryOn history for a store.
    
    Args:
        store_id (int): ID of the store
        page (int): Current page number
        per_page (int): Items per page
        
    Returns:
        dict: Contains 'items' (list of TryOns) and 'total_pages' (int)
    """
    try:
        query = TryOn.query.filter_by(store_id=store_id).order_by(TryOn.created_at.desc())
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'items': paginated.items,
            'total_pages': paginated.pages
        }
    except Exception as e:
        current_app.logger.error(f"Error fetching TryOn history: {str(e)}")
        raise ValueError(f"Error fetching TryOn history: {str(e)}")