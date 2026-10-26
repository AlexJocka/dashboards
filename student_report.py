"""Показатели сводной формы целевых студентов F02A."""

import math
from numbers import Real

from detector import normalize


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        try:
            value = float(value.replace("\u00a0", "").replace(" ", "").replace(",", "."))
        except ValueError:
            return None
    if isinstance(value, Real) and math.isfinite(value) and value >= 0:
        return float(value)
    return None


def student_report(workbook):
    records = []
    warnings = []
    found = False
    missing = 0
    numeric_keys = ("plan", "requested", "quota", "contracts", "within_quota", "outside_quota", "studying", "employed", "terminated", "graduates")
    for sheet in workbook.worksheets:
        header = None
        for i, row in enumerate(sheet.iter_rows(max_row=min(sheet.max_row, 30), max_col=19, values_only=True), 1):
            names = [normalize(v) for v in row]
            if "план приема" in names[9] and "целевых договоров" in names[12] and "образовательная организация" in names[4]:
                header = i
                break
        if header is None:
            continue
        found = True
        for row in sheet.iter_rows(min_row=header + 1, max_col=19, values_only=True):
            names = [normalize(v) for v in row]
            if any(v.startswith("справочно") for v in names):
                break
            # The template contains a subheader and a row of column numbers.
            if names[4] in ("", "5") or any(v.startswith(("итого", "всего")) for v in names[:5]):
                continue
            metrics = {key: _number(value) for key, value in zip(numeric_keys, row[9:19])}
            missing += sum(value is None and raw not in (None, "") for value, raw in zip(metrics.values(), row[9:19]))
            records.append({
                "university": str(row[4]).strip(),
                "year": str(row[2] or "Не указан").strip(),
                "program": str(row[8] or "Не указана").strip(),
                "specialty": str(row[6] or "Не указана").strip(),
                **metrics,
            })
    if not found:
        warnings.append("Не найдена шапка сводной формы F02A. Проверьте выбранный тип отчёта.")
    elif not records:
        warnings.append("В шаблоне нет заполненных строк отчёта. Справочники не включены в расчёты.")
    if missing:
        warnings.append(f"Некорректные числовые значения пропущены: {missing}.")
    return {"records": records}, warnings
