"""Осторожное распознавание форм по содержимому, а не по имени файла."""

import re
from dataclasses import dataclass
from typing import Iterable


def normalize(value: object) -> str:
    if value is None:
        return ""
    text = str(value).lower().replace("ё", "е")
    return " ".join(re.findall(r"[a-zа-я0-9]+", text))


@dataclass(frozen=True)
class Profile:
    code: str
    title: str
    clues: tuple[str, ...]
    sheet_clues: tuple[str, ...] = ()


PROFILES = (
    Profile("F01", "Обучение по программе ШПМ", ("программа обучения", "количество часов", "фактически обученные")),
    Profile("F02A", "Целевые студенты: свод", ("план приема", "количество квот", "целевых договоров")),
    Profile("F02B", "Целевые студенты: месячная форма", ("контингент студентов", "расторгнутых договоров", "целевом обучении")),
    Profile("F03A", "Студенты образовательных треков", ("образовательная организация", "фио студента"), ("запрос с предприятий",)),
    Profile("F03B", "Целевые студенты: реестр обучения", ("вид целевого обучения", "статус студента", "средний балл аттестата")),
    Profile("F04A", "Статус инженерных классов", ("инженерных классов", "образовательная организация партнер"), ("профориентация", "мто")),
    Profile("F04B", "Реестр наставников", ("фио наставника", "фио студента"), ("реестр наставников",)),
    Profile("F05A", "Федеральный проект: многолистовая форма", ("контингент обучающихся", "целевых договоров", "трудоустроенных студентов"), ("данные по организациям",)),
    Profile("F05B", "Обучение персонала", ("отчет по обучению рабочих", "категория персонала"), ("месячная форм по рабочим",)),
    Profile("F06B", "Профориентационные мероприятия", ("количество школьников участников", "план", "факт")),
    Profile("F07A", "Информационные мероприятия", ("инструменты распространения информации", "наименование организации одк")),
    Profile("F07B", "Мультиквалифицированные специалисты", ("мультиквалифицированных специалистов", "2025 чел"), ("выпуск мкс",)),
    Profile("F08", "Федеральный проект: краткая форма", ("контингент обучающихся", "целевых договоров", "трудоустроенных студентов")),
    Profile("F09", "Мероприятия с молодёжью", ("количество участников", "плановые", "фактические", "плановый руб")),
    Profile("F10", "Движение персонала до 35 лет", ("движении работников", "возрасте до 35 лет", "среднесписочная численность")),
    Profile("F11", "Статус проекта 2", ("образовательная организация партнер", "количество обучающихся", "количество оборудования")),
    Profile("F12", "Родственники и профильный ЕГЭ", ("родственниках", "профильные егэ")),
    Profile("FEX", "Вспомогательная сводка обучения", ("программа обучения",), ("2025",)),
)

PROFILE_BY_CODE = {profile.code: profile for profile in PROFILES}


def detect(cells: Iterable[object], sheet_names: Iterable[str]) -> tuple[Profile | None, int, list[tuple[str, int]]]:
    """Возвращает профиль лишь при достаточно явном и однозначном совпадении."""
    cell_texts = [normalize(value) for value in cells if value is not None]
    sheets = [normalize(name) for name in sheet_names]
    scores = []
    for profile in PROFILES:
        hits = sum(any(normalize(clue) in text for text in cell_texts) for clue in profile.clues)
        sheet_hits = sum(any(normalize(clue) in sheet for sheet in sheets) for clue in profile.sheet_clues)
        # Многолистовая форма F05A и краткая F08 имеют схожие поля.
        if profile.code == "F05A" and not sheet_hits:
            scores.append((profile.code, 0))
            continue
        scores.append((profile.code, hits * 2 + sheet_hits * 3))
    scores.sort(key=lambda item: item[1], reverse=True)
    best_code, best_score = scores[0]
    second_score = scores[1][1]
    # Нужны хотя бы два содержательных признака и заметный отрыв.
    if best_score < 4 or best_score - second_score < 2:
        return None, best_score, scores[:3]
    return PROFILE_BY_CODE[best_code], best_score, scores[:3]
