"""
Универсальная утилита для скриншотов экрана с поддержкой:
1. Python mss (работает везде)
2. dsh-vision-router vision_screenshot (через DSH)
3. OCR через pytesseract (если есть Tesseract)
4. Анализ через vision-модель
"""
import mss
from PIL import Image
import sys
import os
import json
import base64
import subprocess
import pytesseract
from datetime import datetime

SCREENSHOT_DIR = "temp/screenshots"

def ensure_dir():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def make_screenshot_mss(output=None, monitor=1, region=None):
    """Скриншот через mss (Python)"""
    ensure_dir()
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = os.path.join(SCREENSHOT_DIR, f"screen_{timestamp}.png")
    
    with mss.mss() as sct:
        if region:
            img = sct.grab(region)
        else:
            img = sct.grab(sct.monitors[monitor])
        mss.tools.to_png(img.rgb, img.size, output=output)
    return output

def make_screenshot_dsh_vision(output=None):
    """Скриншот через dsh-vision-router (требует запущенный DSH Web)"""
    ensure_dir()
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = os.path.join(SCREENSHOT_DIR, f"screen_dsh_{timestamp}.png")
    
    # Используем dsh CLI для вызова vision_screenshot
    try:
        result = subprocess.run([
            "dsh", "web", "--no-open", "--port", "0"
        ], capture_output=True, text=True, timeout=10)
        # Это не сработает напрямую - нужен API вызов
        print("Для vision_screenshot нужен запущенный DSH Web с включенным desktopScreenshot")
        return None
    except Exception as e:
        print(f"DSH vision screenshot недоступен: {e}")
        return None

def compress_image(input_path, output_path=None, max_size=(1280, 720)):
    """Сжать изображение для API"""
    if output_path is None:
        output_path = input_path.replace('.png', '_compressed.png')
    
    with Image.open(input_path) as img:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img.save(output_path, 'PNG', optimize=True)
    return output_path

def ocr_image(image_path):
    """OCR через pytesseract"""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='rus+eng')
        return text.strip()
    except Exception as e:
        return f"OCR ошибка: {e}"

def image_to_base64(image_path):
    """Конвертировать изображение в base64 для API"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def analyze_with_vision_model(image_path, question="Что на этом скриншоте? Опиши интерфейс подробно."):
    """
    Анализ изображения через vision-модель.
    Требует настройки API ключа для vision провайдера.
    """
    # Это заглушка - реальный вызов будет через API
    print(f"Анализ через vision модель: {question}")
    print(f"Изображение: {image_path}")
    return "Vision анализ требует настроенного API"

def full_screenshot_workflow(output=None, monitor=1, do_ocr=True, do_compress=True, analyze=False):
    """Полный workflow: скриншот -> OCR -> сжатие -> анализ"""
    print(f"=== Screenshot workflow ===")
    
    # 1. Screenshot
    path = make_screenshot_mss(output, monitor)
    print(f"[OK] Screenshot: {path}")
    
    # 2. OCR
    if do_ocr:
        text = ocr_image(path)
        print(f"[OK] OCR text ({len(text)} chars): {text[:200]}...")
    
    # 3. Compress
    compressed_path = None
    if do_compress:
        compressed_path = compress_image(path)
        print(f"[OK] Compressed: {compressed_path}")
    
    # 4. Analyze
    if analyze:
        analysis = analyze_with_vision_model(compressed_path or path)
        print(f"[OK] Analysis: {analysis}")
    
    return {
        "original": path,
        "compressed": compressed_path,
        "ocr_text": text if do_ocr else None,
        "size_original": os.path.getsize(path),
        "size_compressed": os.path.getsize(compressed_path) if compressed_path else None
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Скриншот утилита для визуальной проверки UI")
    parser.add_argument("output", nargs="?", help="Путь для сохранения")
    parser.add_argument("-m", "--monitor", type=int, default=1, help="Номер монитора")
    parser.add_argument("--no-ocr", action="store_true", help="Пропустить OCR")
    parser.add_argument("--no-compress", action="store_true", help="Не сжимать")
    parser.add_argument("--analyze", action="store_true", help="Анализировать через vision")
    parser.add_argument("--region", nargs=4, type=int, metavar=("L", "T", "W", "H"), help="Область экрана")
    parser.add_argument("--workflow", action="store_true", help="Запустить полный workflow")
    
    args = parser.parse_args()
    
    if args.workflow:
        result = full_screenshot_workflow(
            args.output, args.monitor, 
            do_ocr=not args.no_ocr, 
            do_compress=not args.no_compress,
            analyze=args.analyze
        )
        print(f"\nРезультат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    else:
        ensure_dir()
        output = args.output or os.path.join(SCREENSHOT_DIR, f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        region = tuple(args.region) if args.region else None
        
        path = make_screenshot_mss(output, args.monitor, region)
        print(f"Готово: {path}")
        
        if not args.no_ocr:
            text = ocr_image(path)
            print(f"OCR: {text[:500]}")
        
        if not args.no_compress:
            compressed = compress_image(path)
            print(f"Сжато: {compressed}")