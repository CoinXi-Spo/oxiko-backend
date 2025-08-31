from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json
import hmac
import hashlib
from urllib.parse import unquote

# تحميل متغيرات البيئة
load_dotenv()

app = Flask(__name__)
CORS(app)

# الاتصال بقاعدة البيانات MongoDB
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["game_db"]              # اسم قاعدة البيانات
players_collection = db["players"]  # اسم المجموعة

@app.route("/")
def index():
    return {"status": "MongoDB connected!", "message": "Backend is running!"}

# ================== 1) Route لتأكيد صلاحية initData ==================
@app.route("/api/validate_init_data", methods=["POST"])
def validate_init_data():
    try:
        payload = request.get_json(silent=True) or {}
        init_data = payload.get("init_data", "")
        print(f"Received init_data: {init_data}")

        if not init_data:
            return jsonify({"ok": False, "error": "missing init_data"}), 400

        bot_token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            return jsonify({"ok": False, "error": "missing BOT_TOKEN"}), 500

        # فك initData
        parts = {}
        for item in init_data.split("&"):
            if "=" not in item:
                continue
            k, v = item.split("=", 1)
            parts[k] = v

        received_hash = parts.pop("hash", None)
        if not received_hash:
            return jsonify({"ok": False, "error": "hash_not_found"}), 400

        # تطبيع user (JSON مضغوط)
        if "user" in parts:
            raw_user = unquote(parts["user"])
            try:
                user_obj = json.loads(raw_user)
            except Exception:
                user_obj = json.loads(parts["user"])
            parts["user"] = json.dumps(user_obj, separators=(",", ":"))

        # data_check_string
        data_check_string = "\n".join(f"{k}={parts[k]}" for k in sorted(parts.keys()))
        print(f"Data check string: {data_check_string}")

        # حساب hash
        secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        print(f"Calculated hash: {calc_hash}")

        is_valid = hmac.compare_digest(calc_hash, received_hash)

        return jsonify({
            "ok": True,
            "valid": is_valid,
            "user": json.loads(parts["user"]) if "user" in parts else None
        }), (200 if is_valid else 401)

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ================== 2) Route لإضافة لاعب جديد ==================
@app.route("/add_player", methods=["POST"])
def add_player():
    try:
        data = request.json
        player = {
            "username": data["username"],
            "score": data.get("score", 0),
            "user_id": data.get("user_id", data["username"])
        }
        players_collection.insert_one(player)
        player.pop("_id", None)  # إزالة _id من الاستجابة
        return jsonify({"message": "Player added!", "player": player})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================== 3) Route لحفظ بيانات اللاعب ==================
@app.route("/api/save_game_data", methods=["POST"])
def save_game_data():
    try:
        data = request.get_json(force=True)
        user_id = str(data.get("user_id"))
        if not user_id:
            return jsonify({"ok": False, "message": "Missing user_id"}), 400

        player_data = {
            "user_id": user_id,
            "username": data.get("username", "مجهول"),
            "level": data.get("level", 1),
            "health": data.get("health", 100),
            "energy": data.get("energy", 100),
        }
        
        players_collection.update_one(
            {"user_id": user_id},
            {"$set": player_data},
            upsert=True
        )
        
        return jsonify({"ok": True, "message": "Player data saved", "player": player_data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ================== 4) Route لجلب كل اللاعبين ==================
@app.route("/api/users", methods=["GET"])
def get_users():
    try:
        all_players = list(players_collection.find({}, {"_id": 0}))
        return jsonify({"ok": True, "players": all_players})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ================== 5) Route لحفظ بيانات اللعبة (game_data) ==================
@app.route("/api/game/save", methods=["POST"])
def save_game():
    try:
        data = request.get_json() or {}
        user_id = str((data.get("user") or {}).get("id") or data.get("user_id"))
        if not user_id:
            return jsonify({"ok": False, "error": "missing user_id"}), 400
        
        game_data = {
            "user_id": user_id,
            "game_data": data
        }
        
        players_collection.update_one(
            {"user_id": user_id},
            {"$set": game_data},
            upsert=True
        )
        
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ================== 6) Route لتقديم الفرونت إند ==================
@app.route("/game")
def serve_game():
    return jsonify({
        "message": "Game frontend should be served here",
        "frontend_url": "http://localhost:3000",
        "backend_url": "http://localhost:5002"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
