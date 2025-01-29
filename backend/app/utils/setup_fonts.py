import os
import urllib.request
import shutil
from typing import Dict, Optional

def download_file(url: str, output_path: str) -> bool:
    """Download a file from URL to the specified path."""
    try:
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        return False

def setup_fonts() -> None:
    """Download and setup required fonts."""
    # Get fonts directory path
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts')
    os.makedirs(fonts_dir, exist_ok=True)
    
    # Font URLs (update these with the correct URLs for your fonts)
    font_urls = {
        'NotoSans-Regular.ttf': 'https://github.com/notofonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf',
        'NotoSansHebrew-Regular.ttf': 'https://github.com/notofonts/noto-fonts/raw/main/hinted/ttf/NotoSansHebrew/NotoSansHebrew-Regular.ttf'
    }
    
    # Note: NotoSansCJK-Regular.ttc needs to be downloaded manually due to its large size
    
    print(f"Setting up fonts in: {fonts_dir}")
    
    for font_name, url in font_urls.items():
        font_path = os.path.join(fonts_dir, font_name)
        
        if os.path.exists(font_path):
            print(f"{font_name} already exists, skipping...")
            continue
            
        print(f"Downloading {font_name}...")
        if download_file(url, font_path):
            print(f"Successfully downloaded {font_name}")
        else:
            print(f"Failed to download {font_name}")
    
    # Special instructions for CJK font
    cjk_font_path = os.path.join(fonts_dir, 'NotoSansCJK-Regular.ttc')
    if not os.path.exists(cjk_font_path):
        print("\nNOTE: NotoSansCJK-Regular.ttc needs to be downloaded manually due to its large size.")
        print("Please download it from: https://github.com/googlefonts/noto-cjk/releases")
        print(f"And place it in: {fonts_dir}")
    
    print("\nFont setup complete!")
    print("Missing fonts (if any) need to be downloaded manually.")

if __name__ == "__main__":
    setup_fonts()