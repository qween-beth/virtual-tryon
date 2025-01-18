
from flask_login import login_required, current_user
from . import customer_bp
from .services import get_customer_dashboard_data, process_customer_tryon, get_customer_tryons
from app.core.models import Store, User, TryOn
from app.core.database import db
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from flask import jsonify
from . import customer_bp
import math
from datetime import datetime


@customer_bp.route("/create", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            # Get form data
            model_image = request.files.get("model_image")
            garment_image = request.files.get("garment_image")
            category = request.form.get("category")

            # Validate inputs
            if not model_image or not garment_image or not category:
                flash("All fields are required!", "error")
                return render_template("index.html", error="All fields are required!")

            # Save uploaded files
            model_image_filename = secure_filename(model_image.filename)
            garment_image_filename = secure_filename(garment_image.filename)

            model_image_path = os.path.join(app.config["UPLOAD_FOLDER"], model_image_filename)
            garment_image_path = os.path.join(app.config["UPLOAD_FOLDER"], garment_image_filename)

            model_image.save(model_image_path)
            garment_image.save(garment_image_path)

            # Simulate result generation (replace this with actual logic)
            output_image_path = os.path.join(app.config["UPLOAD_FOLDER"], "tryon_result.png")

            # Render the results
            return render_template(
                "index.html",
                model_image_url=model_image_path,
                garment_image_url=garment_image_path,
                output_image_url=output_image_path,
            )
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
            return render_template("index.html", error="An error occurred while processing the request.")

    # Handle GET request
    return render_template("index.html")



@customer_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """
    Renders the customer dashboard with try-on history and pagination.
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of try-ons per page

        # Get basic dashboard data
        dashboard_data = get_customer_dashboard_data(current_user.id)
        
        # Get paginated try-ons
        try_ons_data = get_customer_tryons(current_user.store_id, page, per_page)
        
        # Combine all data for the template
        template_data = {
            **dashboard_data,
            'try_ons': try_ons_data['items'],
            'page': page,
            'total_pages': try_ons_data['total_pages'],
            'current_user': current_user
        }
        
        return render_template('customer/dashboard.html', **template_data)
    except Exception as e:
        return jsonify({'error': f'Unable to load dashboard: {str(e)}'}), 500


@customer_bp.route('/download/<int:try_on_id>', methods=['GET'])
@login_required
def download_result(try_on_id):
    """
    Handles downloading of try-on results.
    """
    try:
        try_on = TryOn.query.get_or_404(try_on_id)
        
        # Verify ownership
        if try_on.store_id != current_user.store_id:
            return jsonify({'error': 'Unauthorized access'}), 403
            
        return send_file(
            try_on.result_image_path,
            as_attachment=True,
            download_name=f'tryon_result_{try_on_id}.png'
        )
    except Exception as e:
        return jsonify({'error': f'Error downloading result: {str(e)}'}), 500

@customer_bp.route('/tryon', methods=['GET'])
@login_required
def tryon_form():
    return render_template('customer/tryon.html')

@customer_bp.route('/tryon', methods=['POST'])
@login_required
async def tryon():
    """
    Handles TryOn requests for the customer.
    """
    try:
        # Validate inputs
        if 'model_image' not in request.files or 'garment_image' not in request.files:
            return jsonify({'error': 'Missing required image files'}), 400
        if 'category' not in request.form:
            return jsonify({'error': 'Missing category field'}), 400

        model_image = request.files['model_image']
        garment_image = request.files['garment_image']
        category = request.form['category']

        # Validate category before processing
        normalized_category = normalize_category(category)
        if not normalized_category:
            allowed_categories = [c.value for c in TryOnCategory]
            return jsonify({
                'error': f'Invalid category: "{category}". Allowed categories: {allowed_categories}'
            }), 400

        # Verify the user's store has sufficient credits
        store = Store.query.get(current_user.store_id)
        if not store or store.credit_balance < 1:
            return jsonify({'error': 'Insufficient credits'}), 400

        # Process TryOn
        output_path = await process_customer_tryon(model_image, garment_image, category)
        if not output_path:
            return jsonify({'error': 'TryOn processing failed'}), 500

        # Deduct credits for the TryOn operation
        store.credit_balance -= 1
        db.session.commit()

        output_url = url_for('static', filename=output_path)
        return jsonify({'success': True, 'output_url': output_url})
    except Exception as e:
        return jsonify({'error': f'Error during TryOn: {str(e)}'}), 500