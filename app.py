"""Локальный черновик обработки Excel-отчётов."""

from zipfile import BadZipFile

from flask import Flask, redirect, render_template, request, url_for
from openpyxl.utils.exceptions import InvalidFileException

from analyzer import analyze_file
from detector import PROFILES


app = Flask(__name__)
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
                return redirect(url_for("dashboards"))
    return render_template("index.html", profiles=PROFILES, results=results, page_error=page_error)


@app.route("/dashboards")
def dashboards():
    return render_template("dashboards.html")


@app.errorhandler(413)
def too_large(_error):
    return render_template("index.html", profiles=PROFILES, results=[], page_error="Общий размер загрузки слишком большой."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
