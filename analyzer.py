"""Чтение книг и первый полезный показатель для формы F01."""

from collections import defaultdict
from io import BytesIO
from numbers import Real

from openpyxl import load_workbook

from detector import PROFILE_BY_CODE, detect, normalize
from student_report import student_report


def _display(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\n", " ")
    return text[:90] + ("…" if len(text) > 90 else "")


def _f01_chart(workbook) -> tuple[list[str], list[float], list[str]]:
    warnings = []
    totals = defaultdict(float)
    found_header = False
    for sheet in workbook.worksheets:
        month = trained = None
        for row_number, row in enumerate(sheet.iter_rows(min_row=1, max_row=min(sheet.max_row, 30), values_only=True), 1):
            names = [normalize(value) for value in row]
            month = next((i for i, value in enumerate(names) if value == "месяц"), None)
            trained = next((i for i, value in enumerate(names) if "фактически обученные" in value), None)
            if month is None or trained is None:
                continue
            found_header = True
            break
        if month is None or trained is None:
            continue
        for row in sheet.iter_rows(min_row=row_number + 1, values_only=True):
            if month >= len(row) or trained >= len(row):
                continue
            period = _display(row[month])
            value = row[trained]
            if not period or "итого" in normalize(period) or "всего" in normalize(period):
                continue
            if isinstance(value, Real) and not isinstance(value, bool):
                totals[period] += float(value)
    if not found_header:
        warnings.append("Не найдены столбцы «Месяц» и «Фактически обученные».")
    if found_header and not totals:
        warnings.append("В столбце обученных нет заполненных чисел для графика.")
    return list(totals), list(totals.values()), warnings


def analyze_file(filename: str, content: bytes, selected_code: str = "") -> dict:
    if not filename.lower().endswith(".xlsx"):
        raise ValueError("Нужен файл .xlsx")
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        # Осматриваем ограниченную область; личные записи не выводим на страницу.
        header_cells = []
        previews = []
        for sheet in workbook.worksheets:
            if sheet.max_row is None or sheet.max_column is None:
                sheet.calculate_dimension(force=True)
            rows = list(sheet.iter_rows(min_row=1, max_row=min(sheet.max_row, 10), max_col=min(sheet.max_column, 35), values_only=True))
            header_cells.extend(value for row in rows for value in row)
            previews.append({
                "name": sheet.title,
                "rows": sheet.max_row,
                "columns": sheet.max_column,
            })
        detected, score, candidates = detect(header_cells, workbook.sheetnames)
        profile = PROFILE_BY_CODE.get(selected_code) if selected_code else detected
        if selected_code and profile is None:
            raise ValueError("Неизвестный тип формы")
        result = {
            "filename": filename,
            "profile": profile,
            "automatic": not selected_code and detected is not None,
            "confidence": score,
            "candidates": [(code, PROFILE_BY_CODE[code].title, points) for code, points in candidates if points],
            "sheets": previews,
            "chart": None,
            "warnings": [],
            "students": None,
            "demo": any("демо" in normalize(sheet.cell(1, 1).value).split() for sheet in workbook.worksheets),
        }
        if profile and profile.code == "F01":
            labels, values, warnings = _f01_chart(workbook)
            result["warnings"].extend(warnings)
            if labels:
                result["chart"] = {"labels": labels, "values": values}
        elif profile and profile.code == "F02A":
            result["students"], warnings = student_report(workbook)
            result["warnings"].extend(warnings)
        elif profile:
            result["warnings"].append("Для этой формы график пока не реализован; показаны сведения о файле.")
        else:
            result["warnings"].append("Тип формы не удалось определить уверенно. Выберите его вручную и загрузите файл снова.")
        return result
    finally:
        workbook.close()
