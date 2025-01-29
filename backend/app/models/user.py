from pymongo import MongoClient
from flask import current_app, g
from bson import ObjectId
import re

class User:
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the user model with the Flask app context."""
        app.teardown_appcontext(self.teardown)

    def get_db(self):
        """Get or create a database connection."""
        if 'mongodb_client' not in g:
            g.mongodb_client = MongoClient(current_app.config['MONGODB_URI'])
            g.db = g.mongodb_client[g.mongodb_client.get_default_database().name]
        return g.db

    def teardown(self, exception):
        """Close the database connection at the end of the request."""
        client = g.pop('mongodb_client', None)
        if client is not None:
            client.close()

    def create_user(self, name, email, password_hash):
        user_data = {
            'name': name,
            'email': email,
            'password': password_hash,
            'created_at': ObjectId().generation_time
        }
        return self.get_db().users.insert_one(user_data)

    def find_by_email(self, email):
        return self.get_db().users.find_one({'email': email})

    def validate_email(self, email):
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_regex, email) is not None
    
    def update_user(self, email, updates):
        """Update user document with the provided updates."""
        return self.get_db().users.update_one(
            {'email': email},
            {'$set': updates}
        )