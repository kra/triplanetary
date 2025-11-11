# Unit Test

```bash
source venv/bin/activate
pytest triplanetary/test
```

# IntegrationTest

After deployment, test the API with curl using Basic Authentication:

```bash
# Test the root endpoint (greeting)
curl -u admin:password https://YOUR-API-URL/

# List all users
curl -u admin:password https://YOUR-API-URL/users

# Create a new user
curl -u admin:password -X POST https://YOUR-API-URL/users \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "password": "newpassword"}'

# Delete a user
curl -u admin:password -X DELETE https://YOUR-API-URL/users \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser"}'
```

Replace `YOUR-API-URL` with the actual API Gateway URL from the deployment output.

# View logs

```bash
source venv/bin/activate
cd triplanetary
chalice logs --stage stage --since 10m --follow
```

# View components in AWS console

- region us-west-2
- AWS Lambda dashboard
