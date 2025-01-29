from app import create_app
from flask import send_from_directory
import os

app = create_app()

# Add route to serve Next.js static files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_nextjs(path):
    # Update path to point to correct out directory
    next_build_dir = '/Users/visheshgowda/Downloads/video-subtitle-generator/out'
    
    if path == "":
        return send_from_directory(next_build_dir, 'index.html')
        
    if os.path.exists(os.path.join(next_build_dir, path)):
        return send_from_directory(next_build_dir, path)
    
    # Fallback to index.html for client-side routing
    return send_from_directory(next_build_dir, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)