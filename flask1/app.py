"""Tasks API — CRUD задач на Flask.

Реализуйте функции по техническому заданию.
Все маршруты уже объявлены, тела функций пусты.
"""

from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify

app = Flask(__name__)

tasks = []
next_id = 1

MAX_TITLE_LEN = 200
DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 100



def now_iso():
    """Текущее время в ISO 8601 UTC."""
    return datetime.now(timezone.utc).isoformat()


def normalize(title):
    """Нормализация title для сравнения: схлопнуть пробелы + нижний регистр."""
    if not isinstance(title, str):
        return ""
    return " ".join(title.split()).lower()


def err(message, code):
    """JSON-ответ об ошибке: {"error": message} с заданным кодом."""
    return jsonify({"error": message}), code


def find_task(task_id):
    """Найти задачу по id или вернуть None."""
    for t in tasks:
        if t["id"] == task_id:
            return t
    return None


def title_exists(title, exclude_id=None):
    """Есть ли уже задача с таким title (с нормализацией)?

    exclude_id — id задачи, которую переименовываем.
    """
    norm_target = normalize(title)
    return any(
        normalize(t["title"]) == norm_target and t["id"] != exclude_id for t in tasks
    )


def validate_title(data, exclude_id=None):
    """Валидация title. Возвращает (title, None) или (None, error_response)."""
    if "title" not in data:
        return None, err("Поле title обязательно", 400)

    title_val = data["title"]
    if not isinstance(title_val, str) or not title_val.strip():
        return None, err("Название должно быть непустой строкой", 422)

    stripped_title = title_val.strip()
    if len(stripped_title) > MAX_TITLE_LEN:
        return None, err(f"Название не должно превышать {MAX_TITLE_LEN} символов", 422)

    if title_exists(stripped_title, exclude_id=exclude_id):
        return None, err("Задача с таким названием уже существует", 409)

    return stripped_title, None


def seed():
    """Заполнить хранилище демонстрационными задачами при старте."""
    global next_id, tasks
    tasks = []

    demo_tasks = [
        {"title": "Купить молоко", "done": True, "hours_ago": 5},
        {"title": "Выучить REST", "done": False, "hours_ago": 4},
        {"title": "Сдать лабораторную", "done": True, "hours_ago": 3},
        {"title": "Проверить почту", "done": False, "hours_ago": 2},
        {"title": "Позвонить маме", "done": False, "hours_ago": 1},
    ]

    now = datetime.now(timezone.utc)
    for i, item in enumerate(demo_tasks, start=1):
        task_time = now - timedelta(hours=item["hours_ago"])
        tasks.append(
            {
                "id": i,
                "title": item["title"],
                "done": item["done"],
                "created_at": task_time.isoformat(),
            }
        )
    next_id = 6


seed()

# ---------------------------------------------------------------------------
# Вьюхи
# ---------------------------------------------------------------------------


@app.get("/tasks")
def list_tasks():
    """GET /tasks — список с фильтрами, сортировкой и пагинацией."""
    done_param = request.args.get("done")
    if done_param is not None:
        if done_param.lower() == "true":
            done_filter = True
        elif done_param.lower() == "false":
            done_filter = False
        else:
            return err("Параметр done должен быть true или false", 400)
    else:
        done_filter = None

    q_filter = request.args.get("q")

    sort_by = request.args.get("sort", "created_at")
    if sort_by not in ["id", "title", "created_at"]:
        return err("Неверное поле сортировки sort", 400)

    order = request.args.get("order", "asc")
    if order not in ["asc", "desc"]:
        return err("Параметр order должен быть asc или desc", 400)

    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            raise ValueError
    except ValueError:
        return err("Параметр page должен быть целым числом >= 1", 400)

    try:
        per_page = int(request.args.get("per_page", DEFAULT_PER_PAGE))
        if not (1 <= per_page <= MAX_PER_PAGE):
            raise ValueError
    except ValueError:
        return err(
            f"Параметр per_page должен быть целым числом от 1 до {MAX_PER_PAGE}", 400
        )

    filtered_tasks = tasks.copy()
    if done_filter is not None:
        filtered_tasks = [t for t in filtered_tasks if t["done"] == done_filter]

    if q_filter:
        norm_q = normalize(q_filter)
        filtered_tasks = [t for t in filtered_tasks if norm_q in normalize(t["title"])]

    reverse_sort = order == "desc"
    if sort_by == "title":
        filtered_tasks.sort(key=lambda x: normalize(x["title"]), reverse=reverse_sort)
    else:
        filtered_tasks.sort(key=lambda x: x[sort_by], reverse=reverse_sort)

    total = len(filtered_tasks)
    pages = max(1, (total + per_page - 1) // per_page)

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    if start_idx >= total:
        items = []
    else:
        items = filtered_tasks[start_idx:end_idx]

    return (
        jsonify(
            {
                "items": items,
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": pages,
            }
        ),
        200,
    )


@app.get("/tasks/<int:task_id>")
def get_task(task_id):
    """GET /tasks/<id> — чтение одной задачи."""
    task = find_task(task_id)
    if not task:
        return err("задача не найдена", 404)
    return jsonify(task), 200


@app.post("/tasks")
def create_task():
    """POST /tasks — создание новой задачи."""
    global next_id
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return err("Тело запроса должно быть JSON-объектом", 400)

    title, error_resp = validate_title(data)
    if error_resp:
        return error_resp

    done = bool(data.get("done", False))
    if "done" in data and not isinstance(data["done"], bool):
        pass

    new_task = {"id": next_id, "title": title, "done": done, "created_at": now_iso()}
    tasks.append(new_task)
    next_id += 1
    return jsonify(new_task), 201


@app.put("/tasks/<int:task_id>")
def replace_task(task_id):
    """PUT /tasks/<id> — полная замена ресурса."""
    task = find_task(task_id)
    if not task:
        return err("задача не найдена", 404)

    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return err("Тело запроса должно быть JSON-объектом", 400)

    title, error_resp = validate_title(data, exclude_id=task_id)
    if error_resp:
        return error_resp

    done = bool(data.get("done", False))

    task["title"] = title
    task["done"] = done
    return jsonify(task), 200


@app.patch("/tasks/<int:task_id>")
def update_task(task_id):
    """PATCH /tasks/<id> — частичное обновление ресурса."""
    task = find_task(task_id)
    if not task:
        return err("задача не найдена", 404)

    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return err("Тело запроса должно быть JSON-объектом", 400)

    if "title" in data:
        title, error_resp = validate_title(data, exclude_id=task_id)
        if error_resp:
            return error_resp
        task["title"] = title

    if "done" in data:
        task["done"] = bool(data["done"])

    return jsonify(task), 200


@app.delete("/tasks/<int:task_id>")
def delete_task(task_id):
    """DELETE /tasks/<id> — удаление задачи."""
    global tasks
    task = find_task(task_id)
    if not task:
        return err("задача не найдена", 404)

    tasks = [t for t in tasks if t["id"] != task_id]
    return "", 204


@app.get("/")
def index():
    """GET / — служебный эндпоинт с описанием сервиса."""
    return (
        jsonify(
            {
                "service": "tasks-api",
                "seed": len(tasks),
                "endpoints": [
                    "GET / — описание сервиса",
                    "GET /tasks — получить список задач с фильтрацией, сортировкой и пагинацией",
                    "GET /tasks/<id> — получить конкретную задачу",
                    "POST /tasks — создать новую задачу",
                    "PUT /tasks/<id> — полностью перезаписать задачу",
                    "PATCH /tasks/<id> — частично обновить задачу",
                    "DELETE /tasks/<id> — удалить задачу",
                ],
            }
        ),
        200,
    )


if __name__ == "__main__":
    app.run(debug=True)
