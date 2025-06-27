from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import random
import requests
import json
import os
from functools import wraps
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a-very-secret-key-for-development")

# --- Cấu hình Supabase ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Lỗi khi khởi tạo Supabase client: {e}")
    supabase = None

# --- Cấu hình API Gemini (Linh hoạt hơn) ---

# Đọc chuỗi các API key từ một biến môi trường duy nhất
gemini_keys_str = os.environ.get("GEMINI_API_KEYS", "")

# Tách chuỗi thành một danh sách các key
# Dùng list comprehension để tạo danh sách API_CONFIGS một cách tự động
API_CONFIGS = [
    {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=GEMINI_API_KEY",
        "key": key.strip()  # .strip() để loại bỏ khoảng trắng thừa
    }
    for key in gemini_keys_str.split(',') if key.strip()
] if gemini_keys_str else []

# --- Các hàm phụ trợ ---
def generate_sentence_with_word_and_meaning(word, meaning):
    if not API_CONFIGS:
        print("Lỗi: Không có khóa API nào của Gemini được cấu hình trong biến môi trường GEMINI_API_KEYS.")
        return None

    # Logic xoay vòng key không cần thay đổi, nó sẽ tự động duyệt qua danh sách API_CONFIGS
    for config in API_CONFIGS:
        final_url = config['url'].replace('GEMINI_API_KEY', config['key'])
        key_identifier = config['key'][:10]
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": f"Create a natural English sentence for IT context, 15-20 words, using the word '{word}' which means '{meaning}'."}]}]}
        print(f"🔄 Đang thử với khóa API: {key_identifier}...")
        try:
            response = requests.post(final_url, headers=headers, data=json.dumps(data), timeout=15)
            if response.status_code == 200:
                print(f"✅ Thành công với khóa {key_identifier}!")
                response_data = response.json()
                generated_text = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                return generated_text.replace('**', '')
            elif response.status_code == 429:
                print(f"⚠️ Khóa {key_identifier} đã bị giới hạn. Chuyển sang khóa tiếp theo.")
                continue
            else:
                print(f"❌ Lỗi với khóa {key_identifier} (Mã lỗi: {response.status_code}). Chi tiết: {response.text}")
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
            hidden_word = word[0] + ' _' * (len(word) - 1) if len(word) > 1 else word
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
    if not supabase:
        return "Lỗi: Không thể kết nối tới Supabase. Vui lòng kiểm tra lại biến môi trường.", 500
    return render_template("login.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        response = supabase.table('account').select("*").eq('username', username).eq('password', password).execute()
        
        if response.data:
            user = response.data[0]
            if user['active'] == 0:
                flash("Tài khoản của bạn chưa được kích hoạt. Vui lòng liên hệ admin.", "danger")
                return redirect(url_for("login"))
            
            session["user_id"] = user['id']
            session["username"] = user['username']
            session["roles"] = user['roles']
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
        
        response = supabase.table('account').select("id").eq('username', username).execute()
        if response.data:
            flash("Tên đăng nhập đã tồn tại!", "danger")
            return redirect(url_for("register"))

        roles, active = "user", 0
        supabase.table('account').insert({
            "username": username,
            "password": password,
            "roles": roles,
            "active": active
        }).execute()

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
    question_info_str = f"Câu {next_word_info.get('question_number', 0)}/{next_word_info.get('total_questions', 0)}"

    return render_template("home.html", 
                           username=session["username"],
                           sentence=next_word_info.get("sentence"), 
                           correct_word=next_word_info.get("correct_word"),
                           question_info=question_info_str,
                           roles=session.get("roles"))

# --- Chức năng quản lý từ vựng ---
@app.route("/manage_vocabulary")
@login_required
def manage_vocabulary():
    user_id = session.get("user_id")
    response = supabase.table('vocabulary').select("id, word, mean").eq('user_id', user_id).order('id').execute()
    return render_template("manage_vocabulary.html", all_vocab=response.data, username=session.get("username"))

@app.route("/add_vocabulary", methods=["POST"])
@login_required
def add_vocabulary():
    vocab_input = request.form.get("vocab_input_list")
    user_id = session.get("user_id")
    
    if not vocab_input.strip():
        flash("Vui lòng nhập ít nhất một từ vựng.", "danger")
        return redirect(url_for("manage_vocabulary"))

    lines = vocab_input.strip().split('\n')
    new_vocabs_to_insert = []
    invalid_lines = 0

    for line in lines:
        line = line.strip()
        if not line or '-' not in line:
            if line: invalid_lines += 1
            continue
        
        parts = [p.strip() for p in line.split('-', 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            new_vocabs_to_insert.append({"word": parts[0], "mean": parts[1], "user_id": user_id})
        else:
            invalid_lines += 1

    if not new_vocabs_to_insert:
        flash("Không có từ vựng hợp lệ nào được tìm thấy. Vui lòng kiểm tra lại định dạng.", "danger")
        return redirect(url_for("manage_vocabulary"))

    try:
        supabase.table('vocabulary').insert(new_vocabs_to_insert).execute()
        success_message = f"Đã thêm thành công {len(new_vocabs_to_insert)} từ vựng!"
        if invalid_lines > 0:
            success_message += f" (Bỏ qua {invalid_lines} dòng không hợp lệ)."
        flash(success_message, "success")
    except Exception as e:
        flash(f"Lỗi khi thêm từ vựng: {e}", "danger")

    return redirect(url_for("manage_vocabulary"))

@app.route("/delete_vocabulary/<int:vocab_id>", methods=["POST"])
@login_required
def delete_vocabulary(vocab_id):
    user_id = session.get("user_id")
    try:
        supabase.table('vocabulary').delete().eq('id', vocab_id).eq('user_id', user_id).execute()
        flash("Đã xóa từ vựng thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi xóa từ vựng: {e}", "danger")
    return redirect(url_for("manage_vocabulary"))

@app.route("/delete_all_vocabulary", methods=["POST"])
@login_required
def delete_all_vocabulary():
    user_id = session.get("user_id")
    try:
        supabase.table('vocabulary').delete().eq('user_id', user_id).execute()
        flash("Đã xóa toàn bộ từ vựng của bạn thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi xóa từ vựng: {e}", "danger")
    return redirect(url_for("manage_vocabulary"))

# --- Chức năng của Admin ---
@app.route("/manage_accounts")
@admin_required
def manage_accounts():
    inactive_res = supabase.table('account').select("id, username, roles").eq('active', 0).execute()
    active_res = supabase.table('account').select("id, username, roles").eq('active', 1).neq('roles', 'admin').execute()
    return render_template("manage_accounts.html", inactive_accounts=inactive_res.data, active_accounts=active_res.data, username=session.get("username"))

@app.route("/activate_account/<int:account_id>", methods=["POST"])
@admin_required
def activate_account(account_id):
    try:
        supabase.table('account').update({'active': 1}).eq('id', account_id).execute()
        flash("Kích hoạt tài khoản thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi kích hoạt tài khoản: {e}", "danger")
    return redirect(url_for("manage_accounts"))

@app.route("/delete_account/<int:account_id>", methods=["POST"])
@admin_required
def delete_account(account_id):
    try:
        supabase.table('account').delete().eq('id', account_id).execute()
        flash("Xóa tài khoản thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi xóa tài khoản: {e}", "danger")
    return redirect(url_for("manage_accounts"))

# --- API cho chức năng học từ vựng ---
def load_and_shuffle_vocabulary():
    if 'user_id' not in session: return
    user_id = session.get("user_id")
    response = supabase.table('vocabulary').select("word, mean").eq('user_id', user_id).execute()
    all_words = response.data
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
    hidden_sentence = cut_sentence_around_phrase(sentence, word, word) if sentence else f"Không thể tạo câu cho từ '{word}'. Vui lòng thử lại."

    total_questions = session.get('total_words', 0)
    question_number = total_questions - len(available_words)

    return {
        "completed": False, 
        "sentence": hidden_sentence, 
        "correct_word": word,
        "question_number": question_number,
        "total_questions": total_questions
    }

@app.route("/check_answer", methods=["POST"])
@login_required
def check_answer():
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
            "word": correct_word.capitalize(), 
            "meaning": meaning
        })
    else:
        return jsonify({"success": False, "message": "❌ Sai rồi!"})

@app.route("/next_word", methods=["POST"])
@login_required
def next_word():
    next_word_info = get_next_word_data()
    return jsonify(next_word_info)
    
@app.route("/review", methods=["POST"])
@login_required
def review():
    load_and_shuffle_vocabulary()
    next_word_info = get_next_word_data()
    return jsonify(next_word_info)

@app.route("/regenerate_sentence", methods=["POST"])
@login_required
def regenerate_sentence():
    word = request.json.get("word")
    current_word_data = session.get('current_word_data')
    if not word or not current_word_data or current_word_data['word'] != word:
        return jsonify({"success": False, "message": "Lỗi session hoặc từ không hợp lệ."}), 400
    
    meaning = current_word_data['mean']
    sentence = generate_sentence_with_word_and_meaning(word, meaning)
    
    if sentence:
        hidden_sentence = cut_sentence_around_phrase(sentence, word, word)
        return jsonify({"success": True, "new_sentence": hidden_sentence})
    else:
        return jsonify({"success": False, "message": "Không thể tạo lại câu. Vui lòng thử lại."})
    
@app.route("/logout")
def logout():
    session.clear()
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    if not supabase:
        print("CRITICAL ERROR: Could not connect to Supabase. Check your environment variables.")
    elif not API_CONFIGS:
        print("WARNING: No Gemini API keys found. The sentence generation feature will not work.")
    app.run(debug=True)