#!/usr/bin/python3
import sys
import os
from dotenv import load_dotenv

# Add your project directory to the Python path
sys.path.insert(0, "/var/www/html2/")

# Load environment variables from .env file (if it exists)
env_path = "/var/www/html2/.env"
if os.path.exists(env_path):
    load_dotenv(env_path)

from postgress_connector import app as application

if __name__ == "__main__":
    application.run()
