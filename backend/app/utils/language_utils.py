import os
from langdetect import detect
from typing import Optional

# Define language sets
RTL_LANGUAGES = {'ar', 'he', 'fa', 'ur'}
CJK_LANGUAGES = {'zh', 'ja', 'ko'}
LANGUAGE_NAME_MAP = {
    'english': 'en',
    'hebrew': 'he',
    'arabic': 'ar',
    'chinese': 'zh',
    'japanese': 'ja',
    'korean': 'ko',
    'french': 'fr',
    'spanish': 'es',
    'german': 'de',
    'russian': 'ru',
    'hindi': 'hi'
}

def normalize_lang_code(lang: str) -> str:
    """
    Normalize language names and codes to ISO 639-1 format.
    
    Args:
        lang (str): Input language name or code
        
    Returns:
        str: Normalized 2-letter language code
    """
    lang = lang.strip().lower()
    
    # Check if it's already a valid 2-letter code
    if len(lang) == 2 and lang in LANGUAGE_NAME_MAP.values():
        return lang
    
    # Check if it's a locale code (e.g. en-US)
    if '-' in lang:
        lang = lang.split('-')[0]
    
    # Map common language names to codes
    return LANGUAGE_NAME_MAP.get(lang, lang)

def is_rtl_language(lang_code: str) -> bool:
    """
    Check if a language code represents a right-to-left language.
    """
    return normalize_lang_code(lang_code) in RTL_LANGUAGES

def get_font_path(lang_code: str) -> str:
    """
    Get the appropriate font path for a given language code.
    """
    normalized_code = normalize_lang_code(lang_code)
    fonts_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts')
    
    if not os.path.exists(fonts_dir):
        raise FileNotFoundError(f"Fonts directory not found: {fonts_dir}")

    font_map = {
        'he': 'NotoSansHebrew-Regular.ttf',
        'ar': 'NotoSansArabic-Regular.ttf',
        'zh': 'NotoSansSC-Regular.otf',
        'ja': 'NotoSansJP-Regular.otf',
        'ko': 'NotoSansKR-Regular.otf'
    }
    
    font_file = font_map.get(normalized_code, 'NotoSans-Regular.ttf')
    font_path = os.path.join(fonts_dir, font_file)
    
    if not os.path.exists(font_path):
        default_path = os.path.join(fonts_dir, 'NotoSans-Regular.ttf')
        if os.path.exists(default_path):
            return default_path
        raise FileNotFoundError(f"Font file not found: {font_path}")
    
    return font_path

def detect_language(text: str) -> str:
    """
    Detect the language of a given text.
    """
    if not text or not isinstance(text, str):
        return 'en'
        
    try:
        detected = detect(text)
        return normalize_lang_code(detected)
    except Exception as e:
        print(f"Language detection failed: {str(e)}")
        return 'en'

def verify_fonts_exist() -> bool:
    """
    Verify that all required font files exist.
    """
    fonts_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts')
    required_fonts = [
        'NotoSans-Regular.ttf',
        'NotoSansHebrew-Regular.ttf',
        'NotoSansArabic-Regular.ttf',
        'NotoSansSC-Regular.otf',
        'NotoSansJP-Regular.otf',
        'NotoSansKR-Regular.otf'
    ]
    
    missing = [font for font in required_fonts if not os.path.exists(os.path.join(fonts_dir, font))]
    if missing:
        print(f"Missing fonts: {', '.join(missing)}")
        return False
    return True

def init_fonts() -> None:

    fonts_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts')
    
    try:
        os.makedirs(fonts_dir, exist_ok=True)
        if not verify_fonts_exist():
            print("Required fonts missing. Please install:")
            print("- Noto Sans (Regular)")
            print("- Noto Sans Hebrew")
            print("- Noto Sans Arabic")
            print("- Noto Sans CJK fonts")
            print(f"Copy to: {fonts_dir}")
    except Exception as e:
        print(f"Font initialization error: {str(e)}")
        raise

# Additional validation on import
init_fonts()