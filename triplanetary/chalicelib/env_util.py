import dotenv
import json
import os

dotenv.load_dotenv(os.path.join(
    os.path.dirname(__file__), 'environment', '.env'))

def get_env():
    """Return a map of attributes from the environment."""
    # These are in the environment because they are secrets, or because
    # they are decided at deployment time.
    normal_variables = {
        'S3_USERS_BUCKET': os.environ['S3_USERS_BUCKET'],
        'stage': os.environ['stage']}
    return normal_variables
