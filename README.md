# PDF Report Generator

CLI-скрипт на Python (uv), который принимает HTML-шаблон Jinja2 с placeholder'ами
и CSV-файл со значениями, и создаёт один или несколько PDF-отчётов.
Связь CSV ↔ шаблон — по naming convention: заголовки колонок CSV = имена
переменных `{{ var }}` в шаблоне. Поддерживает русский текст (кириллицу)
в данных, шаблоне, именах файлов и самом PDF.

## Требования

- Python >= 3.10 (управляется через uv)
- [uv](https://docs.astral.sh/uv/) — пакетный менеджер и раннер
- Системные библиотеки для WeasyPrint (Linux):
  ```bash
  sudo apt install libpango-1.0-0 libcairo2 libgdk-pixbuf-2.0-0
  ```
- Шрифты с поддержкой кириллицы (см. [Troubleshooting Cyrillic](#troubleshooting-cyrillic))

## Установка

```bash
git clone <repo>
cd pdf-report-generator
uv sync          # создаст .venv из pyproject.toml + uv.lock
```

Зависимости (`jinja2`, `weasyprint`, `click`, `rich`) управляются только через
`pyproject.toml` + `uv.lock`. `requirements.txt` не используется.

## Быстрый старт

```bash
uv run python -m pdf_report \
  --template examples/template.html \
  --data examples/data.csv \
  --out ./output \
  --filename-pattern "invoice_{invoice_number}_{index}.pdf" \
  --mode batch \
  --font-check
```

Результат (CSV из 5 строк данных):

```
output/invoice_INV-001_001.pdf
output/invoice_INV-002_002.pdf
output/invoice_INV-003_003.pdf
output/invoice_INV-004_004.pdf
output/invoice_INV-005_005.pdf
```

Один отчёт по конкретной строке:

```bash
uv run python -m pdf_report \
  --template examples/template.html \
  --data examples/data.csv \
  --out ./output \
  --filename-pattern "invoice_{invoice_number}_{index}.pdf" \
  --mode single --row 4
# → output/invoice_INV-004_004.pdf (ИП Петров)
```

## Опции CLI

| Опция | По умолчанию | Описание |
|---|---|---|
| `--template PATH` | — (обязательно) | HTML-шаблон Jinja2 (UTF-8) |
| `--data PATH` | — (обязательно) | CSV-файл (UTF-8, BOM допустим) |
| `--out DIR` | `./output` | Директория для PDF (создаётся автоматически) |
| `--filename-pattern TEXT` | `report_{index}.pdf` | Паттерн имени; токены `{col_name}` и обязательный `{index}` (1-based, ведущие нули до 3 знаков) |
| `--mode single\|batch` | `batch` | `batch` — PDF на каждую строку; `single` — один PDF по `--row` |
| `--row INTEGER` | `1` | Номер строки данных (1-based, пустые строки не считаются) для `single`; несовместим с `batch` |
| `--strict` | off | Падать (exit 1), если переменная шаблона отсутствует в CSV или поля строки не соответствуют заголовкам |
| `--font-check` | off | Проверить доступность шрифтов из `font-family` шаблона; только диагностика, не влияет на exit code |

Прочее поведение:
- Без `--strict` отсутствующие переменные подставляются как пустая строка.
- Полностью пустые строки CSV пропускаются; нумерация `{index}` идёт по непустым строкам.
- Недопустимые символы в именах файлов (`/ \ : * ? " < > |`) заменяются на `_`;
  кириллица в именах сохраняется как есть. Коллизии имён разрешаются суффиксами `_1`, `_2`, …
- Ошибка рендеринга одной строки в `batch` не роняет весь прогон (кроме `--strict`).
- `base_url` шаблона = директория файла шаблона, поэтому относительные пути
  к картинкам/CSS/шрифтам (`@font-face { src: url('fonts/…') }`) резолвятся корректно.

## Exit codes

- `0` — полный успех (в т.ч. `batch` при 0 строк данных: `No data rows, nothing to generate`)
- `1` — ошибки входа/валидации: нет файлов, `--row` вне диапазона или `< 1`,
  `--row` + `--mode batch`, паттерн без `{index}` или с неизвестным токеном,
  ошибки при `--strict`
- `2` — частичный успех в `batch` без `--strict` (некоторые PDF не созданы)

## Поддержка русского текста

Кириллица проходит весь пайплайн без перекодировок:
CSV читается как `utf-8-sig`, шаблон — как `utf-8`, Jinja2 и WeasyPrint
работают с Unicode-строками. В шаблоне обязательно `<meta charset="utf-8">`.

### Шрифты

WeasyPrint **молча** подставляет системный шрифт по умолчанию, если запрошенный
`font-family` недоступен — PDF отрисуется, но кириллица может превратиться
в «квадраты». Эталонный `examples/template.html` использует стек:

```css
body { font-family: "DejaVu Sans", "Liberation Sans", "Noto Sans", Arial, sans-serif; }
```

Все они покрывают кириллицу; WeasyPrint берёт первый доступный.

Варианты гарантии шрифта:
- **A (рекомендуется для Docker/CI):** положить `.ttf`/`.woff2` в `examples/fonts/`
  и подключить в шаблоне:
  ```css
  @font-face {
    font-family: "DejaVu Sans";
    src: url("fonts/DejaVuSans.ttf");
  }
  ```
- **B:** установить системные шрифты (см. ниже).

Скрипт не устанавливает и не подменяет шрифты автоматически — `--font-check`
только диагностирует и выводит `[WARN]` с рекомендацией.

## Troubleshooting Cyrillic

Симптом: вместо русского текста — квадраты, точки или пусто.

Причина: в системе нет шрифта с кириллицей, доступного WeasyPrint.

Решение (Debian/Ubuntu):

```bash
sudo apt install fonts-dejavu fonts-liberation fonts-noto
```

Проверка:

```bash
fc-list | grep -i "dejavu"   # должен показать DejaVu Sans
uv run python -m pdf_report --font-check ...   # [OK] / [WARN] по каждому семейству
```

Если шрифт установить нельзя (минимальный образ) — используйте `@font-face`
с локальным `.ttf` (вариант A выше).

Другие возможные причины:
- CSV сохранён не в UTF-8 (например, Windows-1251) → mojibake ещё до рендера.
  Пересохраните CSV в UTF-8.
- В шаблоне нет `<meta charset="utf-8">` при загрузке из файла без BOM.

## Структура проекта

```
pdf_report/
  __main__.py     # entry point: uv run python -m pdf_report
  cli.py          # click-команда, сборка Options
  types.py        # Options, RowData, ReportResult (dataclass)
  csv_reader.py   # парсинг CSV + валидация заголовков/строк
  template.py     # Jinja2 Environment, рендер, извлечение переменных
  naming.py       # генерация имён файлов, разрешение коллизий
  fonts.py        # проверка доступности шрифтов (--font-check)
  pdf.py          # WeasyPrint wrapper, batch/single
examples/
  template.html   # шаблон со стеком кириллических шрифтов
  data.csv        # данные с русскими значениями
tests/            # pytest: naming, csv_reader, template, fonts
```

## Тесты

```bash
uv run pytest
```

## Ограничения (out of scope)

Только плоские CSV (без массивов), один режим `single` = одна строка,
никаких JSON/XLSX, веб-интерфейса, Docker-образа, сетевых шаблонов,
кастомных Jinja-фильтров и автоустановки шрифтов.
