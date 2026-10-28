"""Локальный черновик обработки Excel-отчётов."""

from zipfile import BadZipFile
from pathlib import Path
import os
from secrets import token_hex

from flask import Flask, redirect, render_template, request, url_for, session, send_file
from openpyxl.utils.exceptions import InvalidFileException

from analyzer import analyze_file
from detector import PROFILES
import report_store


app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARDS_SECRET_KEY") or token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
DEMO_FILE = Path(__file__).parent / "examples" / "Зафарова_демо.xlsx"
app.config["MAX_CONTENT_LENGTH"] = 210 * 1024 * 1024
MAX_FILES = 20
MAX_FILE_SIZE = 10 * 1024 * 1024


@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    page_error = None
    if request.method == "POST":
        files = [file for file in request.files.getlist("files") if file.filename]
        selected_code = request.form.get("form_type", "")
        if len(files) > MAX_FILES:
            page_error = f"Можно загрузить не более {MAX_FILES} файлов за раз."
        elif not files:
            page_error = "Выберите хотя бы один Excel-файл."
        else:
            for file in files:
                try:
                    content = file.read(MAX_FILE_SIZE + 1)
                    if len(content) > MAX_FILE_SIZE:
                        raise ValueError("Файл больше 10 МБ")
                    result = analyze_file(file.filename, content, selected_code)
                    results.append(result)
                except (ValueError, InvalidFileException, BadZipFile, OSError, KeyError):
                    results.append({"filename": file.filename, "error": "Не удалось прочитать файл. Проверьте, что это исправная книга .xlsx."})
            if results and all(result.get("profile") and result["profile"].code != "FEX" for result in results):
                session["report_key"] = report_store.save(results)
                return redirect(url_for("dashboards"))
    return render_template("index.html", profiles=PROFILES, results=results, page_error=page_error)


@app.route("/dashboards")
def dashboards():
    return render_template("dashboards.html", reports=current_reports(), active="students")


def current_reports():
    results = report_store.get(session.get("report_key"))
    return [{"filename": r["filename"], "code": r["profile"].code,
                "title": r["profile"].title, "demo": r.get("demo", False),
                "students": r.get("students"), "chart": r.get("chart"),
                "analytics": r.get("analytics"),
                "sheets": r["sheets"], "warnings": r["warnings"]} for r in results]


@app.get("/summary")
def summary():
    reports = current_reports()
    return render_template("summary.html", reports=reports, active="summary",
                           warning_count=sum(len(r["warnings"]) for r in reports))


@app.get("/training")
def training():
    reports = [r for r in current_reports() if r["code"] == "F01"]
    return render_template("dashboards.html", reports=reports, active="training")


@app.get("/data-quality")
def quality():
    return render_template("quality.html", reports=current_reports(), active="quality")


@app.post("/demo")
def demo():
    result = analyze_file(DEMO_FILE.name, DEMO_FILE.read_bytes())
    session["report_key"] = report_store.save([result])
    return redirect(url_for("dashboards"))


@app.get("/demo/download")
def download_demo():
    return send_file(DEMO_FILE, as_attachment=True, download_name=DEMO_FILE.name)


@app.errorhandler(413)
def too_large(_error):
    return render_template("index.html", profiles=PROFILES, results=[], page_error="Общий размер загрузки слишком большой."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
