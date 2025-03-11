import os
from flask import current_app


def get_env_variable(key, default=None):
    return os.getenv(key, default)

def normalize_static_path(path):
    """
    Converts any path to a proper static URL path.
    
    Args:
        path (str): File path to normalize
        
    Returns:
        str: Normalized path relative to static folder with forward slashes
    """
    if os.path.isabs(path):
        static_folder = current_app.static_folder
        if path.startswith(static_folder):
            rel_path = os.path.relpath(path, static_folder)
        else:
            rel_path = os.path.basename(path)
    else:
        rel_path = path
    
    # Replace backslashes with forward slashes for URLs
    return rel_path.replace('\\', '/')


def save_file(file, folder, filename):
    """
    Safely saves an uploaded file to the specified folder.
    
    Args:
        file: FileStorage object from Flask
        folder (str): Destination folder path
        filename (str): Desired filename
        
    Returns:
        str: Path to the saved file
    """
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, filename)
    file.save(file_path)
    return file_path


# Put this in app/utils/helpers.py
from app.utils.constants import TryOnCategory

def normalize_category(category: str) -> str:
    """
    Normalizes the garment category string to match API expectations.
    
    Args:
        category: Input category string
        
    Returns:
        Normalized category string or None if invalid
    """
    category_map = {
        # Tops
        'top': TryOnCategory.TOPS.value,
        'shirt': TryOnCategory.TOPS.value,
        'tshirt': TryOnCategory.TOPS.value,
        't-shirt': TryOnCategory.TOPS.value,
        'tops': TryOnCategory.TOPS.value,
        
        # Bottoms
        'bottom': TryOnCategory.BOTTOMS.value,
        'pants': TryOnCategory.BOTTOMS.value,
        'skirt': TryOnCategory.BOTTOMS.value,
        'bottoms': TryOnCategory.BOTTOMS.value,
        
        # Dresses
        'dress': TryOnCategory.DRESSES.value,
        'dresses': TryOnCategory.DRESSES.value,
        
        # Outerwear
        'outerwear': TryOnCategory.OUTERWEAR.value,
        'jacket': TryOnCategory.OUTERWEAR.value,
        'coat': TryOnCategory.OUTERWEAR.value
    }
    
    normalized = category_map.get(category.lower())
    return normalized if normalized in [c.value for c in TryOnCategory] else None