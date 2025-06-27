from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import random
import requests
import json
import psycopg2
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'quy_secret_key'

# --- API Cấu hình (Không thay đổi) ---
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

# --- Các hàm phụ trợ (Không thay đổi) ---
def generate_sentence_with_word_and_meaning(word, meaning):
    for config in API_CONFIGS:
        final_url = config['url'].replace('GEMINI_API_KEY', config['key'])
        key_identifier = config['key'][:10]
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": f"Create a natural English sentence for IT context, 15-20 words, using the word '{word}' which means '{meaning}'."}]}]}
        print(f"🔄 Đang thử với khóa API: {key_identifier}...")
        try:
            response = requests.post(final_url, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                print(f"✅ Thành công với khóa {key_identifier}!")
                response_data = response.json()
                generated_text = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                return generated_text.replace('**', '')
            elif response.status_code == 429:
                print(f"⚠️ Khóa {key_identifier} đã bị giới hạn. Chuyển sang khóa tiếp theo.")
                continue
            else:
                print(f"❌ Lỗi với khóa {key_identifier} (Mã lỗi: {response.status_code}). Chuyển sang khóa tiếp theo.")
                continue
        except requests.RequestException as e:
            print(f"❌ Lỗi kết nối mạng với khóa {key_identifier}: {e}")
            continue
    return None

def hidden_format(text):
    words = text.split()
    result = []
    for word in words:
        if len(word) > 0:
            hidden_word = word[0] + '_' + ' _' * (len(word) - 2) if len(word) > 1 else word
            result.append(hidden_word)
    return ' '.join(result)

def cut_sentence_around_phrase(sentence, target_phrase, word):
    lower_sentence = sentence.lower()
    lower_target_phrase = target_phrase.lower()
    start_index = lower_sentence.find(lower_target_phrase)
    if start_index == -1: return None
    end_index = start_index + len(target_phrase)
    before_phrase = sentence[:start_index].strip()
    after_phrase = sentence[end_index:].strip()
    return before_phrase + " " + hidden_format(word) + " " + after_phrase
    
def get_db_connection():
    neon_conn_string = os.environ.get('DATABASE_URL')
    try:
        conn = psycopg2.connect(neon_conn_string)
        return conn
    except Exception as e:
        print(f"Error connecting to Neon database: {e}")
        raise

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Vui lòng đăng nhập để sử dụng chức năng này.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("roles") != "admin":
            flash("Bạn không có quyền truy cập trang này.", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

# --- Route xác thực & trang chủ ---
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
        query = "SELECT id, username, roles, active FROM Account WHERE Username = %s AND Password = %s"
        cursor.execute(query, (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            if user[3] == 0:
                flash("Tài khoản của bạn chưa được kích hoạt. Vui lòng liên hệ admin.", "danger")
                return redirect(url_for("login"))
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["roles"] = user[2]
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
        roles, active = "user", 0
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
@login_required
def home():
    load_and_shuffle_vocabulary()
    if not session.get('available_words'):
        return render_template("home.html", username=session["username"], sentence="Bạn chưa có từ vựng nào. Hãy thêm ở trang Quản lý từ vựng.", correct_word="", question_info="0/0", roles=session.get("roles"))
    next_word_info = get_next_word_data()
    return render_template("home.html", 
                           username=session["username"],
                           sentence=next_word_info.get("sentence"), 
                           correct_word=next_word_info.get("correct_word"),
                           question_info=f"{next_word_info.get('question_number', 0)}/{next_word_info.get('total_questions', 0)}",
                           roles=session.get("roles"))

# --- Chức năng quản lý từ vựng cho MỌI USER ---
@app.route("/manage_vocabulary")
@login_required
def manage_vocabulary():
    user_id = session.get("user_id")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, word, mean FROM vocabulary WHERE user_id = %s ORDER BY id ASC", (user_id,))
    all_vocab = cursor.fetchall()
    conn.close()
    return render_template("manage_vocabulary.html", all_vocab=all_vocab, username=session.get("username"))

@app.route("/add_vocabulary", methods=["POST"])
@login_required
def add_vocabulary():
    vocab_input = request.form.get("vocab_input")
    if not vocab_input or '-' not in vocab_input:
        flash("Định dạng không hợp lệ. Vui lòng nhập theo dạng 'Word - Mean'.", "danger")
        return redirect(url_for("manage_vocabulary"))
    parts = [p.strip() for p in vocab_input.split('-', 1)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        flash("Từ và nghĩa không được để trống.", "danger")
        return redirect(url_for("manage_vocabulary"))
    word, mean = parts
    user_id = session.get("user_id")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO vocabulary (word, mean, user_id) VALUES (%s, %s, %s)", (word, mean, user_id))
        conn.commit()
        conn.close()
        flash(f"Đã thêm từ vựng '{word}' thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi thêm từ vựng: {e}", "danger")
    return redirect(url_for("manage_vocabulary"))

@app.route("/delete_vocabulary/<int:vocab_id>", methods=["POST"])
@login_required
def delete_vocabulary(vocab_id):
    user_id = session.get("user_id")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Thêm user_id vào câu lệnh DELETE để đảm bảo user chỉ xóa được từ của mình
        cursor.execute("DELETE FROM vocabulary WHERE id = %s AND user_id = %s", (vocab_id, user_id))
        conn.commit()
        conn.close()
        flash("Đã xóa từ vựng thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi xóa từ vựng: {e}", "danger")
    return redirect(url_for("manage_vocabulary"))

@app.route("/delete_all_vocabulary", methods=["POST"])
@login_required
def delete_all_vocabulary():
    user_id = session.get("user_id")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Thay TRUNCATE bằng DELETE có điều kiện
        cursor.execute("DELETE FROM vocabulary WHERE user_id = %s", (user_id,))
        conn.commit()
        conn.close()
        flash("Đã xóa toàn bộ từ vựng của bạn thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi xóa từ vựng: {e}", "danger")
    return redirect(url_for("manage_vocabulary"))

# --- Chức năng của Admin (Chỉ quản lý tài khoản) ---
@app.route("/manage_accounts")
@admin_required
def manage_accounts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, roles FROM account WHERE active = 0")
    inactive_accounts = cursor.fetchall()
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

# --- API cho chức năng học từ vựng ---
def load_and_shuffle_vocabulary():
    if 'user_id' not in session: return
    user_id = session.get("user_id")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT word, mean FROM vocabulary WHERE user_id = %s", (user_id,))
    all_words = [{'word': r[0], 'mean': r[1]} for r in cursor.fetchall()]
    conn.close()
    random.shuffle(all_words)
    session['available_words'] = all_words
    session['total_words'] = len(all_words)
    session.modified = True
    
def get_next_word_data():
    available_words = session.get('available_words', [])
    if not available_words: return {"completed": True}
    selected_word_data = available_words.pop(0)
    session['current_word_data'] = selected_word_data
    session.modified = True
    word = selected_word_data['word']
    meaning = selected_word_data['mean']
    sentence = generate_sentence_with_word_and_meaning(word, meaning)
    hidden_sentence = cut_sentence_around_phrase(sentence, word, word) if sentence else "Không thể tạo câu."
    return {
        "completed": False, "sentence": hidden_sentence, "correct_word": word,
        "question_number": session.get('total_words', 0) - len(available_words),
        "total_questions": session.get('total_words', 0)
    }

@app.route("/check_answer", methods=["POST"])
@login_required
def check_answer():
    user_input = request.json.get("answer", "").strip().lower()
    correct_word = request.json.get("correct_word", "").strip().lower()
    if user_input == correct_word:
        current_word_data = session.get('current_word_data', {})
        return jsonify({"success": True, "message": "✅ Chính xác!", "word": correct_word, "meaning": current_word_data.get('mean', '')})
    else:
        return jsonify({"success": False, "message": "❌ Sai rồi!"})

@app.route("/next_word", methods=["POST"])
@login_required
def next_word():
    return jsonify(get_next_word_data())

@app.route("/review", methods=["POST"])
@login_required
def review():
    load_and_shuffle_vocabulary()
    return jsonify(get_next_word_data())

@app.route("/regenerate_sentence", methods=["POST"])
@login_required
def regenerate_sentence():
    word = request.json.get("word")
    current_word_data = session.get('current_word_data')
    if not word or not current_word_data or current_word_data['word'] != word:
        return jsonify({"success": False, "message": "Lỗi session hoặc từ không hợp lệ."}), 400
    meaning = current_word_data['mean']
    sentence = generate_sentence_with_word_and_meaning(word, meaning)
    hidden_sentence = cut_sentence_around_phrase(sentence, word, word) if sentence else "Không thể tạo câu."
    return jsonify({"success": True, "new_sentence": hidden_sentence})
    
@app.route("/logout")
def logout():
    session.clear()
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)