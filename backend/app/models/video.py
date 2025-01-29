from datetime import datetime
from bson import ObjectId
from flask import current_app, g
from pymongo import MongoClient, DESCENDING
import os
import shutil
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class Video:
    def __init__(self, app=None):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.upload_folder = os.path.join(self.base_dir, 'uploads')
        self.output_folder = os.path.join(self.base_dir, 'uploads', 'output')
        
        os.makedirs(self.upload_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.teardown_appcontext(self.teardown)

    def get_db(self):
        if 'mongodb_client' not in g:
            mongodb_uri = current_app.config.get('MONGODB_URI')
            if not mongodb_uri:
                raise ValueError("MongoDB URI not configured")
            
            g.mongodb_client = MongoClient(mongodb_uri)
            db_name = mongodb_uri.split('/')[-1].split('?')[0]
            g.db = g.mongodb_client[db_name]
        return g.db.videos

    def teardown(self, exception):
        client = g.pop('mongodb_client', None)
        if client is not None:
            try:
                client.close()
                logger.debug("MongoDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {str(e)}")

    def create_video(self, user_id: str, filename: str, original_path: str):
        try:
            logger.info(f"Creating video entry for user: {user_id}")
            if not os.path.exists(original_path):
                raise FileNotFoundError(f"Video file not found at {original_path}")

            new_upload_path = os.path.join(self.upload_folder, filename)
            logger.debug(f"Original path: {original_path}, New path: {new_upload_path}")

            if original_path != new_upload_path:
                logger.debug("Copying video to upload folder")
                shutil.copy2(original_path, new_upload_path)

            video_data = {
                '_id': ObjectId(),
                'user_id': user_id,
                'filename': filename,
                'original_path': new_upload_path,
                'status': 'uploaded',
                'progress': 0,
                'file_size': os.path.getsize(new_upload_path),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'segments': []
            }
            
            result = self.get_db().insert_one(video_data)
            logger.info(f"Video created with ID: {result.inserted_id}")
            return result

        except Exception as e:
            logger.error(f"Create video error: {str(e)}", exc_info=True)
            if 'new_upload_path' in locals() and os.path.exists(new_upload_path):
                try:
                    os.remove(new_upload_path)
                    logger.debug(f"Cleaned up failed video creation: {new_upload_path}")
                except Exception as cleanup_error:
                    logger.error(f"Cleanup error: {str(cleanup_error)}")
            raise

    def get_video(self, video_id: str) -> Dict[str, Any]:
        try:
            logger.debug(f"Fetching video: {video_id}")
            if not video_id or not ObjectId.is_valid(video_id):
                logger.warning(f"Invalid video ID format: {video_id}")
                return None
            return self.get_db().find_one({'_id': ObjectId(video_id)})
        except Exception as e:
            logger.error(f"Get video error: {str(e)}", exc_info=True)
            return None

    def update_status(self, video_id: str, status: str, error: str = None, progress: int = None):
        try:
            logger.info(f"Updating status for video: {video_id}")
            if not video_id or not ObjectId.is_valid(video_id):
                raise ValueError("Invalid video ID")

            update_data = {
                'status': status,
                'updated_at': datetime.utcnow()
            }
            if error:
                update_data['error'] = error
            if progress is not None:
                update_data['progress'] = progress

            result = self.get_db().update_one(
                {'_id': ObjectId(video_id)},
                {'$set': update_data}
            )
            logger.debug(f"Status update result: {result.modified_count} modified")
            return result
        except Exception as e:
            logger.error(f"Update status error: {str(e)}", exc_info=True)
            raise

    def update_output_path(self, video_id: str, output_path: str, segments: List[Dict]):
        try:
            logger.info(f"Updating output path for video: {video_id}")
            if not video_id or not ObjectId.is_valid(video_id):
                raise ValueError("Invalid video ID")

            update_data = {
                'output_path': output_path,
                'status': 'completed',
                'progress': 100,
                'segments': segments,
                'updated_at': datetime.utcnow()
            }

            result = self.get_db().update_one(
                {'_id': ObjectId(video_id)},
                {'$set': update_data}
            )
            logger.debug(f"Output path update result: {result.modified_count} modified")
            return result
        except Exception as e:
            logger.error(f"Update output path error: {str(e)}", exc_info=True)
            raise

    def delete_video(self, video_id: str):
        try:
            logger.info(f"Deleting video: {video_id}")
            if not video_id or not ObjectId.is_valid(video_id):
                raise ValueError("Invalid video ID")

            video = self.get_video(video_id)
            if video:
                if os.path.exists(video['original_path']):
                    logger.debug(f"Removing original file: {video['original_path']}")
                    os.remove(video['original_path'])
                if 'output_path' in video and os.path.exists(video['output_path']):
                    logger.debug(f"Removing output file: {video['output_path']}")
                    os.remove(video['output_path'])
                result = self.get_db().delete_one({'_id': ObjectId(video_id)})
                logger.info(f"Deleted video: {video_id}")
                return result
            return None
        except Exception as e:
            logger.error(f"Delete video error: {str(e)}", exc_info=True)
            raise
