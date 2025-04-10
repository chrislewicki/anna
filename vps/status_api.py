from flask import Flask, request

app = Flask(__name__)
anna_online = False

@app.route("/api/anna/status", methods=["POST"])
def set_status():
    global anna_online
    data = request.get_json()
    anna_online = data.get("online", False)
    return {"status": "ok"}, 200

def is_model_online():
    print(f"[status_api] Returning anna_online = {anna_online}")
    return anna_online

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
