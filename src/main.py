import os
import sys
import sqlite3
import hashlib
import hmac
import json
from urllib.parse import parse_qs
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, origins="*")

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'game.db')

# In-memory users list for battle club
users = [
    {"id": 1, "name": "لاعب تجريبي 1", "level": 10, "power": 1000},
    {"id": 2, "name": "لاعب تجريبي 2", "level": 15, "power": 1500},
    {"id": 3, "name": "محارب الظلام", "level": 20, "power": 2000},
    {"id": 4, "name": "ملك الساحة", "level": 25, "power": 2500},
]

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def validate_telegram_init_data(init_data, bot_token):
    """Validate Telegram initData"""
    try:
        secret_key = hmac.new("WebAppData".encode(), bot_token.encode(), hashlib.sha256).digest()
        params = parse_qs(init_data)
        
        # Extract hash
        hash_value = params.get('hash', [None])[0]
        if not hash_value:
            return False
            
        # Remove hash from params
        del params['hash']
        
        # Create data check string
        data_check_string = '\n'.join([f"{k}={v[0]}" for k, v in sorted(params.items())])
        
        # Calculate HMAC
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return calculated_hash == hash_value
    except Exception:
        return False

# Error handlers
@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"ok": False, "error": "Method not allowed"}), 405

@app.errorhandler(404)
def not_found(e):
    return jsonify({"ok": False, "error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"ok": False, "error": "Internal server error"}), 500

# ✅ API Routes with correct methods

@app.route('/api/validate_init_data', methods=['POST'])
def validate_init_data():
    """Validate Telegram initData"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ok": False, "error": "No JSON received"}), 400
            
        init_data = data.get('initData')
        if not init_data:
            return jsonify({"ok": False, "error": "Missing initData"}), 400
            
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            # Return success for test mode when no token is configured
            return jsonify({"ok": True, "message": "initData is valid (test mode)"}), 200
            
        is_valid = validate_telegram_init_data(init_data, bot_token)
        
        if not is_valid:
            return jsonify({"ok": False, "error": "Invalid initData"}), 403
            
        return jsonify({"ok": True, "message": "initData is valid"}), 200
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/save_game_data', methods=['POST'])
def save_game_data():
    """Save game data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ok": False, "error": "No JSON received"}), 400
            
        # Here you can save the game data to database
        # For now, just return success
        return jsonify({"ok": True, "message": "Game data saved successfully"}), 200
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/users', methods=['GET', 'POST'])
def handle_users():
    """Handle users - GET to retrieve, POST to add"""
    global users
    
    if request.method == 'GET':
        return jsonify(users), 200
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON received"}), 400
                
            new_user = {
                "id": len(users) + 1,
                "name": data.get("name", "مجهول"),
                "level": data.get("level", 1),
                "power": data.get("power", 100)
            }
            users.append(new_user)
            return jsonify(new_user), 201
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# Public routes (keeping existing structure)
@app.route('/api/public/validate_init_data', methods=['POST'])
def public_validate_init_data():
    """Public validate Telegram initData"""
    return validate_init_data()

@app.route('/api/public/register', methods=['POST'])
def register_player():
    """Register new player"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON received"}), 400
            
        username = data.get('username')
        telegram_id = data.get('telegram_id')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO players (username, telegram_id, oxy_balance, ko_balance) VALUES (?, ?, 0, 0)",
                (username, telegram_id)
            )
            player_id = cursor.lastrowid
            conn.commit()
            
            # Airdrop for new player (simplified)
            cursor.execute(
                "UPDATE players SET oxy_balance = 1000000000000000000, ko_balance = 50000000000000000000 WHERE id = ?",
                (player_id,)
            )
            conn.commit()
            
            return jsonify({
                "message": "Player registered and airdropped",
                "player_id": player_id
            }), 200
            
        except sqlite3.IntegrityError:
            return jsonify({"error": "Username or Telegram ID already exists"}), 409
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/public/balance/<username>', methods=['GET'])
def get_player_balance(username):
    """Get player balance"""
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM players WHERE username = ?", (username,))
            player = cursor.fetchone()
            
            if not player:
                return jsonify({"error": "Player not found"}), 404
                
            return jsonify({
                "username": player['username'],
                "oxy_balance": str(player['oxy_balance']),
                "ko_balance": str(player['ko_balance'])
            }), 200
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Game routes
@app.route('/game/reward/click', methods=['POST'])
def reward_click():
    """Reward player for clicking"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON received"}), 400
            
        player_id = data.get('playerId')
        amount = data.get('amount')
        
        if not player_id or not amount:
            return jsonify({"error": "playerId and amount required"}), 400
            
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Check if player exists
            cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
            player = cursor.fetchone()
            if not player:
                return jsonify({"error": "Player not found"}), 404
                
            # Update KO balance
            cursor.execute(
                "UPDATE players SET ko_balance = ko_balance + ? WHERE id = ?",
                (int(amount), player_id)
            )
            conn.commit()
            
            # Get updated player data
            cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
            updated_player = cursor.fetchone()
            
            return jsonify({
                "ok": True,
                "player": dict(updated_player)
            }), 200
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/game/reward/action', methods=['POST'])
def reward_action():
    """Reward player for action (crime/fight)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON received"}), 400
            
        player_id = data.get('playerId')
        amount = data.get('amount')
        action = data.get('action')
        
        if not player_id or not amount or not action:
            return jsonify({"error": "playerId, amount, action required"}), 400
            
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Check if player exists
            cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
            player = cursor.fetchone()
            if not player:
                return jsonify({"error": "Player not found"}), 404
                
            # Update OXY balance
            cursor.execute(
                "UPDATE players SET oxy_balance = oxy_balance + ? WHERE id = ?",
                (int(amount), player_id)
            )
            conn.commit()
            
            # Get updated player data
            cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
            updated_player = cursor.fetchone()
            
            return jsonify({
                "ok": True,
                "player": dict(updated_player)
            }), 200
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/game/pay', methods=['POST'])
def game_pay():
    """Player payment (debit from player)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON received"}), 400
            
        player_id = data.get('playerId')
        token = data.get('token')
        amount = data.get('amount')
        reason = data.get('reason')
        
        if not player_id or not token or not amount or not reason:
            return jsonify({"error": "playerId, token, amount, reason required"}), 400
            
        if token not in ['KO', 'OXI']:
            return jsonify({"error": "token must be KO or OXI"}), 400
            
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Check if player exists
            cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
            player = cursor.fetchone()
            if not player:
                return jsonify({"error": "Player not found"}), 404
                
            # Check balance
            balance_field = 'ko_balance' if token == 'KO' else 'oxy_balance'
            current_balance = player[balance_field]
            
            if current_balance < int(amount):
                return jsonify({"error": "Insufficient balance"}), 400
                
            # Update balance
            cursor.execute(
                f"UPDATE players SET {balance_field} = {balance_field} - ? WHERE id = ?",
                (int(amount), player_id)
            )
            conn.commit()
            
            # Get updated player data
            cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
            updated_player = cursor.fetchone()
            
            return jsonify({
                "ok": True,
                "player": dict(updated_player)
            }), 200
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Admin routes (simplified)
@app.route('/api/admin/players', methods=['GET'])
def list_players():
    """List all players"""
    try:
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM players ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            players = cursor.fetchall()
            
            return jsonify([dict(player) for player in players]), 200
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve static files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return jsonify({"error": "Static folder not configured"}), 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return jsonify({"error": "index.html not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

