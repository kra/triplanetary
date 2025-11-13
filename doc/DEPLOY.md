# Triplanetary server deployment

We use dev, stage, and prod instances. We will document stage here.

# Requirements

- Debian box (trixie, ubuntu 23)
- Python 3.12
- AWS CLI configured with appropriate credentials
- AWS account with permissions to create S3 buckets, IAM roles, Lambda functions, and API Gateway

# Setup

To be done once.

## Set up environment

Populate .env to match .env.sample as described in aws.md:

- triplanetary/chalicelib/environment/.env

## Create deployment virtualenv

```bash
python3.12 -m venv venv
source venv/bin/activate
python3 -m pip install chalice pytest
cd triplanetary
pip install -r requirements.txt
```

## Create S3 buckets for user storage

Create the S3 buckets that will store user credentials:

```bash
aws s3 mb s3://triplanetary-users-stage
```

## Create initial admin user

```bash
echo '{"password": "<PASSWORD>"}' > admin.json
aws s3 cp admin.json s3://triplanetary-users-stage/admin
rm admin.json
```

# Create or update and deploy new instance

## Create or check out branch

If deploying stage or prod, check out or create relevant release branch.

## Unit Test

See test.md.

## Deploy

## Deploy instance

```bash
source venv/bin/activate
(cd triplanetary && chalice deploy --stage stage)
```

Note the API endpoint URL.

## Integration Test

See test.md.

# Delete instance

```bash
source venv/bin/activate
cd triplanetary
chalice delete --stage stage
```

```bash
aws s3 rm s3://triplanetary-users-stage --recursive
aws s3 rb s3://triplanetary-users-stage
```
