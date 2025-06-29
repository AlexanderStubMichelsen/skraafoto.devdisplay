import sys
import os

# Ensure your app folder is on sys.path
sys.path.insert(0, '/var/www/html2')

# Set environment variables (optional but helpful)
os.environ['FLASK_ENV'] = 'production'

# Import your Flask app
from postgress_connector import app as application
