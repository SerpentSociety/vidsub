from flask import Blueprint, request, jsonify, Response, stream_with_context, send_file, make_response, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from werkzeug.utils import secure_filename
from functools import wraps
from bson import ObjectId
from datetime import datetime
from ..core.video_service import VideoService
from ..models.video import Video
import json
import os
import logging

logger = logging.getLogger(__name__)

video_bp = Blueprint('video', __name__)
video_model = Video()

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}
MAX_FILE_SIZE = 500 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def jwt_required_with_url_token():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                token = request.args.get('token')
                if token:
                    decoded_token = decode_token(token)
                    request.current_user = decoded_token['sub']
                    return fn(*args, **kwargs)
                return jwt_required()(fn)(*args, **kwargs)
            except Exception as e:
                logger.error(f"JWT validation error: {str(e)}")
                return jsonify({'error': 'Invalid or expired token'}), 401
        return decorator
    return wrapper

def validate_video_id(video_id):
    if not video_id or not ObjectId.is_valid(video_id):
        return False, "Invalid video ID format"
    return True, None

def validate_subtitle_segments(segments):
    if not isinstance(segments, list):
        return False, "Subtitles must be an array"
    
    required_keys = {'start', 'end', 'text'}
    for idx, segment in enumerate(segments):
        if not isinstance(segment, dict):
            return False, f"Segment {idx} is not an object"
        missing_keys = required_keys - segment.keys()
        if missing_keys:
            return False, f"Segment {idx} missing keys: {', '.join(missing_keys)}"
        if not isinstance(segment['start'], (int, float)) or segment['start'] < 0:
            return False, f"Segment {idx} has invalid start time"
        if not isinstance(segment['end'], (int, float)) or segment['end'] <= segment['start']:
            return False, f"Segment {idx} has invalid end time"
        if not isinstance(segment['text'], str) or len(segment['text'].strip()) == 0:
            return False, f"Segment {idx} has invalid text"
    return True, None

@video_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_video():
    try:
        if 'video' not in request.files:
            logger.warning("No video file in upload request")
            return jsonify({'error': 'No video file provided'}), 400

        file = request.files['video']
        if not file or not file.filename:
            logger.warning("Empty filename in upload request")
            return jsonify({'error': 'No selected file'}), 400

        if not allowed_file(file.filename):
            logger.warning(f"Invalid file type attempted: {file.filename}")
            return jsonify({'error': 'Invalid file type. Allowed types: mp4, mov, avi, mkv'}), 400

        if request.content_length > MAX_FILE_SIZE:
            logger.warning(f"File size exceeded limit: {request.content_length}")
            return jsonify({'error': 'File size exceeds maximum limit (500MB)'}), 400

        filename = secure_filename(file.filename)
        unique_filename = f"{os.urandom(8).hex()}_{filename}"
        upload_path = os.path.join(video_model.upload_folder, unique_filename)
        
        logger.info(f"Starting file upload: {unique_filename}")
        file.save(upload_path)
        logger.debug(f"File saved to: {upload_path}")

        user_id = get_jwt_identity()
        video_doc = video_model.create_video(
            user_id=user_id,
            filename=unique_filename,
            original_path=upload_path
        )

        logger.info(f"Video document created: {video_doc.inserted_id}")
        return jsonify({
            'message': 'Video uploaded successfully',
            'video_id': str(video_doc.inserted_id),
            'filename': unique_filename
        }), 200

    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        if 'upload_path' in locals() and os.path.exists(upload_path):
            try:
                os.remove(upload_path)
                logger.debug(f"Cleaned up failed upload: {upload_path}")
            except Exception as cleanup_error:
                logger.error(f"Cleanup error: {str(cleanup_error)}")
        return jsonify({'error': 'Failed to process upload'}), 500

@video_bp.route('/process', methods=['POST', 'GET'])
@jwt_required_with_url_token()
def process_video():
    try:
        if not hasattr(current_app, 'video_service'):
            current_app.video_service = VideoService()
            logger.info("VideoService initialized")

        if request.method == 'POST':
            data = request.get_json()
            video_id = data.get('video_id')
            is_valid, error_msg = validate_video_id(video_id)
            if not is_valid:
                logger.warning(f"Invalid video ID in process request: {video_id}")
                return jsonify({'error': error_msg}), 400

            target_lang = data.get('target_language', 'en')
            font_size = int(data.get('font_size', 20))

            video = video_model.get_video(video_id)
            if not video:
                logger.warning(f"Video not found: {video_id}")
                return jsonify({'error': 'Video not found'}), 404

            logger.info(f"Starting processing for video: {video_id}")
            return jsonify({'status': 'processing_started'}), 200

        elif request.method == 'GET':
            video_id = request.args.get('video_id')
            is_valid, error_msg = validate_video_id(video_id)
            if not is_valid:
                return jsonify({'error': error_msg}), 400

            target_lang = request.args.get('target_language', 'en')
            font_size = int(request.args.get('font_size', 20))

            video = video_model.get_video(video_id)
            if not video:
                logger.warning(f"Video not found during processing: {video_id}")
                return jsonify({'error': 'Video not found'}), 404

            if video['status'] == 'failed':
                logger.error(f"Processing failed for video: {video_id}")
                return jsonify({'error': video.get('error', 'Processing failed')}), 400

            video_path = video['original_path']
            logger.debug(f"Processing video path: {video_path}")

            def generate():
                try:
                    for progress_data in current_app.video_service.process_video_stream(
                        video_path,
                        target_lang,
                        font_size
                    ):
                        logger.debug(f"Sending SSE update: {progress_data}")
                        yield f"data: {progress_data}\n\n"
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"SSE generation error: {error_msg}", exc_info=True)
                    video_model.update_status(video_id, 'failed', error_msg)
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"

            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': request.headers.get('Origin', '*'),
                    'Access-Control-Allow-Credentials': 'true'
                }
            )

    except Exception as e:
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Video processing failed'}), 500

@video_bp.route('/download/<video_id>', methods=['GET'])
@jwt_required_with_url_token()
def download_video(video_id):
    try:
        is_valid, error_msg = validate_video_id(video_id)
        if not is_valid:
            logger.warning(f"Invalid video ID for download: {video_id}")
            return jsonify({'error': error_msg}), 400

        video = video_model.get_video(video_id)
        if not video:
            logger.warning(f"Video not found for download: {video_id}")
            return jsonify({'error': 'Video not found'}), 404

        if video['status'] != 'completed' or 'output_path' not in video:
            logger.warning(f"Video not ready for download: {video_id}")
            return jsonify({'error': 'Video processing not completed'}), 400

        if not os.path.exists(video['output_path']):
            logger.error(f"Output file missing for video: {video_id}")
            return jsonify({'error': 'Output video file not found'}), 404

        logger.info(f"Serving download for video: {video_id}")
        response = send_file(
            video['output_path'],
            mimetype='video/mp4',
            as_attachment=True,
            download_name=f"subtitled_{video['filename']}"
        )
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

    except Exception as e:
        logger.error(f"Download error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to download video'}), 500

@video_bp.route('/status/<video_id>', methods=['GET'])
@jwt_required_with_url_token()
def get_video_status(video_id):
    try:
        is_valid, error_msg = validate_video_id(video_id)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        video = video_model.get_video(video_id)
        if not video:
            logger.warning(f"Status check for non-existent video: {video_id}")
            return jsonify({'error': 'Video not found'}), 404

        status_data = {
            'status': video['status'],
            'error': video.get('error'),
            'progress': video.get('progress', 0),
            'segments': video.get('segments', [])
        }

        if video['status'] == 'completed' and video.get('output_path'):
            status_data['output_path'] = video['output_path']
            status_data['download_url'] = f"/api/video/download/{str(video['_id'])}"

        logger.debug(f"Returning status for video: {video_id}")
        return jsonify(status_data)

    except Exception as e:
        logger.error(f"Status check error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get video status'}), 500

@video_bp.route('/update_subtitles/<video_id>', methods=['POST'])
@jwt_required()
def update_subtitles(video_id):
    try:
        start_time = datetime.now()
        logger.info(f"Starting subtitle update for video: {video_id}")
        
        data = request.get_json()
        if not data:
            logger.warning("No JSON data in subtitle update request")
            return jsonify({'error': 'Missing request body'}), 400
            
        segments = data.get('segments')
        if not segments:
            logger.warning("Missing segments in subtitle update")
            return jsonify({'error': 'Segments data is required'}), 400
            
        is_valid, error_msg = validate_subtitle_segments(segments)
        if not is_valid:
            logger.warning(f"Invalid subtitle segments: {error_msg}")
            return jsonify({'error': f"Invalid subtitle format: {error_msg}"}), 400
            
        video = video_model.get_video(video_id)
        if not video:
            logger.warning(f"Video not found for subtitle update: {video_id}")
            return jsonify({'error': 'Video not found'}), 404
            
        logger.debug(f"Updating segments for video: {video_id}")
        update_result = video_model.get_db().update_one(
            {'_id': ObjectId(video_id)},
            {'$set': {
                'segments': segments,
                'status': 'processing',
                'progress': 0,
                'updated_at': datetime.utcnow()
            }}
        )
        
        if update_result.modified_count == 0:
            logger.error(f"Failed to update segments for video: {video_id}")
            return jsonify({'error': 'Failed to update subtitles'}), 500
            
        logger.info(f"Successfully updated segments for video: {video_id}")
        logger.debug(f"Segments update took: {(datetime.now() - start_time).total_seconds()} seconds")
        
        return jsonify({
            'message': 'Subtitles updated successfully',
            'video_id': video_id
        }), 200
        
    except Exception as e:
        logger.error(f"Subtitle update error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to update subtitles'}), 500

@video_bp.route('/regenerate/<video_id>', methods=['GET'])
@jwt_required_with_url_token()
def regenerate_video(video_id):
    try:
        # Initialize service if needed
        if not hasattr(current_app, 'video_service'):
            current_app.video_service = VideoService()
            logger.info("VideoService initialized for regeneration")

        # Validate video_id
        if not ObjectId.is_valid(video_id):
            return Response(
                f"data: {json.dumps({'error': 'Invalid video ID'})}\n\n",
                mimetype='text/event-stream',
                headers={
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                    'Access-Control-Allow-Origin': request.headers.get('Origin', '*'),
                    'Access-Control-Allow-Credentials': 'true'
                }
            )

        # Parse and validate segments
        try:
            segments = json.loads(request.args.get('segments', '[]'))
        except json.JSONDecodeError:
            return Response(
                f"data: {json.dumps({'error': 'Invalid segments data'})}\n\n",
                mimetype='text/event-stream',
                headers={
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                    'Access-Control-Allow-Origin': request.headers.get('Origin', '*'),
                    'Access-Control-Allow-Credentials': 'true'
                }
            )

        font_size = int(request.args.get('font_size', 20))
        target_lang = request.args.get('target_language', 'en')

        # Get video
        video = video_model.get_video(video_id)
        if not video or not video.get('original_path'):
            return Response(
                f"data: {json.dumps({'error': 'Video not found'})}\n\n",
                mimetype='text/event-stream',
                headers={
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                    'Access-Control-Allow-Origin': request.headers.get('Origin', '*'),
                    'Access-Control-Allow-Credentials': 'true'
                }
            )

        def generate():
            vs = current_app.video_service
            srt_path = None
            try:
                # Generate SRT
                yield f"data: {json.dumps({'step': 'Generating subtitles', 'progress': 30})}\n\n"
                srt_path = vs._generate_srt(segments, target_lang)

                # Burn subtitles
                yield f"data: {json.dumps({'step': 'Processing video', 'progress': 60})}\n\n"
                output_path = vs._burn_subtitles(
                    video['original_path'],
                    srt_path,
                    target_lang,
                    font_size
                )

                # Update database
                yield f"data: {json.dumps({'step': 'Finalizing', 'progress': 90})}\n\n"
                video_model.update_output_path(video_id, output_path, segments)

                # Final event
                completed_data = {
                    'step': 'Completed',
                    'progress': 100,
                    'output_path': output_path,
                    'segments': segments
                }
                yield f"data: {json.dumps(completed_data)}\n\n"

            except Exception as e:
                logger.error(f"Regeneration failed: {str(e)}")
                error_data = {'error': str(e), 'progress': -1}
                yield f"data: {json.dumps(error_data)}\n\n"
            finally:
                if srt_path and os.path.exists(srt_path):
                    try:
                        os.remove(srt_path)
                        logger.debug(f"Cleaned up SRT file: {srt_path}")
                    except Exception as e:
                        logger.warning(f"Error cleaning up SRT: {str(e)}")

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': request.headers.get('Origin', '*'),
                'Access-Control-Allow-Credentials': 'true'
            }
        )

    except Exception as e:
        logger.error(f"Regeneration endpoint error: {str(e)}")
        return Response(
            f"data: {json.dumps({'error': 'Server error'})}\n\n",
            mimetype='text/event-stream',
            status=500,
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': request.headers.get('Origin', '*'),
                'Access-Control-Allow-Credentials': 'true'
            }
        )

@video_bp.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response

@video_bp.route('', methods=['OPTIONS'])
@video_bp.route('/<path:path>', methods=['OPTIONS'])
def handle_preflight(path=None):
    response = make_response()
    return add_cors_headers(response)