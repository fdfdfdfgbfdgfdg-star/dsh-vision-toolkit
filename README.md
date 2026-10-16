# dsh-vision-toolkit — Система скриншотов для визуальной проверки UI (DeepSeek Harness)

Набор инструментов, позволяющий текстовому агенту DSH «видеть» экран:
регулярные скриншоты, OCR без квот и ключей, попиксельное сравнение и
интеграция с плагином dsh-vision-router.

## Быстрый старт

```sh
git clone https://github.com/fdfdfdfgbfdgfdg-star/dsh-vision-toolkit.git
cd dsh-vision-toolkit
pip install mss Pillow

# один снимок + OCR + сжатие
python ui_monitor.py once

# регулярный мониторинг (каждые 60 сек, сохранять только при изменении)
python ui_monitor.py watch --interval 60 --on-change

# сравнить два снимка
python ui_monitor.py diff a.png b.png
```

## Состав

| Файл | Назначение |
|---|---|
| `ui_monitor.py` | главная утилита: once / watch / diff |
| `win-ocr.ps1` | OCR через встроенный Windows.Media.Ocr (без ключей и квот) |
| `screenshot.py` | простой снимок экрана (mss) |
| `screenshot_ocr.py` | снимок + pytesseract (если установлен Tesseract) |
| `screenshot_tool.py` | расширенная утилита (region, workflow, base64) |

## Что установлено и настроено

### 1. dsh-vision-router v3.0.3 (плагин DSH)
- Установлен в профиль `web`: `dsh plugin --profile web add dsh-vision-router@latest`
- Включён `desktopScreenshot: true` (инструмент `vision_screenshot`) в
  `C:\Users\79881\.dsh\profiles\web\cordis.patch.yml`
- Встроенная бесплатная OVH vision-цепочка работает без API-ключа
- DSH Web перезапущен, конфигурация подтверждена через `--dump-config`

Инструменты плагина (доступны агенту в сессии при включённом 👁 Vision):
`vision_screenshot`, `vision_describe`, `vision_ground`, `vision_detect`,
`vision_crop`, `vision_pixel_diff`, `vision_colors`, `vision_ocr`,
`vision_present`, `vision_html_screenshot` и др.

### 2. Локальная цепочка (не зависит от провайдера)
- `screenshot.py` — простой скриншот (mss)
- `screenshot_ocr.py` — скриншот + pytesseract (бинарник Tesseract не установился
  из-за прав на C:\ProgramData — см. ниже)
- `screenshot_tool.py` — расширенная утилита (region, workflow, base64)
- `ui_monitor.py` — ГЛАВНАЯ утилита:
  - `once` — один снимок + OCR + сжатие + отчёт JSON
  - `watch --interval N [--on-change]` — регулярные снимки
  - `diff a.png b.png` — попиксельное сравнение
- `win-ocr.ps1` — OCR через встроенный Windows.Media.Ocr
  (без установки, без квот, без ключей) — основной рабочий путь

OCR-тексты сохраняются в `temp/screenshots/ocr/*.txt` для аудита.

## Регулярность (правила для агента)

1. После каждого изменения UI — `python ui_monitor.py once --tag <feature>`
2. После запуска сервера — снимок главной страницы
3. Перед отчётом о завершении — финальный снимок:
   `python ui_monitor.py once --tag final`
4. Регулярный мониторинг монтажа:
   `python ui_monitor.py watch --interval 60 --on-change`

## Провайдер и квоты

- `describe_image` (встроенная VLM): квота исчерпана (429 token_quota_exceeded) —
  работоспособность через VLM возобновится после сброса квоты.
- Независимый от провайдера путь: Windows OCR (`win-ocr.ps1`) — проверен,
  распознаёт интерфейсы (DSH Web GUI, веб-студия в Chrome).
- dsh-vision-router отправляет изображения на OVH анонимно (2 req/min на модель,
  5 моделей ≈ 10 RPM) — не зависит от квоты вашего API-ключа.

## Проверено

| Проверка | Результат |
|---|---|
| Установка плагина | ✓ dsh-vision-router 3.0.3 в профиле web |
| desktopScreenshot: true | ✓ подтверждён в composed config |
| DSH Web запуск с плагином | ✓ http://127.0.0.1:56816 |
| Тестовый скриншот (mss) | ✓ temp/screenshots/ |
| OCR встроенный Windows | ✓ текст интерфейса распознан |
| Сжатие (1280x720) | ✓ _compressed.png рядом с оригиналом |
| pixel diff (identical) | ✓ 0.00% |
| pixel diff (разные) | ✓ 53.36% |
| watch режим | ✓ 2 итерации, снимки + OCR |
| Скриншот приложения (студия в Chrome) | ✓ интерфейс распознан через OCR |

## Ограничения

- Tesseract-бинарник не установлен (chocolatey lock-файл в C:\ProgramData без
  прав администратора). Для установки: запустить от администратора
  `choco install tesseract -y` — но встроенный Windows OCR уже покрывает
  текстовый анализ без него.
- VLM-анализ (describe_image) временно недоступен: квота 50M токенов исчерпана.
  Альтернатива без квоты — OCR-текст + vision-цепочка dsh-vision-router (OVH).
