from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# تخزين مؤقت للّاعبين (في RAM)
players = {}

@app.route("/")
def index():
    return "Backend is running!"

# ✅ 1) Route لتأكيد صلاحية initData (Telegram WebApp)
@app.route("/api/validate_init_data", methods=["POST"])
def validate_init_data():
    """
    يطابق دليل تيليجرام الرسمي:
    - secret_key = SHA256(bot_token)
    - data_check_string = كل الأزواج key=value (بدون الحقل "hash") مرتبة أبجدياً ومفصولة بسطر جديد
    - user يتم تحويله لنص JSON دون مسافات
    - hash = HMAC_SHA256(secret_key, data_check_string) مكتوبة hex
    """
    import os, json, hmac, hashlib
    from dotenv import load_dotenv
    load_dotenv()
    try:
        payload = request.get_json(silent=True) or {}
        init_data = payload.get("init_data", "")
        if not init_data:
            return jsonify({"ok": False, "error": "missing init_data"}), 400

        bot_token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            return jsonify({"ok": False, "error": "missing BOT_TOKEN env"}), 500

        # نفك الـ querystring القادمة من WebApp.initData
        # مثال: query_id=...&user={"id":...}&auth_date=...&hash=...
        parts = {}
        for item in init_data.split("&"):
            if "=" not in item:
                continue
            k, v = item.split("=", 1)
            parts[k] = v

        received_hash = parts.pop("hash", None)
        if not received_hash:
            return jsonify({"ok": False, "error": "hash_not_found"}), 400

        # تطبيع user (لازم JSON دون مسافات)
        if "user" in parts:
            # بعض العملاء يمررون user URL-encoded؛ نفك التشفير إن لزم
            from urllib.parse import unquote
            raw_user = unquote(parts["user"])
            try:
                user_obj = json.loads(raw_user)
            except Exception:
                # لو كان أصلاً JSON صالح
                user_obj = json.loads(parts["user"])
            parts["user"] = json.dumps(user_obj, separators=(",", ":"))

        # data_check_string
        data_check_string = "\n".join(f"{k}={parts[k]}" for k in sorted(parts.keys()))

        # secret_key = sha256(bot_token)
        secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        is_valid = hmac.compare_digest(calc_hash, received_hash)

        return jsonify({
            "ok": True,
            "valid": is_valid,
            "user": json.loads(parts["user"]) if "user" in parts else None
        }), (200 if is_valid else 401)

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




@app.route("/api/game/save", methods=["POST"])
def save_game():
    try:
        data = request.get_json() or {}
        # TODO: خزّن البيانات بقاعدة البيانات بدل الذاكرة المؤقتة
        user_id = str((data.get("user") or {}).get("id") or data.get("user_id"))
        if not user_id:
            return jsonify({"ok": False, "error": "missing user_id"}), 400
        players[user_id] = data
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


