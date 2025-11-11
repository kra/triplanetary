# System overview

# Web pages

The system returns a HTTPS response when the user makes a HTTPS GET, PUT, or POST request.

The response displays a web page.

# Authentication

Requests are authenticated with a username and password.

Valid username and password combinations are stored in the "users" S3 bucket.

# Pages

## /

The landing page greets the user by their username.

Requests:
- GET
  - Greet the user by their username.

## /users

The users page lists and updates usernames and passwords.

Requests:
- GET
  - Display a list of all usernames.
- POST
  - Add a user by updating the users S3 bucket, adding or updating an object with username as the key and password as the value.
  - Arguments: username, password
- DELETE
  - Remove a user by updating the users S3 bucket, deleting the object with username as the key.
  - Arguments: username
