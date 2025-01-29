import os
import sys
import groq
import ffmpeg
import json
import uuid
import requests
from typing import Generator, Optional, List, Dict
from flask import current_app
from bson import ObjectId
from transformers import MarianMTModel, MarianTokenizer
from datetime import datetime
from ..utils.language_utils import get_font_path, normalize_lang_code
from ..models.video import Video
import logging

# Configure logging
logger = logging.getLogger(__name__)

class ProcessingSteps:
    INIT = "Initializing"
    EXTRACT_AUDIO = "Extracting audio"
    DETECT_LANGUAGE = "Detecting language"
    TRANSCRIBE = "Transcribing"
    TRANSLATE = "Translating"
    GENERATE_SRT = "Generating subtitles"
    ADD_SUBTITLES = "Adding subtitles"
    FINALIZE = "Finalizing"

class VideoService:
    def __init__(self):
        logger.info("Initializing VideoService")
        self.initialized = False
        self.client: Optional[groq.Client] = None
        self.translation_models = {}
        app_dir = os.path.dirname(os.path.dirname(__file__))
        self.upload_folder = os.path.join(app_dir, 'uploads')
        self.output_folder = os.path.join(app_dir, 'uploads', 'output')
        
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        logger.debug(f"Set HF_ENDPOINT to: {os.environ['HF_ENDPOINT']}")
        
        for folder in [self.upload_folder, self.output_folder]:
            os.makedirs(folder, exist_ok=True)
            logger.debug(f"Ensured directory exists: {folder}")
            
        self.initialized = True
        logger.info("VideoService initialized successfully")

    def ensure_initialized(self):
        """Ensure Groq client is initialized with valid API key"""
        if not self.client:
            logger.info("Initializing Groq client")
            api_key = os.getenv('GROQ_API_KEY') or current_app.config.get('GROQ_API_KEY')
            if not api_key:
                logger.error("No GROQ_API_KEY found in environment or config")
                raise ValueError("GROQ_API_KEY not found")
            try:
                self.client = groq.Client(api_key=api_key)
                logger.info("Groq client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {str(e)}")
                raise

    def validate_and_get_video_id(self, video_path: str) -> str:
        """Validate and retrieve video ID from path or generate new one"""
        try:
            basename = os.path.basename(video_path)
            logger.debug(f"Processing video path: {basename}")
            name_parts = basename.split('_')
            
            for part in name_parts:
                part = os.path.splitext(part)[0]
                if ObjectId.is_valid(part):
                    logger.info(f"Found valid video ID in filename: {part}")
                    return str(part)
            
            logger.debug("No video ID in filename, checking database")
            video = Video().get_db().find_one({'original_path': video_path})
            if video and '_id' in video:
                video_id = str(video['_id'])
                logger.info(f"Found existing video ID in database: {video_id}")
                return video_id
            
            new_id = str(ObjectId())
            logger.info(f"Generated new video ID: {new_id}")
            return new_id
        except Exception as e:
            logger.error(f"Error validating video ID: {str(e)}")
            return str(ObjectId())

    def _extract_audio(self, video_path: str) -> str:
        """Extract audio from video file"""
        audio_path = os.path.join(self.output_folder, f"{uuid.uuid4()}.wav")
        logger.info(f"Extracting audio from video: {video_path}")
        logger.debug(f"Target audio path: {audio_path}")
        
        try:
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, ac=1, ar=16000)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            logger.info("Audio extraction completed successfully")
            return audio_path
        except ffmpeg.Error as e:
            error_message = f"FFmpeg error: {e.stderr.decode('utf-8') if e.stderr else 'Unknown error'}"
            logger.error(error_message)
            raise RuntimeError(error_message)
        except Exception as e:
            logger.error(f"Unexpected error in audio extraction: {str(e)}")
            raise

    def _model_exists_on_hf(self, model_name: str) -> bool:
        """Check if a model exists on HuggingFace hub"""
        try:
            logger.debug(f"Checking HuggingFace for model: {model_name}")
            api_url = f"https://huggingface.co/api/models/{model_name}"
            response = requests.get(api_url, timeout=10)
            exists = response.status_code == 200
            logger.info(f"Model {model_name} {'exists' if exists else 'not found'} on HuggingFace")
            return exists
        except requests.exceptions.Timeout:
            logger.warning(f"HuggingFace API timeout for model: {model_name}")
            return False
        except Exception as e:
            logger.error(f"Error checking HuggingFace model: {str(e)}")
            return False

    def get_translation_model(self, source_lang: str, target_lang: str):
        """Get appropriate translation model for language pair with fallbacks"""
        source_lang = normalize_lang_code(source_lang)
        target_lang = normalize_lang_code(target_lang)
        logger.info(f"Getting translation model for {source_lang} -> {target_lang}")

        # For Arabic to English, prefer Groq translation
        if source_lang == 'ar' and target_lang == 'en':
            logger.info("Arabic to English detected, will use Groq translation")
            return None

        model_variants = [
            f'Helsinki-NLP/opus-mt-{source_lang}-{target_lang}',
            f'Helsinki-NLP/opus-mt-tc-big-{source_lang}-{target_lang}',
            f'Helsinki-NLP/opus-mt-{source_lang}-{target_lang}-big',
        ]

        # Check cached models first
        for model_name in model_variants:
            if model_name in self.translation_models:
                logger.info(f"Using cached translation model: {model_name}")
                return self.translation_models[model_name]

        # Try direct translation models
        logger.info("Attempting to load direct translation models")
        for model_name in model_variants:
            try:
                if self._model_exists_on_hf(model_name):
                    logger.info(f"Loading direct translation model: {model_name}")
                    self.translation_models[model_name] = {
                        'model': MarianMTModel.from_pretrained(model_name),
                        'tokenizer': MarianTokenizer.from_pretrained(model_name)
                    }
                    return self.translation_models[model_name]
            except Exception as e:
                logger.warning(f"Failed to load direct model {model_name}: {str(e)}")
                continue

        # Try pivot translation via English
        if source_lang != 'en':
            try:
                logger.info("Attempting pivot translation via English")
                source_to_en = f'Helsinki-NLP/opus-mt-{source_lang}-en'
                en_to_target = f'Helsinki-NLP/opus-mt-en-{target_lang}'

                if not self._model_exists_on_hf(source_to_en):
                    logger.warning(f"Source pivot model not found: {source_to_en}")
                    return None
                if not self._model_exists_on_hf(en_to_target):
                    logger.warning(f"Target pivot model not found: {en_to_target}")
                    return None

                logger.info("Loading pivot translation models")
                self.translation_models[f'{source_lang}-{target_lang}_pivot'] = {
                    'model': [
                        MarianMTModel.from_pretrained(source_to_en),
                        MarianMTModel.from_pretrained(en_to_target)
                    ],
                    'tokenizer': [
                        MarianTokenizer.from_pretrained(source_to_en),
                        MarianTokenizer.from_pretrained(en_to_target)
                    ]
                }
                return self.translation_models[f'{source_lang}-{target_lang}_pivot']
            except Exception as e:
                logger.error(f"Pivot translation setup failed: {str(e)}")

        logger.warning("No suitable translation models found")
        return None

    def _translate_with_groq_fallback(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text using Groq LLM as fallback"""
        self.ensure_initialized()
        try:
            logger.info(f"Using Groq LLM for translation: {source_lang} -> {target_lang}")
            logger.debug(f"Text to translate: {text[:100]}...")

            # Enhanced prompt for Arabic translation
            if source_lang == 'ar':
                system_prompt = (
                    "You are an expert Arabic translator. Translate the following text to English, "
                    "maintaining proper context and nuance. Preserve any technical terms, names, "
                    "and numbers exactly as they appear. Provide a natural, fluent translation "
                    "that captures the original meaning accurately."
                )
            else:
                system_prompt = (
                    f"Translate the following text from {source_lang} to {target_lang}. "
                    "Maintain exact meaning, preserve numbers and proper nouns."
                )

            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                model="mixtral-8x7b-32768",
                temperature=0.1,
                max_tokens=1000
            )

            translated = response.choices[0].message.content.strip()
            logger.info("Groq translation completed successfully")
            logger.debug(f"Translated text: {translated[:100]}...")
            return translated

        except Exception as e:
            logger.error(f"Groq translation failed: {str(e)}")
            logger.error(f"Original text: {text[:100]}...")
            return text

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text between languages with enhanced Arabic support"""
        source_lang = normalize_lang_code(source_lang)
        target_lang = normalize_lang_code(target_lang)
        
        logger.info(f"Translating text from {source_lang} to {target_lang}")
        logger.debug(f"Input text: {text[:100]}...")
        
        if source_lang == target_lang:
            logger.debug("Skipping translation (same language)")
            return text

        # For Arabic to English, prefer Groq directly
        if source_lang == 'ar' and target_lang == 'en':
            logger.info("Arabic to English detected, using Groq directly")
            return self._translate_with_groq_fallback(text, source_lang, target_lang)

        model_info = self.get_translation_model(source_lang, target_lang)
        if not model_info:
            logger.warning("No translation model available, using Groq fallback")
            return self._translate_with_groq_fallback(text, source_lang, target_lang)

        try:
            logger.debug(f"Using translation model: {model_info['tokenizer'].name_or_path}")
            if isinstance(model_info['model'], list):
                # Pivot translation via English
                tokenizer1, tokenizer2 = model_info['tokenizer']
                model1, model2 = model_info['model']
                
                logger.debug("Performing pivot translation via English")
                
                # First translation to English
                inputs = tokenizer1([text], return_tensors="pt", 
                                  padding=True, truncation=True, max_length=512)
                translated = model1.generate(**inputs)
                pivot_text = tokenizer1.decode(translated[0], skip_special_tokens=True)
                logger.debug(f"Pivot text (English): {pivot_text[:100]}...")
                
                # Then to target language
                inputs = tokenizer2([pivot_text], return_tensors="pt", 
                                 padding=True, truncation=True, max_length=512)
                translated = model2.generate(**inputs)
                final_text = tokenizer2.decode(translated[0], skip_special_tokens=True)
                logger.debug(f"Final translated text: {final_text[:100]}...")
                return final_text
            else:
                # Direct translation
                logger.debug("Performing direct translation")
                tokenizer = model_info['tokenizer']
                model = model_info['model']
                inputs = tokenizer([text], return_tensors="pt", 
                                 padding=True, truncation=True, max_length=512)
                translated = model.generate(**inputs)
                final_text = tokenizer.decode(translated[0], skip_special_tokens=True)
                logger.debug(f"Translated text: {final_text[:100]}...")
                return final_text
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            logger.warning("Falling back to Groq translation")
            return self._translate_with_groq_fallback(text, source_lang, target_lang)

    def detect_language(self, audio_path: str) -> str:
        """Detect language of audio content using Whisper"""
        try:
            logger.info("Starting language detection with Whisper")
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    response_format="verbose_json"
                )
                
                if not isinstance(response, dict):
                    response = response.model_dump()
                
                detected_lang = response.get('language', 'en')
                normalized_lang = normalize_lang_code(detected_lang)
                logger.info(f"Whisper detected language code: {detected_lang}, normalized to: {normalized_lang}")
                return normalized_lang
        except Exception as e:
            logger.error(f"Language detection error: {str(e)}, defaulting to 'en'")
            return 'en'

    def _transcribe_with_groq(self, audio_path: str, source_lang: str, target_lang: str) -> dict:
        """Transcribe audio using Groq's Whisper model"""
        try:
            logger.info(f"Starting transcription (source={source_lang}, target={target_lang})")
            logger.info(f"Audio file: {audio_path}")

            with open(audio_path, "rb") as audio_file:
                # Try translations API first if target is English
                if target_lang == 'en' and source_lang != 'en':
                    try:
                        logger.info("Attempting direct English translation with Whisper translations API")
                        response = self.client.audio.translations.create(
                            file=audio_file,
                            model="whisper-large-v3",
                            response_format="verbose_json"
                        )
                        logger.info("Translation API call successful")
                    except Exception as e:
                        logger.warning(f"Translations API failed: {str(e)}, falling back to transcription")
                        response = self.client.audio.transcriptions.create(
                            file=audio_file,
                            model="whisper-large-v3",
                            response_format="verbose_json",
                            language=source_lang
                        )
                else:
                    logger.info(f"Using transcription API with language={source_lang}")
                    response = self.client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3",
                        response_format="verbose_json",
                        language=source_lang
                    )

            if not isinstance(response, dict):
                response = response.model_dump()
                logger.debug("Converted response to dictionary format")

            # Extract and validate detected language
            detected_language = response.get('language', source_lang)
            normalized_detected = normalize_lang_code(detected_language)
            logger.info(f"Whisper detected language: {detected_language} (normalized: {normalized_detected})")

            # Get sample text for verification
            segments = response.get('segments', [])
            if segments:
                sample_text = segments[0].get('text', '')
                logger.info(f"Sample text from first segment: {sample_text[:100]}")
            else:
                logger.warning("No segments found in transcription response")
                sample_text = ''

            # Process and validate segments
            processed_segments = []
            for idx, segment in enumerate(segments, 1):
                try:
                    if all(key in segment for key in ['start', 'end', 'text']):
                        if segment['end'] > segment['start'] and segment['text'].strip():
                            processed_segments.append({
                                'start': float(segment['start']),
                                'end': float(segment['end']),
                                'text': segment['text'].strip()
                            })
                        else:
                            logger.warning(f"Invalid segment timing or empty text in segment {idx}")
                    else:
                        logger.warning(f"Missing required keys in segment {idx}")
                except Exception as e:
                    logger.error(f"Error processing segment {idx}: {str(e)}")

            logger.info(f"Successfully processed {len(processed_segments)} segments")
            return {
                'segments': processed_segments,
                'detected_language': normalized_detected,
                'sample_text': sample_text
            }

        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            return {
                'segments': [],
                'detected_language': source_lang,
                'sample_text': ''
            }

    def _process_subtitles(self, subtitles: list, source_lang: str, target_lang: str) -> list:
        """Process and translate subtitles with enhanced logging"""
        logger.info(f"Processing {len(subtitles)} subtitle segments")
        logger.info(f"Translation direction: {source_lang} -> {target_lang}")
        
        processed = []
        total_segments = len(subtitles)
        translation_errors = 0
        
        for idx, sub in enumerate(subtitles, 1):
            try:
                translated_text = self.translate_text(sub['text'], source_lang, target_lang)
                processed.append({
                    'start': sub['start'],
                    'end': sub['end'],
                    'text': translated_text
                })
                
                # Detailed logging every few segments
                if idx % 5 == 0:
                    logger.info(f"Progress: {idx}/{total_segments} segments translated")
                    logger.debug(f"Sample translation {idx}:")
                    logger.debug(f"Original: {sub['text']}")
                    logger.debug(f"Translated: {translated_text}")
                
            except Exception as e:
                translation_errors += 1
                logger.error(f"Failed to translate segment {idx}: {str(e)}")
                logger.error(f"Problematic text: {sub['text']}")
                # Keep original if translation fails
                processed.append(sub)
                
                if translation_errors >= 5:
                    logger.critical(f"High translation failure rate: {translation_errors} failures")

        logger.info(f"Completed translation of {len(processed)} segments")
        if translation_errors > 0:
            logger.warning(f"Total translation errors: {translation_errors}")
        
        return processed

    def _send_progress(self, step: str, progress: int, data: dict = None) -> str:
        """Send progress updates with enhanced logging"""
        message = {
            'step': step,
            'progress': progress,
            'status': 'failed' if progress == -1 else 'completed' if progress == 100 else 'processing'
        }
        if data:
            message.update(data)
            
        logger.info(f"Progress update - Step: {step}, Progress: {progress}%")
        if data:
            logger.debug(f"Additional data: {json.dumps(data, ensure_ascii=False)}")
            
        return json.dumps(message)

    def process_video_stream(self, video_path: str, target_lang: str, user_font_size: Optional[int] = None) -> Generator:
        """Main video processing pipeline with enhanced error handling and logging"""
        audio_path = None
        video_id = None
        start_time = datetime.now()
        
        try:
            video_id = self.validate_and_get_video_id(video_path)
            logger.info(f"Starting video processing for ID: {video_id}")
            logger.info(f"Target language: {target_lang}")
            logger.info(f"Input video path: {video_path}")
            
            yield self._send_progress(ProcessingSteps.INIT, 0)
            self.ensure_initialized()

            # Check for existing edited segments
            video = Video().get_video(video_id)
            existing_segments = video.get('segments', []) if video else []
            use_existing_segments = len(existing_segments) > 0

            if use_existing_segments:
                logger.info(f"Using {len(existing_segments)} existing edited segments")
                yield self._send_progress(ProcessingSteps.TRANSLATE, 80, {
                    'translation': '\n'.join(s['text'] for s in existing_segments)
                })
                translated_subs = existing_segments
            else:
                # Extract audio
                yield self._send_progress(ProcessingSteps.EXTRACT_AUDIO, 10)
                audio_path = self._extract_audio(video_path)
                yield self._send_progress(ProcessingSteps.EXTRACT_AUDIO, 30)

                # Detect language
                yield self._send_progress(ProcessingSteps.DETECT_LANGUAGE, 35)
                source_lang = self.detect_language(audio_path)
                logger.info(f"Detected source language: {source_lang}")
                yield self._send_progress(ProcessingSteps.DETECT_LANGUAGE, 40, {
                    'detected_language': source_lang
                })

                # Transcribe
                yield self._send_progress(ProcessingSteps.TRANSCRIBE, 45)
                transcription = self._transcribe_with_groq(audio_path, source_lang, target_lang)
                segments = transcription['segments']
                detected_language = transcription['detected_language']

                if not segments:
                    error_msg = "No valid subtitles generated"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.info(f"Generated {len(segments)} segments")
                logger.info(f"Detected language from transcription: {detected_language}")

                yield self._send_progress(ProcessingSteps.TRANSCRIBE, 60, {
                    'transcription': '\n'.join(s['text'] for s in segments)
                })

                # Process translation
                if detected_language != target_lang:
                    logger.info(f"Translation needed: {detected_language} -> {target_lang}")
                    yield self._send_progress(ProcessingSteps.TRANSLATE, 65)
                    translated_subs = self._process_subtitles(segments, detected_language, target_lang)
                    yield self._send_progress(ProcessingSteps.TRANSLATE, 80, {
                        'translation': '\n'.join(s['text'] for s in translated_subs)
                    })
                    logger.info(f"Translation completed: {len(translated_subs)} segments")
                else:
                    logger.info(f"No translation needed - detected language matches target: {target_lang}")
                    translated_subs = segments

            # Generate subtitles
            yield self._send_progress(ProcessingSteps.GENERATE_SRT, 85)
            yield self._send_progress(ProcessingSteps.ADD_SUBTITLES, 90)
            
            output_path = self._add_subtitles(video_path, translated_subs, target_lang, user_font_size)
            
            if not os.path.exists(output_path):
                raise FileNotFoundError("Output video not generated")

            Video().update_output_path(video_id, output_path, translated_subs)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Video processing completed in {processing_time:.2f} seconds")
            logger.info(f"Output video saved to: {output_path}")
            
            yield self._send_progress(ProcessingSteps.FINALIZE, 100, {
                'output_path': output_path,
                'transcription': '\n'.join(s['text'] for s in translated_subs),
                'segments': translated_subs
            })

        except Exception as e:
            logger.error(f"Critical processing error: {str(e)}", exc_info=True)
            if video_id:
                error_msg = str(e)
                logger.error(f"Updating video status to failed: {video_id}")
                Video().update_status(video_id, 'failed', error_msg, -1)
            yield self._send_progress("Error", -1, {'error': str(e)})
            raise

        finally:
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    logger.debug(f"Cleaned up temporary audio file: {audio_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up audio file: {str(e)}")

    def _generate_srt(self, subtitles: list, target_lang: str) -> str:
        """Generate SRT file from subtitles"""
        srt_path = os.path.join(self.output_folder, f"{uuid.uuid4()}.srt")
        logger.info(f"Generating SRT file: {srt_path}")
        logger.info(f"Processing {len(subtitles)} subtitle segments")
        
        try:
            with open(srt_path, 'w', encoding='utf-8') as srt_file:
                for idx, sub in enumerate(subtitles, start=1):
                    start = self._format_srt_time(sub['start'])
                    end = self._format_srt_time(sub['end'])
                    text = sub['text']
                    
                    srt_file.write(f"{idx}\n{start} --> {end}\n{text}\n\n")

            logger.info("SRT file generated successfully")
            return srt_path
        except Exception as e:
            logger.error(f"SRT generation failed: {str(e)}")
            raise

    def _format_srt_time(self, seconds: float) -> str:
        """Format time for SRT format"""
        try:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace('.', ',')
        except Exception as e:
            logger.error(f"Time formatting error: {str(e)}")
            raise

    def _calculate_subtitle_properties(self, width: int, height: int, user_font_size: Optional[int] = None) -> tuple:
        """Calculate subtitle display properties based on video dimensions"""
        try:
            logger.info(f"Calculating subtitle properties for dimensions: {width}x{height}")
            aspect_ratio = width / height
            is_vertical = aspect_ratio < 0.6
            safe_zone = 0.82

            if is_vertical:
                logger.info("Vertical video layout detected")
                max_lines = 1
                safe_zone = 0.90
                h_margin = max(width * 0.06, 15)
                v_margin = height * 0.08
                char_per_line = 42

                if user_font_size:
                    base_size = min(max(user_font_size, 12), 20)
                    logger.debug(f"Using user font size for vertical: {base_size}")
                else:
                    base_dimension = min(width, height) * 0.038
                    size_multiplier = 0.92
                    base_size = base_dimension * size_multiplier
                    base_size = min(max(base_size, 14), 20)

                line_spacing = int(base_size * 0.25)
            else:
                logger.info("Standard video layout detected")
                base_dimension = height * 0.042
                size_multiplier = 1.0
                max_lines = 2
                h_margin = max(width * 0.12, 50)
                safe_zone = 0.82

                if user_font_size:
                    base_size = min(max(user_font_size, 22), 44)
                    logger.debug(f"Using user font size: {base_size}")
                else:
                    base_size = base_dimension * size_multiplier
                    base_size = min(max(base_size, 22), 44)

                line_spacing = int(base_size * 0.3)
                v_margin = height * 0.06
                char_per_line = int((width * safe_zone) / (base_size * 0.6))
                char_per_line = min(max(char_per_line, 20), 50)

            dimensions = (
                int(base_size),
                max_lines,
                int(v_margin),
                int(base_size + line_spacing),
                int(h_margin),
                char_per_line
            )
            
            logger.info(f"Calculated subtitle properties: {dimensions}")
            return dimensions

        except Exception as e:
            logger.error(f"Subtitle scaling calculation failed: {str(e)}")
            return (24, 2, 20, 28, 50, 40)

    def _burn_subtitles(self, video_path: str, srt_path: str, target_lang: str, font_size: int) -> str:
        """Burn subtitles into video"""
        try:
            output_path = os.path.join(self.output_folder, f"regenerated_{uuid.uuid4()}.mp4")
            logger.info(f"Burning subtitles into video: {video_path}")
            logger.info(f"Output path: {output_path}")

            probe = ffmpeg.probe(video_path)
            video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            width = int(video_stream['width'])
            height = int(video_stream['height'])

            logger.info(f"Video dimensions: {width}x{height}")
            
            font_size, _, margin_v, line_height, h_margin, _ = self._calculate_subtitle_properties(
                width, height, font_size
            )
            
            font_path = get_font_path(target_lang)
            logger.debug(f"Using font: {font_path}")

            style = [
                f"FontName={font_path}",
                f"FontSize={font_size}",
                "PrimaryColour=&H00FFFFFF",
                "BackColour=&H80000000",
                "BorderStyle=4",
                "Outline=0",
                "Shadow=0",
                f"MarginL={h_margin}",
                f"MarginR={h_margin}",
                f"MarginV={margin_v}",
                "Alignment=2",
                "WrapStyle=1",
                f"PlayResX={width}",
                f"PlayResY={height}",
                f"LineSpacing={line_height - font_size}"
            ]

            logger.debug(f"Applied subtitle style: {style}")

            input_stream = ffmpeg.input(video_path)
            
            subtitled = input_stream.filter(
                'subtitles',
                srt_path,
                force_style=",".join(style),
                **{
                    'charenc': 'UTF-8',
                    'original_size': f"{width}x{height}"
                }
            )

            logger.info("Starting video rendering with subtitles")
            (
                ffmpeg
                .output(
                    subtitled,
                    input_stream.audio,
                    output_path,
                    vcodec='libx264',
                    crf=18,
                    preset='slow',
                    movflags='+faststart',
                    acodec='aac',
                    pix_fmt='yuv420p'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            logger.info("Video rendering completed successfully")
            return output_path

        except Exception as e:
            logger.error(f"Error burning subtitles: {str(e)}")
            raise

    def _add_subtitles(self, video_path: str, subtitles: list, target_lang: str, user_font_size: Optional[int] = None) -> str:
        """Add subtitles to video with fallback handling"""
        if not subtitles:
            logger.error("No subtitles provided")
            raise ValueError("No subtitles to add")

        output_path = os.path.join(self.output_folder, f"{uuid.uuid4()}.mp4")
        srt_path = self._generate_srt(subtitles, target_lang)
        
        try:
            logger.info(f"Adding subtitles to video: {video_path}")
            logger.info(f"Target output: {output_path}")
            logger.debug(f"Using SRT file: {srt_path}")

            probe = ffmpeg.probe(video_path)
            video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            
            logger.info(f"Video dimensions: {width}x{height}")
            
            (font_size, max_lines, margin_v, line_height, 
             h_margin, max_chars) = self._calculate_subtitle_properties(width, height, user_font_size)
            
            font_path = get_font_path(target_lang)
            logger.debug(f"Using font: {font_path} with size {font_size}")

            style = [
                f"FontName={font_path}",
                f"FontSize={font_size}",
                "PrimaryColour=&H00FFFFFF",
                "BackColour=&H80000000",
                "BorderStyle=4",
                "Outline=0",
                "Shadow=0",
                f"MarginL={h_margin}",
                f"MarginR={h_margin}",
                f"MarginV={margin_v}",
                "Alignment=2",
                "WrapStyle=1",
                f"PlayResX={width}",
                f"PlayResY={height}",
                f"LineSpacing={line_height - font_size}",
                f"MaxLineCount={max_lines}",
                f"MaximumLineLength={max_chars}"
            ]

            input_stream = ffmpeg.input(video_path)
            
            # Handle vertical video
            if (width/height) < 0.6:
                logger.info("Processing vertical video format")
                scaled = input_stream.filter('scale', w='-2', h=int(height * 0.92))
                padded = scaled.filter('pad', width, height, '(ow-iw)/2', 0)
                final_output = padded
            else:
                logger.info("Processing standard video format")
                final_output = input_stream

            subtitled = final_output.filter(
                'subtitles',
                srt_path,
                force_style=",".join(style),
                **{
                    'charenc': 'UTF-8',
                    'original_size': f"{width}x{height}"
                }
            )

            logger.info("Starting video rendering")
            (
                ffmpeg
                .output(
                    subtitled,
                    input_stream.audio,
                    output_path,
                    vcodec='libx264',
                    crf=18,
                    preset='slow',
                    movflags='+faststart',
                    acodec='aac',
                    pix_fmt='yuv420p'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            logger.info("Video rendered successfully")
            return output_path

        except ffmpeg.Error as e:
            error_msg = f"FFmpeg error: {e.stderr.decode('utf-8') if e.stderr else str(e)}"
            logger.error(f"Subtitle rendering failed: {error_msg}")
            
            logger.info("Attempting fallback subtitle rendering")
            try:
                (
                    ffmpeg
                    .input(video_path)
                    .output(output_path, vf=f"subtitles={srt_path}")
                    .overwrite_output()
                    .run()
                )
                logger.info("Fallback rendering successful")
                return output_path
            except Exception as fallback_error:
                logger.error(f"Fallback rendering failed: {str(fallback_error)}")
                raise

        except Exception as e:
            logger.error(f"Video processing failed: {str(e)}")
            raise
        finally:
            if os.path.exists(srt_path):
                try:
                    os.remove(srt_path)
                    logger.debug(f"Cleaned up SRT file: {srt_path}")
                except Exception as e:
                    logger.warning(f"Error removing SRT: {str(e)}")