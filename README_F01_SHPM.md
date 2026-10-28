# Интеграция F01 (ШПМ) с Matri006/dashboards

## Установка

1. В корень клона репозитория добавить `reports/f01_otchet_po_obucheniyu_shpm.py` и `reports/__init__.py` (если отсутствует). Обновить существующий `analyzer.py`: перенести изменения для F01. Не перезаписывайте новый `analyzer.py` коллег полным файлом без проверки различий.
2. Не менять `detector.py` / `app.py` / HTML. Используется существующая зависимость `openpyxl`.
3. Вызов из текущего Flask сохраняется: `analyze_file(filename, content, selected_code='F01')`.
4. Новый результат в `result['analytics']`: `report_id`, `status`, `kpi`, `charts`, `tables`, `data_quality`, `warnings`.
5. Старый `result['chart']` по-прежнему содержит `labels` / `values` по завершившим обучение, только для месяцев с числом. В пустой форме он `None`.

## Проверка без Flask

```bash
python -m pip install openpyxl
python -m unittest discover -s tests -v
```

Тест берёт `SHPM_TEST_XLSX` из переменной среды (путь к оригинальному XLSX). Если не задан, тестируется синтетическая форма, созданная в памяти.

## Договор с веб-командой

`result['analytics']['charts']` описывает графики, а не готовые изображения. Серии содержат `None` для пропусков, не подменять нулём. `result['analytics']['tables'][0]['rows']` содержит строки программ по месяцам.

Ограничения: распознавание в `detector.py` может потребовать ручного выбора F01, если автоматическое определение неоднозначно. `openpyxl(data_only=True)` читает сохранённые значения формул, не пересчитывает их. Схема строго проверяет исходный шаблон (7 месяцев × 3 программы).

## Почему `analyzer.py` и `reports/__init__.py` не переименованы

- `analyzer.py` — общий модуль, на который уже ссылается `app.py`; он не относится исключительно к F01. Для интеграции отчёта F01 в нём нужен импорт `from reports.f01_otchet_po_obucheniyu_shpm import analyze_shpm` и вызов обработчика.
- `reports/__init__.py` — служебное имя Python для пакета.
- `tests/test_f01_otchet_po_obucheniyu_shpm.py` — тесты конкретно этой формы.

В архиве **нет XLSX с данными сотрудников**.
