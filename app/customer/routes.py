from flask import (
    render_template, request, jsonify, send_file, 
    current_app, url_for, flash, redirect, Blueprint
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from . import customer_bp
from .services import (
    get_customer_dashboard_data, 
    process_customer_tryon, 
    get_customer_tryons,
    normalize_static_path
)
from app.core.models import Store, TryOn
from app.core.database import db
from app.utils.helpers import normalize_category
import os

# Error handlers
@customer_bp.errorhandler(400)
@customer_bp.errorhandler(404)
@customer_bp.errorhandler(500)
def handle_api_error(error):
    """Return JSON instead of HTML for API errors."""
    if request.path.startswith('/customer/'):
        return jsonify({
            'error': str(error),
            'description': error.description if hasattr(error, 'description') else 'Unknown error'
        }), error.code
    return error  # For non-API routes, return the normal error response

# Add request/response logging for debugging
@customer_bp.before_request
def log_request_info():
    if current_app.debug:
        current_app.logger.debug('Request Headers: %s', request.headers)
        current_app.logger.debug('Request Path: %s', request.path)
        current_app.logger.debug('Request Method: %s', request.method)
        if request.is_json:
            current_app.logger.debug('Request JSON: %s', request.json)

@customer_bp.after_request
def log_response_info(response):
    if current_app.debug and response.content_type == 'application/json':
        current_app.logger.debug('Response Status: %s', response.status)
        current_app.logger.debug('Response Content-Type: %s', response.content_type)
    return response

@customer_bp.route('/tryon', methods=['GET']) 
@login_required 
def tryon_form():
    """
    Render the TryOn form page.
    This handles the initial page load (GET request).
    """
    # Get store name if the user is affiliated with a store
    store_name = None
    if current_user.store_id:
        store = Store.query.get(current_user.store_id)
        store_name = store.name if store else None
    
    return render_template(
        'customer/tryon.html', 
        remaining_credits=current_user.credit_balance,
        store_name=store_name,
        model_image_url=None,
        garment_image_url=None,
        output_image=None
    )

@customer_bp.route('/tryon', methods=['POST']) 
@login_required 
async def tryon():
    """
    Handle TryOn API requests and return JSON response.
    This handles form submissions (POST requests).
    """
    try:
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Log for debugging
        current_app.logger.debug(f"AJAX request: {is_ajax}")
        
        # Validate required files
        if 'model_image' not in request.files:
            if is_ajax:
                return jsonify({'error': 'Missing model image file'}), 400
            flash('Missing model image file', 'error')
            return redirect(url_for('customer.tryon_form'))
                 
        if 'garment_image' not in request.files:
            if is_ajax:
                return jsonify({'error': 'Missing garment image file'}), 400
            flash('Missing garment image file', 'error')
            return redirect(url_for('customer.tryon_form'))
                 
        if 'category' not in request.form:
            if is_ajax:
                return jsonify({'error': 'Missing category field'}), 400
            flash('Missing category field', 'error')
            return redirect(url_for('customer.tryon_form'))
        
        model_image = request.files['model_image']
        garment_image = request.files['garment_image']
        category = request.form['category']
             
        # Log received data for debugging
        current_app.logger.debug(f"Received category: '{category}'")
        current_app.logger.debug(f"Received files: model={model_image.filename}, garment={garment_image.filename}")
        
        # Validate file types
        allowed_extensions = {'png', 'jpg', 'jpeg'}
        if not all(f.filename.lower().endswith(tuple(f'.{ext}' for ext in allowed_extensions))
                   for f in [model_image, garment_image]):
            if is_ajax:
                return jsonify({'error': 'Only image files (PNG, JPG, JPEG) are allowed'}), 400
            flash('Only image files (PNG, JPG, JPEG) are allowed', 'error')
            return redirect(url_for('customer.tryon_form'))
        
        # Validate category
        normalized_category = normalize_category(category)
        if not normalized_category:
            from app.utils.constants import TryOnCategory
            valid_categories = [c.value for c in TryOnCategory]
            error_msg = f'Invalid category: "{category}". Allowed categories: {", ".join(valid_categories)}'
            if is_ajax:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('customer.tryon_form'))
        
        # Check credit balance - check user's credits first, then store's if available
        if current_user.credit_balance < 1:
            # If user has no credits, check if they're affiliated with a store
            if current_user.store_id:
                store = Store.query.get(current_user.store_id)
                if not store or store.credit_balance < 1:
                    if is_ajax:
                        return jsonify({'error': 'Insufficient credits'}), 400
                    flash('Insufficient credits', 'error')
                    return redirect(url_for('customer.tryon_form'))
            else:
                if is_ajax:
                    return jsonify({'error': 'Insufficient credits'}), 400
                flash('Insufficient credits', 'error')
                return redirect(url_for('customer.tryon_form'))
        
        # Process TryOn
        output_path = await process_customer_tryon(model_image, garment_image, normalized_category)
        if not output_path:
            if is_ajax:
                return jsonify({'error': 'TryOn processing failed'}), 500
            flash('TryOn processing failed', 'error')
            return redirect(url_for('customer.tryon_form'))
        
        # Log the output path
        current_app.logger.debug(f"Output path from process_customer_tryon: {output_path}")
        
        # Convert to URL
        output_image = url_for('static', filename=output_path)
        current_app.logger.debug(f"Generated URL: {output_image}")
        
        # Verify the file exists at the expected location
        full_path = os.path.join(current_app.static_folder, output_path)
        file_exists = os.path.isfile(full_path)
        current_app.logger.debug(f"Output file {full_path} exists: {file_exists}")
        
        # Save uploaded images for template rendering (when not AJAX)
        model_image_url = None
        garment_image_url = None
        
        if not is_ajax:
            # Save model image
            model_filename = secure_filename(model_image.filename)
            model_path = os.path.join('uploads', 'models', model_filename)
            full_model_path = os.path.join(current_app.static_folder, model_path)
            os.makedirs(os.path.dirname(full_model_path), exist_ok=True)
            model_image.save(full_model_path)
            model_image_url = url_for('static', filename=model_path)
            
            # Save garment image
            garment_filename = secure_filename(garment_image.filename)
            garment_path = os.path.join('uploads', 'garments', garment_filename)
            full_garment_path = os.path.join(current_app.static_folder, garment_path)
            os.makedirs(os.path.dirname(full_garment_path), exist_ok=True)
            garment_image.save(full_garment_path)
            garment_image_url = url_for('static', filename=garment_path)
        
        # Deduct credits from appropriate account
        if current_user.credit_balance >= 1:
            current_user.credit_balance -= 1
            remaining_credits = current_user.credit_balance
        elif current_user.store_id:
            store = Store.query.get(current_user.store_id)
            store.credit_balance -= 1
            remaining_credits = store.credit_balance
                 
        db.session.commit()
        
        # Get store name if applicable
        store_name = None
        if current_user.store_id:
            store = Store.query.get(current_user.store_id)
            store_name = store.name if store else None
        
        # Return appropriate response based on request type
        if is_ajax:
            response_data = {
                'success': True,
                'output_image': output_image,
                'remaining_credits': remaining_credits,
                'debug_info': {
                    'file_exists': file_exists,
                    'output_path': output_path,
                    'full_path': full_path
                }
            }
            current_app.logger.debug(f"Sending JSON response: {response_data}")
            return jsonify(response_data)
        else:
            # For regular form submissions, render the template with results
            return render_template(
                'customer/tryon.html',
                remaining_credits=remaining_credits,
                store_name=store_name,
                model_image_url=model_image_url,
                garment_image_url=garment_image_url,
                output_image=output_image
            )
            
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error during TryOn: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': f'Error during TryOn: {str(e)}'}), 500
        flash(f'Error during TryOn: {str(e)}', 'error')
        return redirect(url_for('customer.tryon_form'))
    

@customer_bp.route("/create", methods=["GET", "POST"])
@login_required
async def create_tryon():
    """Handle creation of new TryOn requests."""
    if request.method == "POST":
        try:
            model_image = request.files.get("model_image")
            garment_image = request.files.get("garment_image")
            category = request.form.get("category")

            # Input validation
            if not all([model_image, garment_image, category]):
                flash("All fields are required!", "error")
                return render_template("customer/create.html", error="All fields are required!")

            # Validate file types
            allowed_extensions = {'png', 'jpg', 'jpeg'}
            if not all(f.filename.lower().endswith(tuple('.' + ext for ext in allowed_extensions)) 
                      for f in [model_image, garment_image]):
                flash("Only image files (PNG, JPG, JPEG) are allowed!", "error")
                return render_template("customer/create.html")

            # Process the TryOn request
            result = await process_customer_tryon(model_image, garment_image, category)
            if not result:
                flash("Failed to process TryOn request", "error")
                return render_template("customer/create.html")

            result_url = url_for('static', filename=result)
            current_app.logger.debug(f"Generated result URL: {result_url}")

            return render_template(
                "customer/create.html",
                result_url=result_url
            )

        except Exception as e:
            current_app.logger.error(f"Error in create_tryon: {str(e)}")
            flash("An unexpected error occurred", "error")
            return render_template("customer/create.html")

    return render_template("customer/create.html")

@customer_bp.route('/dashboard')
@login_required
def dashboard():
    """Display customer dashboard with TryOn history."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('ITEMS_PER_PAGE', 10)

        dashboard_data = get_customer_dashboard_data(current_user.id)
        tryons_data = get_customer_tryons(current_user.store_id, page, per_page)

        return render_template(
            'customer/dashboard.html',
            **dashboard_data,
            tryons=tryons_data['items'],
            page=page,
            total_pages=tryons_data['total_pages']
        )

    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        flash("Unable to load dashboard", "error")
        return redirect(url_for('main.landing_page'))

@customer_bp.route('/download/<int:tryon_id>')
@login_required
def download_result(tryon_id):
    """Download TryOn result image."""
    try:
        tryon = TryOn.query.get_or_404(tryon_id)
        
        if tryon.store_id != current_user.store_id:
            return jsonify({'error': 'Unauthorized access'}), 403

        # Get the result image path
        result_path = tryon.result_image
        full_path = os.path.join(current_app.static_folder, result_path)
        
        if not os.path.exists(full_path):
            current_app.logger.error(f"Result file not found: {full_path}")
            return jsonify({'error': 'Result file not found'}), 404

        return send_file(
            full_path,
            as_attachment=True,
            download_name=f'tryon_result_{tryon_id}.png'
        )

    except Exception as e:
        current_app.logger.error(f"Download error: {str(e)}")
        return jsonify({'error': 'Failed to download result'}), 500