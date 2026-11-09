from flask import Flask, request, jsonify

app = Flask(__name__)

tasks = [ 
    {"id": 1, "title": "Выучить REST", "done": False},
    {"id": 2, "title": "Разобраться с Flask", "done": False},
    {"id": 3, "title": "Настроить виртуальное окружение", "done": True},
]

next_id = max(t["id"] for t in tasks) + 1


@app.get("/tasks")                       # Read (список)
def list_tasks():
    return jsonify(tasks), 200


@app.get("/tasks/<int:task_id>")         # Read (одна)
def get_task(task_id):
    for t in tasks:
        if t["id"] == task_id:
            return jsonify(t), 200
    return jsonify({"error": "не найдено"}), 404


@app.post("/tasks")                      # Create
def create_task():
    global next_id
    data = request.get_json(silent=True) or {}
    task = {"id": next_id, "title": data.get("title", ""), "done": False}
    tasks.append(task)
    next_id += 1
    return jsonify(task), 201


@app.patch("/tasks/<int:task_id>")       # Update
def update_task(task_id):
    for t in tasks:
        if t["id"] == task_id:
            t.update(request.get_json(silent=True) or {})
            return jsonify(t), 200
    return jsonify({"error": "не найдено"}), 404


@app.delete("/tasks/<int:task_id>")      # Delete
def delete_task(task_id):
    global tasks
    tasks = [t for t in tasks if t["id"] != task_id]
    return "", 204


if __name__ == "__main__":
    app.run(debug=True)