# -*- coding: utf-8 -*-
"""
UI Monitor - регулярные скриншоты экрана для визуальной проверки UI.

Использование:
  python ui_monitor.py once                # один скриншот + OCR
  python ui_monitor.py watch --interval 60 # регулярные скриншоты (каждые 60 сек)
  python ui_monitor.py diff a.png b.png    # сравнение двух скриншотов

Скриншоты сохраняются в temp/screenshots/, не удаляются (аудит).
OCR: Windows.Media.Ocr (встроенный, без квот и ключей).
"""
import sys
import os
import json
import time
import argparse
from datetime import datetime

SCREENSHOT_DIR = os.path.join("temp", "screenshots")
OCR_REPORT_DIR = os.path.join(SCREENSHOT_DIR, "ocr")

PS_OCR_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "win-ocr.ps1")


def make_screenshot(output=None, monitor=1):
    """Скриншот через mss."""
    import mss
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    if output is None:
        output = os.path.join(
            SCREENSHOT_DIR,
            "ui_{}.png".format(datetime.now().strftime("%Y%m%d_%H%M%S")),
        )
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[monitor])
        mss.tools.to_png(img.rgb, img.size, output=output)
    return output


def compress_image(input_path, max_size=(1280, 720)):
    """Сжать до max_size, сохранить рядом с суффиксом _compressed."""
    from PIL import Image
    output_path = input_path.replace(".png", "_compressed.png")
    with Image.open(input_path) as img:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img.save(output_path, "PNG", optimize=True)
    return output_path


def win_ocr(image_path, lang="ru-RU"):
    """OCR через встроенный Windows.Media.Ocr (powershell win-ocr.ps1)."""
    import subprocess
    result = subprocess.run(
        [
            "powershell", "-ExecutionPolicy", "Bypass",
            "-File", PS_OCR_SCRIPT,
            "-ImagePath", os.path.abspath(image_path),
            "-Lang", lang,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if result.returncode != 0:
        return None, (result.stderr or "OCR failed").strip()
    return result.stdout.strip(), None


def pixel_diff(img_a, img_b, threshold=16):
    """Попиксельное сравнение: доля различающихся пикселей."""
    from PIL import Image, ImageChops
    with Image.open(img_a) as a, Image.open(img_b) as b:
        if a.size != b.size:
            b = b.resize(a.size)
        diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
        hist = diff.convert("L").histogram()
        total = sum(hist)
        changed = sum(hist[threshold:])
        return changed / total if total else 0.0


def snapshot(tag="ui", do_ocr=True, do_compress=True):
    """Один цикл: скриншот -> OCR -> сжатие. Возвращает отчёт."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, "{}_{}.png".format(tag, timestamp))
    path = make_screenshot(path)

    report = {
        "timestamp": timestamp,
        "original": path,
        "size_bytes": os.path.getsize(path),
        "ocr_text": None,
        "ocr_error": None,
        "compressed": None,
    }

    if do_compress:
        try:
            report["compressed"] = compress_image(path)
        except Exception as e:
            report["compress_error"] = str(e)

    if do_ocr:
        text, err = win_ocr(report["compressed"] or path)
        report["ocr_text"] = text
        report["ocr_error"] = err
        # сохранить текст OCR рядом для аудита
        if text:
            os.makedirs(OCR_REPORT_DIR, exist_ok=True)
            txt_path = os.path.join(
                OCR_REPORT_DIR, "{}_{}.txt".format(tag, timestamp)
            )
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            report["ocr_file"] = txt_path

    return report


def main():
    parser = argparse.ArgumentParser(description="UI screenshot monitor")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_once = sub.add_parser("once", help="один снимок + OCR")
    p_once.add_argument("--tag", default="ui")
    p_once.add_argument("--no-ocr", action="store_true")
    p_once.add_argument("--no-compress", action="store_true")

    p_watch = sub.add_parser("watch", help="регулярные снимки")
    p_watch.add_argument("--interval", type=int, default=60)
    p_watch.add_argument("--tag", default="watch")
    p_watch.add_argument("--max", type=int, default=0, help="0 = бесконечно")
    p_watch.add_argument("--on-change", action="store_true",
                         help="OCR/сохранять только если экран изменился")

    p_diff = sub.add_parser("diff", help="сравнить два скриншота")
    p_diff.add_argument("image_a")
    p_diff.add_argument("image_b")

    args = parser.parse_args()

    if args.cmd == "once":
        r = snapshot(args.tag, not args.no_ocr, not args.no_compress)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        if r["ocr_text"]:
            print("\n--- OCR ---\n{}".format(r["ocr_text"][:1500]))

    elif args.cmd == "watch":
        prev_path = None
        count = 0
        print("watching: interval={}s on_change={}".format(
            args.interval, args.on_change))
        try:
            while True:
                if args.max and count >= args.max:
                    break
                path = make_screenshot()
                changed = True
                if args.on_change and prev_path:
                    ratio = pixel_diff(prev_path, path)
                    changed = ratio > 0.005
                    print("[{}] diff={:.4f} changed={}".format(
                        datetime.now().strftime("%H:%M:%S"), ratio, changed))
                if changed:
                    r = snapshot(args.tag)
                    print("[{}] saved {}{}".format(
                        datetime.now().strftime("%H:%M:%S"),
                        r["original"],
                        " (+OCR)" if r["ocr_text"] else ""))
                prev_path = path
                count += 1
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nstopped, {} iterations".format(count))

    elif args.cmd == "diff":
        ratio = pixel_diff(args.image_a, args.image_b)
        print("diff ratio: {:.6f} ({:.2f}%)".format(ratio, ratio * 100))


if __name__ == "__main__":
    main()
