import re
from flask import current_app

def validate_password(password):
    errors = []

    if len(password) < current_app.config['PASSWORD_MIN_LENGTH']:
        errors.append(f"Password must be at least {current_app.config['PASSWORD_MIN_LENGTH']} characters long.")

    if current_app.config['PASSWORD_REQUIRE_UPPERCASE'] and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter.")

    if current_app.config['PASSWORD_REQUIRE_LOWERCASE'] and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter.")

    if current_app.config['PASSWORD_REQUIRE_DIGIT'] and not re.search(r'\d', password):
        errors.append("Password must contain at least one number.")

    if current_app.config['PASSWORD_REQUIRE_SPECIAL_CHAR'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character.")

    return errors