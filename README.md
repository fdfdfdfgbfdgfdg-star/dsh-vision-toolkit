# dsh-vision-toolkit

**Eyes for text-only DeepSeek Harness agents on Windows — fully local, no API keys, no quotas, no Python.**

Устанавливается как обычный DSH-плагин (через поле «установить плагин» по ссылке на этот репозиторий) и регистрирует четыре инструмента агента:

| Инструмент | Что делает |
|---|---|
| `ui_screenshot` | DPI-aware снимок всего экрана Windows → PNG в `temp/screenshots/` + опциональный OCR |
| `ui_ocr` | Распознавание текста на любом изображении через встроенный Windows.Media.Ocr |
| `ui_diff` | Попиксельное сравнение двух изображений (доля и % изменений) |
| `ui_screen_check` | Одним вызовом: снимок экрана + OCR + отчёт (для финальной проверки перед отчётом о завершении) |

Все операции выполняются локально: скриншот через PowerShell + System.Drawing (с учётом per-monitor DPI), OCR через встроенный движок Windows, сравнение через LockBits. Ничего не отправляется в сеть — плагин не зависит от квот vision-моделей и API-ключей.

## Установка

```
dsh plugin --profile <profile> add github:fdfdfdfgbfdgfdg-star/dsh-vision-toolkit
```

или вставьте в поле установки плагина в GUI:

```
https://github.com/fdfdfdfgbfdgfdg-star/dsh-vision-toolkit
```

Перезапустите DSH после установки.

## Использование агентом

```
ui_screenshot                          # снимок + OCR (ru-RU) + сохранение в temp/screenshots/
ui_screenshot filename="login.png" ocr=false
ui_ocr image="temp/screenshots/ui_xxx.png" lang="en-US"
ui_diff image_a="ref.png" image_b="now.png" threshold=16
ui_screen_check                        # финальная проверка: снимок + OCR
```

Правила регулярности (рекомендуется добавить в системный промпт агента):
1. После каждого изменения UI — `ui_screenshot`.
2. После запуска сервера — снимок главной страницы.
3. Перед отчётом о завершении — `ui_screen_check`.
4. Скриншоты не удалять — они служат аудиторским следом.

## Регулярный мониторинг (Python, опционально)

В `python/` лежит автономная утилита `ui_monitor.py` (требует `pip install mss Pillow`):

```
python python/ui_monitor.py once                      # один цикл: снимок + OCR + сжатие
python python/ui_monitor.py watch --interval 60 --on-change  # мониторинг каждые 60 с
python python/ui_monitor.py diff a.png b.png          # сравнение
```

## Состав репозитория

```
index.js            — плагин: регистрация инструментов через ctx.tools.register
cordis.patch.yml    — bundle-patch для монтирования плагина в профиль
scripts/capture.ps1 — DPI-aware захват виртуального экрана (System.Drawing)
scripts/ocr.ps1     — Windows.Media.Ocr (без установки, без ключей)
scripts/diff.ps1    — попиксельное сравнение
python/             — автономные Python-утилиты (опционально)
```

## Требования

- Windows с PowerShell (встроенный)
- DSH Host ≥ 0.1.5
- Для OCR: языковой пакет распознавания (ru-RU или en-US; обычно уже установлен в Windows)

## Лицензия

MIT
