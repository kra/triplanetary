# Triplanetary server deployment

# Requirements

- debian box (trixie, ubuntu 23)
- Python 3.12

# Setup

To be done once.

## Create deployment virtualenv

- python3.12 -m venv venv
- source venv/bin/activate
- python3 -m pip install chalice pytest
- cd triplanetary
- pip install -r requirements.txt

# Create and deploy new instances

## Deploy instances

Deploy the instances:

- source venv/bin/activate
- chalice deploy --stage stage

# Delete instances

- source venv/bin/activate
- chalice delete --stage stage
