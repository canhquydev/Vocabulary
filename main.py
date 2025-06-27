from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import random
import requests
import json
import psycopg2
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'quy_secret_key'

# --- Các hàm và cấu hình API giữ nguyên ---
API_CONFIGS = [
    {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=GEMINI_API_KEY",
        "key": "AIzaSyB6oo4MOqTTq07tLpWozpZ2NoKo45vLc14"
    },
    {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=GEMINI_API_KEY",
        "key": "AIzaSyCTHUesZlrg23UFTTVpDEGe54gSpHdZ9KU"
    }
]

def generate_sentence_with_word_and_meaning(word, meaning):
    for config in API_CONFIGS:
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"Create a 15-20 word IT-related sentence using '{word}' which means '{meaning}'. "
                                    f"The sentence should be professional, use diverse structures, and not repeat previous forms."
                        }
                    ]
                }
            ]
        }

        try:
            response = requests.post(
                f"{config['url']}?key={config['key']}",
                headers=headers,
                data=json.dumps(data)
            )

            if response.status_code == 200:
                response_data = response.json()
                return response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()

            elif response.status_code == 429:
                print(f"⚠️ Quá giới hạn với key {config['key']}, thử key khác...")
                continue

        except Exception as e:
            print(f"Lỗi gọi API với key {config['key']}: {e}")
            continue

    return None

def hidden_format(text):
    words = text.split()
    result = []

    for word in words:
        if len(word) > 0:
            if len(word) == 1:
                hidden_word = word
            else:
                hidden_word = word[0] + '_' + ' _' * (len(word) - 2)
            result.append(hidden_word)

    return ' '.join(result)

def cut_sentence_around_phrase(sentence, target_phrase, word):
    lower_sentence = sentence.lower()
    lower_target_phrase = target_phrase.lower()

    start_index = lower_sentence.find(lower_target_phrase)

    if start_index == -1:
        return None
    
    end_index = start_index + len(target_phrase)

    before_phrase = sentence[:start_index].strip()
    after_phrase = sentence[end_index:].strip()

    return before_phrase + " " + hidden_format(word) + " " + after_phrase
    
# Cấu hình kết nối
def get_db_connection():
    neon_conn_string = os.environ.get('DATABASE_URL')
    try:
        conn = psycopg2.connect(neon_conn_string)
        return conn
    except Exception as e:
        print(f"Error connecting to Neon database: {e}")
        raise

# Decorator để kiểm tra vai trò admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("roles") != "admin":
            flash("Bạn không có quyền truy cập trang này.", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

# --- Các route đã được cập nhật và thêm mới ---

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT username, roles, active FROM Account WHERE Username = %s AND Password = %s"
        cursor.execute(query, (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            if user[2] == 0: # Kiểm tra active
                flash("Tài khoản của bạn chưa được kích hoạt. Vui lòng liên hệ admin.", "danger")
                return redirect(url_for("login"))
            
            session["username"] = user[0]
            session["roles"] = user[1]
            session.pop('available_words', None)
            return redirect(url_for("home"))
        else:
            flash("Sai tài khoản hoặc mật khẩu.", "danger")
            return redirect(url_for("login"))
            
    return render_template("login.html")

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        rpassword = request.form.get('rpassword')
        if password != rpassword:
            flash("Mật khẩu không khớp.", "danger")
            return redirect(url_for("register"))
        
        # Mặc định role là user và active là 0
        roles = "user" 
        active = 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ACCOUNT WHERE Username = %s", (username,))
        if cursor.fetchone():
            conn.close()
            flash("Tên đăng nhập đã tồn tại!", "danger")
            return redirect(url_for("register"))

        query = "INSERT INTO account (username, password, roles, active) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (username, password, roles, active))
        conn.commit()
        conn.close()

        flash("Đăng ký thành công! Vui lòng chờ admin kích hoạt tài khoản của bạn.", "success")
        return redirect(url_for("login"))
        
    return render_template("register.html")

@app.route("/home")
def home():
    if "username" not in session:
        return redirect("/login")
    
    # Logic ôn tập từ vựng giữ nguyên
    load_and_shuffle_vocabulary()
    
    if not session.get('available_words'):
        return render_template("home.html", username=session["username"], sentence="Không có từ vựng nào.", correct_word="", question_info="0/0", roles=session.get("roles"))

    next_word_info = get_next_word_data()

    return render_template("home.html", 
                           username=session["username"],
                           sentence=next_word_info.get("sentence"), 
                           correct_word=next_word_info.get("correct_word"),
                           question_info=f"{next_word_info.get('question_number', 0)}/{next_word_info.get('total_questions', 0)}",
                           roles=session.get("roles"))

# --- Chức năng của Admin ---
@app.route("/admin")
@admin_required
def admin_panel():
    return render_template("admin.html", username=session.get("username"))

@app.route("/add_vocabulary", methods=["POST"])
@admin_required
def add_vocabulary():
    vocab_input = request.form.get("vocab_input")
    if not vocab_input or '-' not in vocab_input:
        flash("Định dạng không hợp lệ. Vui lòng nhập theo dạng 'Word - Mean'.", "danger")
        return redirect(url_for("admin_panel"))

    parts = [p.strip() for p in vocab_input.split('-', 1)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        flash("Từ và nghĩa không được để trống.", "danger")
        return redirect(url_for("admin_panel"))
        
    word, mean = parts
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO vocabulary (word, mean) VALUES (%s, %s)", (word, mean))
        conn.commit()
        conn.close()
        flash(f"Đã thêm từ vựng '{word}' thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi thêm từ vựng: {e}", "danger")

    return redirect(url_for("admin_panel"))

@app.route("/manage_accounts")
@admin_required
def manage_accounts():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Lấy danh sách tài khoản chưa kích hoạt
    cursor.execute("SELECT id, username, roles FROM account WHERE active = 0")
    inactive_accounts = cursor.fetchall()
    # Lấy danh sách tài khoản đã kích hoạt (trừ admin)
    cursor.execute("SELECT id, username, roles FROM account WHERE active = 1 AND roles != 'admin'")
    active_accounts = cursor.fetchall()
    conn.close()
    return render_template("manage_accounts.html", inactive_accounts=inactive_accounts, active_accounts=active_accounts, username=session.get("username"))

@app.route("/activate_account/<int:account_id>", methods=["POST"])
@admin_required
def activate_account(account_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE account SET active = 1 WHERE id = %s", (account_id,))
        conn.commit()
        conn.close()
        flash("Kích hoạt tài khoản thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi kích hoạt tài khoản: {e}", "danger")
    return redirect(url_for("manage_accounts"))

@app.route("/delete_account/<int:account_id>", methods=["POST"])
@admin_required
def delete_account(account_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM account WHERE id = %s", (account_id,))
        conn.commit()
        conn.close()
        flash("Xóa tài khoản thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi xóa tài khoản: {e}", "danger")
    return redirect(url_for("manage_accounts"))

# --- Các hàm và route còn lại giữ nguyên ---
def load_and_shuffle_vocabulary():
    """Tải từ vựng từ DB, xáo trộn và lưu vào session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT word, mean FROM vocabulary")
    all_words = [{'word': r[0], 'mean': r[1]} for r in cursor.fetchall()]
    conn.close()
    random.shuffle(all_words)
    session['available_words'] = all_words
    session['total_words'] = len(all_words)
    session.modified = True
    
def get_next_word_data():
    """Lấy dữ liệu cho từ tiếp theo trong session."""
    available_words = session.get('available_words', [])
    if not available_words:
        return {"completed": True}

    selected_word_data = available_words.pop(0)
    session['current_word_data'] = selected_word_data
    session.modified = True

    word = selected_word_data['word']
    meaning = selected_word_data['mean']
    sentence = generate_sentence_with_word_and_meaning(word, meaning)

    if sentence:
        hidden_sentence = cut_sentence_around_phrase(sentence, word, word)
    else:
        hidden_sentence = "Không thể tạo câu."

    return {
        "completed": False,
        "sentence": hidden_sentence,
        "correct_word": word,
        "question_number": session.get('total_words', 0) - len(available_words),
        "total_questions": session.get('total_words', 0)
    }

@app.route("/check_answer", methods=["POST"])
def check_answer():
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    user_input = request.json.get("answer", "").strip().lower()
    correct_word = request.json.get("correct_word", "").strip().lower()

    if user_input == correct_word:
        current_word_data = session.get('current_word_data')
        if not current_word_data:
            return jsonify({"success": False, "message": "Lỗi session."})

        meaning = current_word_data.get('mean', 'Không tìm thấy nghĩa')
        return jsonify({
            "success": True, 
            "message": "✅ Chính xác!", 
            "word": correct_word, 
            "meaning": meaning
        })
    else:
        return jsonify({"success": False, "message": "❌ Sai rồi!"})

@app.route("/next_word", methods=["POST"])
def next_word():
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    next_word_info = get_next_word_data()
    return jsonify(next_word_info)

@app.route("/review", methods=["POST"])
def review():
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    load_and_shuffle_vocabulary()
    next_word_info = get_next_word_data()
    return jsonify(next_word_info)


@app.route("/skip_word", methods=["POST"])
def skip_word():
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    if not session.get('available_words'):
        return jsonify({"completed": True, "message": "Bạn đã hoàn thành tất cả các câu hỏi!"})

    next_word_info = get_next_word_data()
    return jsonify(next_word_info)

@app.route("/regenerate_sentence", methods=["POST"])
def regenerate_sentence():
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    word = request.json.get("word")
    if not word:
        return jsonify({"success": False, "message": "Word not provided."}), 400

    current_word_data = session.get('current_word_data')
    if not current_word_data or current_word_data['word'] != word:
        return jsonify({"success": False, "message": "Lỗi session hoặc từ không hợp lệ."}), 400

    meaning = current_word_data['mean']
    sentence = generate_sentence_with_word_and_meaning(word, meaning)
    if sentence:
        hidden_sentence = cut_sentence_around_phrase(sentence, word, word)
    else:
        hidden_sentence = "Không thể tạo câu."

    return jsonify({
        "success": True,
        "new_sentence": hidden_sentence
    })
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)