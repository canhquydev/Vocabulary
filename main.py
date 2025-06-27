from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
# import pyodbc
import random
import requests
import json
import psycopg2 # Thêm vào cho Neon/PostgreSQL
import os # Để đọc biến môi trường
app = Flask(__name__)
app.secret_key = 'quy_secret_key'
API_CONFIGS = [
    {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent",
        "key": "AIzaSyC5Tkm0jMROkEhpvYZdYDQSdYnjv5qhh5s"
    },
    {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent",
        "key": "AIzaSyCMQ_deEV-ZSIvyJuot5Dxpyrd8qzEIpag"
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


# Cấu hình kết nối SQL Server
def get_db_connection():
    # Lấy chuỗi kết nối từ biến môi trường trên Render
    # Biến môi trường này sẽ được cấu hình trên Render dashboard
    neon_conn_string = os.environ.get('DATABASE_URL')
    try:
            conn = psycopg2.connect(neon_conn_string)
            return conn
    except Exception as e:
        print(f"Error connecting to Neon database: {e}")
        # Xử lý lỗi kết nối, có thể raise exception hoặc trả về None
        raise
    # if neon_conn_string:
    #     try:
    #         conn = psycopg2.connect(neon_conn_string)
    #         return conn
    #     except Exception as e:
    #         print(f"Error connecting to Neon database: {e}")
    #         # Xử lý lỗi kết nối, có thể raise exception hoặc trả về None
    #         raise
    # else:
    #     # Fallback cho phát triển cục bộ với SQL Server nếu biến môi trường không tồn tại
    #     # Đảm bảo bạn đã cài đặt pyodbc và driver cho SQL Server
    #     try:
    #         conn = pyodbc.connect(
    #             'DRIVER={ODBC Driver 17 for SQL Server};'
    #             'SERVER=0D75D1721846358\\SQLEXPRESS;'
    #             'DATABASE=QL;'
    #             'UID=sa;'
    #             'PWD=123456789'
    #         )
    #         return conn
    #     except Exception as e:
    #         print(f"Error connecting to local SQL Server: {e}")
    #         raise
# def get_db_connection():
#     conn = pyodbc.connect(
#         'DRIVER={ODBC Driver 17 for SQL Server};'
#         'SERVER=0D75D1721846358\\SQLEXPRESS;'
#         'DATABASE=QL;'
#         'UID=sa;'
#         'PWD=123456789'
#     )
#     return conn

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

        query = "SELECT * FROM Account WHERE Username = %s AND Password = %s"
        cursor.execute(query, (username, password))
        user = cursor.fetchone()

        conn.close()

        if user:
            session["username"] = username
            # Clear available_words for a new session/login, will be reloaded by home()
            session.pop('available_words', None) 
            return redirect(url_for("home"))
        else:
            return "❌ Sai tài khoản hoặc mật khẩu"
    return render_template("login.html")

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        rpassword = request.form.get('rpassword')
        if password != rpassword:
            return "Mật khẩu không khớp"
        roles = "user"
        active = 0
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ACCOUNT WHERE Username = %s", (username,))
        if cursor.fetchone():
            conn.close()
            return "❌ Tên đăng nhập đã tồn tại!"
        query = "INSERT INTO ACCOUNT VALUES(%s, %s, %s, %s)"
        cursor.execute(query, (username, password, roles, active))
        conn.commit()
        conn.close()
        return render_template("login.html")
    return render_template("register.html")

@app.route("/home", methods=["GET"])
def home():
    if "username" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT word, mean FROM vocabulary")
    # Always load words from the database on initial home load or refresh
    session['available_words'] = [{'word': r[0], 'mean': r[1]} for r in cursor.fetchall()]
    conn.close()
    random.shuffle(session['available_words']) # Shuffle for random order
    session.modified = True # Mark session as modified after updating the list

    if not session['available_words']:
        return render_template("home.html", username=session["username"], sentence="Không có từ vựng nào.", correct_word="")

    # Pop a word from the list
    selected_word_data = session['available_words'].pop(0) # Pop from the beginning
    word = selected_word_data['word']
    meaning = selected_word_data['mean']

    session.modified = True # Mark session as modified after popping

    sentence = generate_sentence_with_word_and_meaning(word, meaning)
    if sentence:
        hidden_sentence = cut_sentence_around_phrase(sentence, word, word)
    else:
        hidden_sentence = "Không thể tạo câu."

    return render_template("home.html", username=session["username"],
                           sentence=hidden_sentence, correct_word=word)

@app.route("/check_answer", methods=["POST"])
def check_answer():
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    user_input = request.json.get("answer", "").strip().lower()
    correct_word = request.json.get("correct_word", "").strip().lower()

    if user_input == correct_word:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT mean FROM vocabulary WHERE word = %s", (correct_word,))
        result = cursor.fetchone()
        conn.close()
        meaning = result[0] if result else "Không tìm thấy nghĩa" # Giả sử 'mean' là cột đầu tiên hoặc duy nhất được chọn
        return jsonify({"success": True, "message": "✅ Chính xác!", "word": correct_word, "meaning": meaning})
    else:
        return jsonify({"success": False, "message": "❌ Sai rồi!"})

@app.route("/skip_word", methods=["POST"])
def skip_word():
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    if not session.get('available_words'):
        # If the list is empty, re-populate it for the next round (simulates starting over)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT word, mean FROM vocabulary")
        session['available_words'] = [{'word': r.word, 'mean': r.mean} for r in cursor.fetchall()]
        conn.close()
        random.shuffle(session['available_words'])
        session.modified = True # Mark session as modified

        if not session['available_words']:
            return jsonify({"success": False, "message": "Không có từ vựng nào để tải."})

    # Pop a new word from the list
    selected_word_data = session['available_words'].pop(0) # Pop from the beginning
    word = selected_word_data['word']
    meaning = selected_word_data['mean']

    session.modified = True # Mark session as modified

    sentence = generate_sentence_with_word_and_meaning(word, meaning)
    if sentence:
        hidden_sentence = cut_sentence_around_phrase(sentence, word, word)
    else:
        hidden_sentence = "Không thể tạo câu."

    return jsonify({
        "success": True,
        "new_sentence": hidden_sentence,
        "new_correct_word": word
    })

@app.route("/regenerate_sentence", methods=["POST"])
def regenerate_sentence():
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    word = request.json.get("word")
    if not word:
        return jsonify({"success": False, "message": "Word not provided."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT mean FROM vocabulary WHERE word = %s", (word,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return jsonify({"success": False, "message": f"Không tìm thấy nghĩa cho từ '{word}'."}), 404

    meaning = result.mean
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
    app.run(debug=False)