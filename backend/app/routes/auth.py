from flask import Blueprint, request, jsonify
from app.extensions import bcrypt, jwt
from app.models.user import User
from app.utils.validators import validate_password
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

auth_bp = Blueprint('auth', __name__)
user_model = User()

@auth_bp.route('/signup', methods=['POST', 'OPTIONS'])
def signup():
    if request.method == "OPTIONS":
        return jsonify({"msg": "OK"}), 200
        
    try:
        data = request.get_json()
        
        # Log received data for debugging
        print("Received signup data:", data)
        
        # Validate required fields
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        if not all([name, email, password]):
            return jsonify({
                'error': 'Missing required fields',
                'details': 'Name, email, and password are required'
            }), 400

        # Validate email format
        if not user_model.validate_email(email):
            return jsonify({
                'error': 'Invalid email format',
                'details': 'Please provide a valid email address'
            }), 400

        # Validate password
        password_errors = validate_password(password)
        if password_errors:
            return jsonify({
                'error': 'Invalid password',
                'details': password_errors
            }), 400

        # Check if user already exists
        if user_model.find_by_email(email):
            return jsonify({
                'error': 'Email already registered',
                'details': 'Please use a different email address'
            }), 409

        # Hash password
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        # Create user
        user = user_model.create_user(name, email, password_hash)

        # Generate access token
        access_token = create_access_token(identity=email)
        
        return jsonify({
            'access_token': access_token,
            'user': {
                'id': str(user.inserted_id),
                'name': name,
                'email': email
            },
            'message': 'User created successfully'
        }), 201
        
    except Exception as e:
        # Log error for debugging
        print("Error in signup:", str(e))
        return jsonify({
            'error': 'Server error',
            'details': 'An unexpected error occurred'
        }), 500

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == "OPTIONS":
        return jsonify({"msg": "OK"}), 200
        
    try:
        data = request.get_json()
        
        # Log received data for debugging
        print("Received login data:", data)
        
        email = data.get('email')
        password = data.get('password')

        if not all([email, password]):
            return jsonify({
                'error': 'Missing required fields',
                'details': 'Email and password are required'
            }), 400

        # Find user
        user = user_model.find_by_email(email)
        if not user:
            return jsonify({
                'error': 'Authentication failed',
                'details': 'Invalid email or password'
            }), 401

        # Check password
        if not bcrypt.check_password_hash(user['password'], password):
            return jsonify({
                'error': 'Authentication failed',
                'details': 'Invalid email or password'
            }), 401

        # Generate access token
        access_token = create_access_token(identity=email)
        
        return jsonify({
            'access_token': access_token,
            'user': {
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email']
            },
            'message': 'Login successful'
        }), 200
        
    except Exception as e:
        print("Error in login:", str(e))
        return jsonify({
            'error': 'Server error',
            'details': 'An unexpected error occurred'
        }), 500

@auth_bp.route('/validate', methods=['GET', 'OPTIONS'])
def validate_token():
    if request.method == "OPTIONS":
        return jsonify({"msg": "OK"}), 200
        
    # Only apply JWT check for non-OPTIONS requests
    @jwt_required()
    def handle_validation():
        try:
            current_user_email = get_jwt_identity()
            user = user_model.find_by_email(current_user_email)
            
            if not user:
                return jsonify({
                    'error': 'User not found'
                }), 404
                
            return jsonify({
                'user': {
                    'id': str(user['_id']),
                    'name': user['name'],
                    'email': user['email']
                }
            }), 200
            
        except Exception as e:
            print("Error in token validation:", str(e))
            return jsonify({
                'error': 'Server error'
            }), 500
    
    return handle_validation()

@auth_bp.route('/logout', methods=['POST', 'OPTIONS'])
@jwt_required()
def logout():
    if request.method == "OPTIONS":
        return jsonify({"msg": "OK"}), 200
        
    try:
        # Note: Since we're using JWTs, we don't need to do much server-side
        # The frontend should remove the token
        return jsonify({
            'message': 'Logout successful'
        }), 200
        
    except Exception as e:
        print("Error in logout:", str(e))
        return jsonify({
            'error': 'Server error',
            'details': 'An unexpected error occurred'
        }), 500

@auth_bp.errorhandler(Exception)
def handle_error(error):
    print("Unhandled error:", str(error))
    return jsonify({
        'error': 'Server error',
        'details': 'An unexpected error occurred'
    }), 500         

@auth_bp.route('/update-profile', methods=['PUT', 'OPTIONS'])
@jwt_required()
def update_profile():
    if request.method == "OPTIONS":
        return jsonify({"msg": "OK"}), 200
        
    try:
        current_user_email = get_jwt_identity()
        user = user_model.find_by_email(current_user_email)
        
        if not user:
            return jsonify({
                'error': 'User not found'
            }), 404

        data = request.get_json()
        updates = {}
        
        # Update name if provided
        if 'name' in data:
            updates['name'] = data['name']
            
        # Update email if provided and different
        if 'email' in data and data['email'] != current_user_email:
            # Check if new email already exists
            if user_model.find_by_email(data['email']):
                return jsonify({
                    'error': 'Email already exists'
                }), 409
            updates['email'] = data['email']
            
        # Update password if provided
        if 'password' in data and data['password']:
            password_errors = validate_password(data['password'])
            if password_errors:
                return jsonify({
                    'error': 'Invalid password',
                    'details': password_errors
                }), 400
            updates['password'] = bcrypt.generate_password_hash(data['password']).decode('utf-8')

        if updates:
            user_model.update_user(current_user_email, updates)
            
        updated_user = user_model.find_by_email(updates.get('email', current_user_email))
        
        return jsonify({
            'user': {
                'id': str(updated_user['_id']),
                'name': updated_user['name'],
                'email': updated_user['email']
            },
            'message': 'Profile updated successfully'
        }), 200
        
    except Exception as e:
        print("Error in profile update:", str(e))
        return jsonify({
            'error': 'Server error'
        }), 500