import os
from app.utils.tryon import process_tryon
from app.utils.helpers import save_file
from app.core.database import db
from app.core.models import User, Store, TryOn
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_customer_dashboard_data(user_id):
    """
    Retrieves data for the customer's dashboard, including their TryOn history and remaining credits.

    Args:
        user_id (int): ID of the user.

    Returns:
        dict: A dictionary containing dashboard data.

    Raises:
        ValueError: If the user or associated store is not found.
    """
    # Fetch user
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found.")

    # Fetch store
    store = Store.query.get(user.store_id)
    if not store:
        raise ValueError(f"No store associated with user ID {user_id}.")

    # Prepare data
    data = {
        'user_email': user.email,
        'store_name': store.name,
        'remaining_credits': store.credit_balance or 0,  # Default to 0 if None
        'user_id': user_id,
        'store_id': store.id
    }

    return data

async def process_customer_tryon(model_image, garment_image, category):
    """
    Processes the TryOn request by saving the input images and invoking the TryOn utility.
    
    Args:
        model_image: FileStorage object containing the model image
        garment_image: FileStorage object containing the garment image
        category: String indicating the garment category
        
    Returns:
        str: Path to the output image relative to static folder, or None if processing failed
    """
    try:
        # Secure the filenames
        model_filename = secure_filename(f"model_{category}_{model_image.filename}")
        garment_filename = secure_filename(f"garment_{category}_{garment_image.filename}")

        # Create full paths
        model_image_path = os.path.join(UPLOAD_FOLDER, model_filename)
        garment_image_path = os.path.join(UPLOAD_FOLDER, garment_filename)

        # Save the uploaded images
        save_file(model_image, UPLOAD_FOLDER, model_filename)
        save_file(garment_image, UPLOAD_FOLDER, garment_filename)

        # Call the TryOn processing utility (now async)
        output_filename = await process_tryon(model_image_path, garment_image_path, category)
        
        # Clean up temporary files
        try:
            os.remove(model_image_path)
            os.remove(garment_image_path)
        except Exception as e:
            print(f"Warning: Could not clean up temporary files: {str(e)}")
            
        return output_filename
    except Exception as e:
        print(f"Error during TryOn service: {str(e)}")
        return None

    
def get_customer_tryons(store_id, page, per_page):
    """
    Retrieves paginated TryOn history for a given store.

    Args:
        store_id (int): ID of the store.
        page (int): Current page number.
        per_page (int): Number of items per page.

    Returns:
        dict: Contains 'items' (list of TryOn objects) and 'total_pages' (int).
    """
    try:
        # Query TryOn objects associated with the store, ordered by creation date
        query = TryOn.query.filter_by(store_id=store_id).order_by(TryOn.created_at.desc())
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            'items': paginated.items,
            'total_pages': paginated.pages
        }
    except Exception as e:
        raise ValueError(f"Error fetching TryOn history: {str(e)}")
