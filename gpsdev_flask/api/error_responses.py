from flask import jsonify


def parse_ma_errors(e: dict) -> list:
    """Парсинг словаря с ошибками валидации схемы в список строк по типу:
    'Название поля: Ошибка'"""
    e_list = []
    for field, descriptions in e.items():
        for description in descriptions:
            e_list.append(f"{field}: {description}")
    return e_list


def not_found_404(detail: str | None = None):
    object_not_exists = {
        'status': '404',
        'title': 'not found',
        'detail': detail or "Запрошенная страница не существует"
    }
    return object_not_exists, 404


def validation_error_422(detail: dict | str):
    if isinstance(detail, dict):
        detail = parse_ma_errors(detail)
    error = {
        'status': '422',
        'title': 'validation error',
        'detail': [detail]
    }
    return jsonify(error), 422


def not_allowed_403(detail: str | None = None):
    error = {
        'status': '403',
        'title': 'not allowed',
        'detail': detail or "У вас нет прав для доступа к данному ресурсу"
    }
    return jsonify(error), 403


def report_error_422(e: str):
    error = {
        'status': '422',
        'title': 'report error',
        'detail': e
    }
    return jsonify(error), 422


def mts_error_422(e: str):
    error = {
        'status': '422',
        'title': 'mts error',
        'detail': e
    }
    return jsonify(error), 422
