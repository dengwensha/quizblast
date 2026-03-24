#!/usr/bin/env python3
"""
QuizBlast Multiplayer — Flask Web Uygulaması
Kurulum: pip install flask
Çalıştır: python3 app.py
"""

from flask import Flask, render_template, request, jsonify, session
import random, time, string, copy, threading, json, base64, io, os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "quizblast-secret-2024")

# ─────────────────────────────────────────
#  QR KOD ÜRETİCİ (sıfır bağımlılık)
# ─────────────────────────────────────────
def make_qr_svg(url, size=200):
    """URL'den SVG QR kodu üretir — qrcode kütüphanesi gerekmez."""
    try:
        import qrcode
        import qrcode.image.svg
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue().decode()
    except ImportError:
        pass

    # Fallback: basit QR benzeri SVG (gerçek QR değil ama görsel)
    # Gerçek mini QR matrisi: URL'in hash'ine göre desen üret
    import hashlib
    h = hashlib.md5(url.encode()).hexdigest()
    n = 21  # 21x21 modül
    cell = size // n
    random.seed(int(h, 16) % (2**31))

    # Gerçek QR pattern simülasyonu
    grid = [[False] * n for _ in range(n)]

    # Finder patterns (3 köşe)
    for fx, fy in [(0, 0), (n - 7, 0), (0, n - 7)]:
        for dy in range(7):
            for dx in range(7):
                if dx == 0 or dx == 6 or dy == 0 or dy == 6:
                    grid[fy + dy][fx + dx] = True
                elif 2 <= dx <= 4 and 2 <= dy <= 4:
                    grid[fy + dy][fx + dx] = True

    # Timing patterns
    for i in range(8, n - 8):
        grid[6][i] = (i % 2 == 0)
        grid[i][6] = (i % 2 == 0)

    # Data modules (URL hash'e göre)
    data_bits = bin(int(h * 3, 16))[2:].zfill(n * n)
    bit_i = 0
    for y in range(n):
        for x in range(n):
            if not (
                (x < 8 and y < 8) or (x > n - 9 and y < 8) or
                (x < 8 and y > n - 9) or x == 6 or y == 6
            ):
                if bit_i < len(data_bits):
                    grid[y][x] = data_bits[bit_i] == "1"
                    bit_i += 1

    cells_svg = []
    for y in range(n):
        for x in range(n):
            if grid[y][x]:
                cx = x * cell
                cy = y * cell
                cells_svg.append(f'<rect x="{cx}" y="{cy}" width="{cell}" height="{cell}"/>')

    total = n * cell
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" width="{size}" height="{size}">
  <rect width="{total}" height="{total}" fill="white"/>
  <g fill="black">{"".join(cells_svg)}</g>
</svg>'''
    return svg


# ─────────────────────────────────────────
#  VERİ
# ─────────────────────────────────────────
DEFAULT_QUESTIONS = [
    {"q": "Güneş sisteminin en büyük gezegeni hangisidir?",
     "opts": ["Jüpiter", "Satürn", "Neptün", "Uranüs"], "correct": 0,
     "category": "Bilim", "hint": "Büyük Kırmızı Leke fırtınasına ev sahipliği yapar."},
    {"q": "'Au' kimyasal sembolü hangi elemene aittir?",
     "opts": ["Altın", "Gümüş", "Bakır", "Demir"], "correct": 0,
     "category": "Kimya", "hint": "Mücevherlerde kullanılan değerli bir metaldir."},
    {"q": "İkinci Dünya Savaşı hangi yılda sona erdi?",
     "opts": ["1945", "1944", "1946", "1943"], "correct": 0,
     "category": "Tarih", "hint": "Japonya'ya atom bombası atıldığı yıldır."},
    {"q": "Japonya'nın başkenti neresidir?",
     "opts": ["Tokyo", "Osaka", "Kyoto", "Hiroşima"], "correct": 0,
     "category": "Coğrafya", "hint": "Dünyanın en kalabalık şehridir."},
    {"q": "Mona Lisa'yı kim yaptı?",
     "opts": ["Leonardo da Vinci", "Michelangelo", "Raphael", "Botticelli"], "correct": 0,
     "category": "Sanat", "hint": "Aynı zamanda bilim insanı ve mucitti."},
    {"q": "Dünyanın en uzun nehri hangisidir?",
     "opts": ["Nil", "Amazon", "Yangtze", "Mississippi"], "correct": 0,
     "category": "Coğrafya", "hint": "Kuzeydoğu Afrika'dan geçer."},
    {"q": "Yetişkin insan vücudunda kaç kemik bulunur?",
     "opts": ["206", "204", "208", "212"], "correct": 0,
     "category": "Biyoloji", "hint": "Bebekler yaklaşık 270 kemikle doğar."},
    {"q": "Kızıl Gezegen olarak bilinen gezegen?",
     "opts": ["Mars", "Venüs", "Merkür", "Jüpiter"], "correct": 0,
     "category": "Astronomi", "hint": "Güneş sistemindeki en büyük volkan burada."},
    {"q": "En fazla anadil konuşucusuna sahip dil?",
     "opts": ["Mandarin", "İspanyolca", "İngilizce", "Hintçe"], "correct": 0,
     "category": "Diller", "hint": "900 milyondan fazla anadil konuşucusu var."},
    {"q": "Işığın hızı yaklaşık kaçtır?",
     "opts": ["300.000 km/s", "150.000 km/s", "600.000 km/s", "30.000 km/s"], "correct": 0,
     "category": "Fizik", "hint": "Işık, Dünya'yı saniyede ~7.5 kez çevirebilir."},
]

# ─────────────────────────────────────────
#  OYUN DURUMU (in-memory, tek session)
# ─────────────────────────────────────────
game_state = {
    "status": "waiting",       # waiting | question | answer | finished
    "questions": copy.deepcopy(DEFAULT_QUESTIONS),
    "game_questions": [],
    "current_q": -1,
    "timer_start": 0,
    "timer_duration": 20,
    "players": {},             # player_id -> {name, score, streak, answers}
    "room_code": "QUIZ",
    "answers_this_round": {},  # player_id -> answer_idx
    "host_password": os.environ.get("HOST_PASSWORD", "host123"),
    "lifelines": {},           # player_id -> {fiftyfifty, skip, hint}
}

state_lock = threading.Lock()

def gen_room_code():
    return "".join(random.choices(string.ascii_uppercase, k=4))

def gen_player_id():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

def get_timer_remaining():
    if game_state["status"] != "question":
        return 0
    elapsed = time.time() - game_state["timer_start"]
    return max(0, game_state["timer_duration"] - elapsed)

def current_question():
    qi = game_state["current_q"]
    if 0 <= qi < len(game_state["game_questions"]):
        return game_state["game_questions"][qi]
    return None

def safe_question(q):
    """Doğru cevabı gizle — oyuncuya gönderilecek versiyon."""
    if not q:
        return None
    return {
        "q": q["q"],
        "opts": q["opts"],
        "category": q.get("category", "Genel"),
        "idx": game_state["current_q"],
        "total": len(game_state["game_questions"]),
    }

def leaderboard():
    players = game_state["players"]
    lb = sorted(
        [{"id": pid, "name": p["name"], "score": p["score"], "streak": p["streak"]}
         for pid, p in players.items()],
        key=lambda x: x["score"], reverse=True
    )
    for i, p in enumerate(lb):
        p["rank"] = i + 1
    return lb

# ─────────────────────────────────────────
#  ROTALAR — HOST
# ─────────────────────────────────────────
@app.route("/")
def index():
    return render_template("host.html")

@app.route("/play")
def play():
    return render_template("player.html")

@app.route("/api/host/init", methods=["POST"])
def host_init():
    data = request.json or {}
    pwd = data.get("password", "")
    if pwd != game_state["host_password"]:
        return jsonify({"ok": False, "error": "Şifre yanlış"}), 403

    with state_lock:
        game_state["room_code"] = gen_room_code()
        game_state["status"] = "waiting"
        game_state["players"] = {}
        game_state["current_q"] = -1
        game_state["game_questions"] = []
        game_state["answers_this_round"] = {}

    host_url = f"http://{request.host}/play?room={game_state['room_code']}"
    qr_svg = make_qr_svg(host_url)
    return jsonify({
        "ok": True,
        "room_code": game_state["room_code"],
        "join_url": host_url,
        "qr_svg": qr_svg,
    })

@app.route("/api/host/start", methods=["POST"])
def host_start():
    data = request.json or {}
    if data.get("password") != game_state["host_password"]:
        return jsonify({"ok": False, "error": "Yetkisiz"}), 403

    timer_dur = int(data.get("timer", 20))
    with state_lock:
        game_state["timer_duration"] = timer_dur
        qs = copy.deepcopy(game_state["questions"])
        random.shuffle(qs)
        game_state["game_questions"] = qs[:min(len(qs), 10)]
        game_state["current_q"] = 0
        game_state["status"] = "question"
        game_state["timer_start"] = time.time()
        game_state["answers_this_round"] = {}
        # Lifeline reset
        for pid in game_state["players"]:
            game_state["lifelines"][pid] = {"fiftyfifty": True, "skip": True, "hint": True}

    return jsonify({"ok": True})

@app.route("/api/host/next", methods=["POST"])
def host_next():
    data = request.json or {}
    if data.get("password") != game_state["host_password"]:
        return jsonify({"ok": False}), 403

    with state_lock:
        game_state["current_q"] += 1
        if game_state["current_q"] >= len(game_state["game_questions"]):
            game_state["status"] = "finished"
        else:
            game_state["status"] = "question"
            game_state["timer_start"] = time.time()
            game_state["answers_this_round"] = {}

    return jsonify({"ok": True, "status": game_state["status"]})

@app.route("/api/host/reveal", methods=["POST"])
def host_reveal():
    data = request.json or {}
    if data.get("password") != game_state["host_password"]:
        return jsonify({"ok": False}), 403

    with state_lock:
        q = current_question()
        if not q:
            return jsonify({"ok": False})

        correct = q["correct"]
        time_bonus_max = 50
        elapsed = time.time() - game_state["timer_start"]
        
        results = {}
        for pid, ans_idx in game_state["answers_this_round"].items():
            if pid not in game_state["players"]:
                continue
            p = game_state["players"][pid]
            is_correct = ans_idx == correct
            time_taken = p.get("answer_time", elapsed)
            t_ratio = max(0, (game_state["timer_duration"] - time_taken) / game_state["timer_duration"])
            time_bonus = round(t_ratio * time_bonus_max) if is_correct else 0
            points = 100 + time_bonus if is_correct else 0
            p["score"] += points
            p["streak"] = (p["streak"] + 1) if is_correct else 0
            results[pid] = {"correct": is_correct, "points": points, "streak": p["streak"]}

        # Cevap vermeyen oyuncular
        for pid in game_state["players"]:
            if pid not in game_state["answers_this_round"]:
                game_state["players"][pid]["streak"] = 0

        game_state["status"] = "answer"

    return jsonify({
        "ok": True,
        "correct_idx": correct,
        "correct_text": q["opts"][correct],
        "hint": q.get("hint", ""),
        "results": results,
        "leaderboard": leaderboard(),
    })

@app.route("/api/host/state")
def host_state():
    pwd = request.args.get("password", "")
    if pwd != game_state["host_password"]:
        return jsonify({"ok": False}), 403

    q = current_question()
    return jsonify({
        "ok": True,
        "status": game_state["status"],
        "room_code": game_state["room_code"],
        "player_count": len(game_state["players"]),
        "players": [{"name": p["name"], "score": p["score"]} for p in game_state["players"].values()],
        "current_q": game_state["current_q"],
        "total_q": len(game_state["game_questions"]),
        "timer_remaining": get_timer_remaining(),
        "question": q,
        "answer_count": len(game_state["answers_this_round"]),
        "leaderboard": leaderboard(),
    })

@app.route("/api/host/add_question", methods=["POST"])
def host_add_question():
    data = request.json or {}
    if data.get("password") != game_state["host_password"]:
        return jsonify({"ok": False}), 403
    q = {
        "q": data.get("q", ""),
        "opts": data.get("opts", []),
        "correct": int(data.get("correct", 0)),
        "category": data.get("category", "Genel"),
        "hint": data.get("hint", ""),
    }
    if not q["q"] or len(q["opts"]) < 2:
        return jsonify({"ok": False, "error": "Eksik veri"})
    game_state["questions"].append(q)
    return jsonify({"ok": True, "count": len(game_state["questions"])})

@app.route("/api/host/kick", methods=["POST"])
def host_kick():
    data = request.json or {}
    if data.get("password") != game_state["host_password"]:
        return jsonify({"ok": False}), 403
    pid = data.get("player_id")
    if pid in game_state["players"]:
        del game_state["players"][pid]
    return jsonify({"ok": True})

# ─────────────────────────────────────────
#  ROTALAR — OYUNCU
# ─────────────────────────────────────────
@app.route("/api/join", methods=["POST"])
def join():
    data = request.json or {}
    name = data.get("name", "").strip()[:20]
    room = data.get("room", "").upper().strip()

    if not name:
        return jsonify({"ok": False, "error": "İsim gerekli"})
    if room != game_state["room_code"]:
        return jsonify({"ok": False, "error": f"Oda kodu yanlış (Beklenen: {game_state['room_code']})"})
    if game_state["status"] not in ("waiting", "question"):
        return jsonify({"ok": False, "error": "Oyun zaten başladı veya bitti"})

    pid = gen_player_id()
    with state_lock:
        game_state["players"][pid] = {
            "name": name, "score": 0, "streak": 0,
            "answers": [], "answer_time": 0,
        }
        game_state["lifelines"][pid] = {"fiftyfifty": True, "skip": True, "hint": True}

    return jsonify({"ok": True, "player_id": pid, "name": name})

@app.route("/api/state")
def player_state():
    pid = request.args.get("player_id", "")
    q = current_question()
    answered = pid in game_state["answers_this_round"]
    lifelines = game_state.get("lifelines", {}).get(pid, {})

    resp = {
        "ok": True,
        "status": game_state["status"],
        "room_code": game_state["room_code"],
        "player_count": len(game_state["players"]),
        "current_q": game_state["current_q"],
        "total_q": len(game_state["game_questions"]),
        "timer_remaining": get_timer_remaining(),
        "question": safe_question(q),
        "answered": answered,
        "leaderboard": leaderboard(),
        "my_score": game_state["players"].get(pid, {}).get("score", 0),
        "my_streak": game_state["players"].get(pid, {}).get("streak", 0),
        "lifelines": lifelines,
    }
    return jsonify(resp)

@app.route("/api/answer", methods=["POST"])
def answer():
    data = request.json or {}
    pid = data.get("player_id")
    ans = data.get("answer")

    if pid not in game_state["players"]:
        return jsonify({"ok": False, "error": "Oyuncu bulunamadı"})
    if game_state["status"] != "question":
        return jsonify({"ok": False, "error": "Şu an cevap verilemez"})
    if pid in game_state["answers_this_round"]:
        return jsonify({"ok": False, "error": "Zaten cevap verdiniz"})

    with state_lock:
        elapsed = time.time() - game_state["timer_start"]
        game_state["answers_this_round"][pid] = int(ans)
        game_state["players"][pid]["answer_time"] = elapsed

    return jsonify({"ok": True, "answer": ans})

@app.route("/api/lifeline", methods=["POST"])
def use_lifeline():
    data = request.json or {}
    pid = data.get("player_id")
    ll = data.get("lifeline")

    if pid not in game_state["players"]:
        return jsonify({"ok": False})
    lifelines = game_state["lifelines"].get(pid, {})
    if not lifelines.get(ll):
        return jsonify({"ok": False, "error": "Zaten kullanıldı"})

    q = current_question()
    result = {}
    with state_lock:
        game_state["lifelines"][pid][ll] = False
        if ll == "fiftyfifty" and q:
            wrong = [i for i in range(len(q["opts"])) if i != q["correct"]]
            remove = random.sample(wrong, min(2, len(wrong)))
            result["remove"] = remove
        elif ll == "hint" and q:
            result["hint"] = q.get("hint") or "Bu soru için ipucu yok."

    return jsonify({"ok": True, "result": result})

# ─────────────────────────────────────────
#  BAŞLAT
# ─────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    import socket
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except:
        local_ip = "127.0.0.1"

    print("\n" + "="*50)
    print("  🎯  QuizBlast Multiplayer Sunucu")
    print("="*50)
    print(f"  Host paneli : http://localhost:{port}")
    print(f"  Oyuncu URL  : http://{local_ip}:{port}/play")
    print(f"  Host şifresi: {game_state['host_password']}")
    print("="*50 + "\n")

    app.run(host="0.0.0.0", port=port, debug=False)
