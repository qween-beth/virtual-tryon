import os

# def save_file(file, directory, filename):
#     if not os.path.exists(directory):
#         os.makedirs(directory)
#     file.save(os.path.join(directory, filename))

def get_env_variable(key, default=None):
    return os.getenv(key, default)


import os

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