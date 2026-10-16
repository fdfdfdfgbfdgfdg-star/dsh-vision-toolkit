import mss
from PIL import Image
import sys
import os

def make_screenshot(output="screenshot.png", monitor=1):
    with mss.mss() as sct:
        # monitor=1 — первый монитор
        # можно указать region=(x, y, width, height)
        img = sct.grab(sct.monitors[monitor])
        mss.tools.to_png(img.rgb, img.size, output=output)
        return output

def make_screenshot_region(output="screenshot.png", region=None):
    """Сделать скриншот указанной области экрана.
    region = (left, top, width, height)"""
    with mss.mss() as sct:
        if region:
            img = sct.grab(region)
        else:
            img = sct.grab(sct.monitors[1])
        mss.tools.to_png(img.rgb, img.size, output=output)
        return output

def make_screenshot_window(output="screenshot.png", window_title=None):
    """Попытка сделать скриншот конкретного окна по заголовку.
    Требует pygetwindow: pip install pygetwindow"""
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            print(f"Окно с заголовком '{window_title}' не найдено")
            return None
        win = windows[0]
        region = (win.left, win.top, win.width, win.height)
        return make_screenshot_region(output, region)
    except ImportError:
        print("Для скриншота окна установите pygetwindow: pip install pygetwindow")
        return None

if __name__ == "__main__":
    # Создаем папку для скриншотов если её нет
    os.makedirs("temp/screenshots", exist_ok=True)
    
    path = sys.argv[1] if len(sys.argv) > 1 else "temp/screenshots/screenshot.png"
    
    # Если передан второй аргумент как номер монитора
    monitor = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    print(f"Создание скриншота: {path} (монитор {monitor})")
    result = make_screenshot(path, monitor)
    print(f"Готово: {result}")