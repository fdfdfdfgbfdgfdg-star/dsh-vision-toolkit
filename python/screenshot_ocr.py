import mss
from PIL import Image
import sys
import os
import pytesseract

# pytesseract needs tesseract binary - if not found, we'll use vision model
# We can set tesseract path explicitly if it's installed elsewhere
try:
    pytesseract.get_tesseract_version()
    print("Tesseract found")
except:
    print("Tesseract binary not found - will use vision model fallback")

def make_screenshot(output="screenshot.png", monitor=1):
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[monitor])
        mss.tools.to_png(img.rgb, img.size, output=output)
        return output

def ocr_image(image_path):
    """Распознать текст на изображении"""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='rus+eng')
        return text.strip()
    except Exception as e:
        return f"OCR ошибка: {e}"

def compress_image(input_path, output_path, max_size=(1280, 720), quality=85):
    """Сжать изображение перед отправкой в API"""
    with Image.open(input_path) as img:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img.save(output_path, 'PNG', optimize=True)
        return output_path

if __name__ == "__main__":
    os.makedirs("temp/screenshots", exist_ok=True)
    
    path = sys.argv[1] if len(sys.argv) > 1 else "temp/screenshots/screenshot.png"
    monitor = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    print(f"Создание скриншота: {path} (монитор {monitor})")
    result = make_screenshot(path, monitor)
    print(f"Готово: {result}")
    
    # OCR
    print("\nРаспознавание текста...")
    text = ocr_image(result)
    print(f"Текст: {text[:500]}...")
    
    # Сжатая версия для API
    compressed = result.replace('.png', '_compressed.png')
    compress_image(result, compressed)
    print(f"Сжато: {compressed}")