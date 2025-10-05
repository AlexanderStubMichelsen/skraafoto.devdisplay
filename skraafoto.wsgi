import sys
import os

# Ensure your project directory is on sys.path
sys.path.insert(0, '/var/www/skraafoto')

from postgress_connector import app as application
