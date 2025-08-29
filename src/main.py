from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# تخزين مؤقت للّاعبين (في RAM)
players = {}

@app.route("/")
def index():
    return "Backend is running!"

# ✅ 1) Route لتأكيد صلاحية initData
@app.route("/api/validate_init_data", methods=["POST"])
def validate_init_data():
    try:
        data = request.get_json(force=True)
        init_data = data.get("initData", "")
        if not init_data:
            return jsonify({"ok": False, "message": "Missing initData"}), 400

        # هنا تقدر تعمل تحقق من initData (اختياري)
        return jsonify({"ok": True, "message": "initData is valid", "initData": init_data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ✅ 2) Route لحفظ بيانات اللاعب
@app.route("/api/save_game_data", methods=["POST"])
def save_game_data():
    try:
        data = request.get_json(force=True)
        user_id = str(data.get("user_id"))
        if not user_id:
            return jsonify({"ok": False, "message": "Missing user_id"}), 400

        # حفظ أو تحديث بيانات اللاعب
        players[user_id] = {
            "username": data.get("username", "مجهول"),
            "level": data.get("level", 1),
            "health": data.get("health", 100),
            "energy": data.get("energy", 100),
        }
        return jsonify({"ok": True, "message": "Player data saved", "player": players[user_id]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ✅ 3) Route لجلب كل اللاعبين
@app.route("/api/users", methods=["GET"])
def get_users():
    try:
        return jsonify({"ok": True, "players": players})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


