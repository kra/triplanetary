import base64
import boto3
from chalice import Chalice, Response, UnauthorizedError
import json
import os

from chalicelib import env_util

env = env_util.get_env()
app = Chalice(app_name='triplanetary')
s3_client = boto3.client('s3')

env = env_util.get_env()

def log(msg):
    print(msg)

def get_bucket_name():
    """Get the S3 bucket name from environment variables."""
    return os.environ.get('S3_USERS_BUCKET', 'triplanetary-users-stage')

def get_credentials_from_header():
    """Extract username and password from Basic Auth header."""
    request = app.current_request
    auth_header = request.headers.get('authorization', '')

    if not auth_header.startswith('Basic '):
        return (None, None)

    try:
        credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
        username, password = credentials.split(':', 1)
        return username, password
    except Exception:
        return None, None

def verify_user(username, password):
    """Verify username and password against S3 storage."""
    if not username or not password:
        return False

    bucket_name = get_bucket_name()
    log(bucket_name)

    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=username)
        log(response)
        user_data = json.loads(response['Body'].read().decode('utf-8'))
        log(user_data)
        return user_data.get('password') == password
    except s3_client.exceptions.NoSuchKey:
        return False

def require_auth():
    """Decorator-like function to verify authentication."""
    (username, password) = get_credentials_from_header()
    log((username, password))

    if not verify_user(username, password):
        raise UnauthorizedError('Invalid credentials')
    return username

def list_all_users():
    """List all usernames from S3 bucket."""
    bucket_name = get_bucket_name()
    usernames = []

    response = s3_client.list_objects_v2(Bucket=bucket_name)
    for obj in response['Contents']:
        usernames.append(obj['Key'])
    return usernames

def add_or_update_user(username, password):
    """Add or update a user in S3 bucket."""
    bucket_name = get_bucket_name()
    user_data = {'password': password}

    s3_client.put_object(
        Bucket=bucket_name,
        Key=username,
        Body=json.dumps(user_data),
        ContentType='application/json')

def delete_user(username):
    """Delete a user from S3 bucket."""
    bucket_name = get_bucket_name()
    s3_client.delete_object(Bucket=bucket_name, Key=username)
    return True

@app.route('/')
def index():
    """Greet the user by their username."""
    username = require_auth()
    return {'message': f'Hello, {username}!'}


@app.route('/users', methods=['GET'])
def list_users():
    """Display a list of all usernames."""
    require_auth()
    usernames = list_all_users()
    return {'users': usernames}


@app.route('/users', methods=['POST'])
def create_user():
    """Add or update a user."""
    require_auth()

    request = app.current_request
    user_data = request.json_body
    if not user_data:
        return Response(
            body={'error': 'Request body is required'},
            status_code=400)

    username = user_data.get('username')
    password = user_data.get('password')
    if not username or not password:
        return Response(
            body={'error': 'username and password are required'},
            status_code=400)
    add_or_update_user(username, password)
    return {'message': f'User {username} created/updated successfully'}

@app.route('/users', methods=['DELETE'])
def remove_user():
    """Remove a user."""
    require_auth()

    request = app.current_request
    user_data = request.json_body

    if not user_data:
        return Response(
            body={'error': 'Request body is required'},
            status_code=400)

    username = user_data.get('username')
    if not username:
        return Response(
            body={'error': 'username is required'},
            status_code=400)
    delete_user(username)
    return {'message': f'User {username} deleted successfully'}
