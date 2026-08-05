import os
import json
import sqlite3
import random
from datetime import datetime
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ── Config (masked secrets read from env with safe defaults) ──────────────
DB_PATH = os.environ.get("DB_PATH", "luna.db")
MANAGER_USERNAME = os.environ.get("MANAGER_USERNAME", "manager")
# Crypto wallet addresses substituted into the HTML (placeholders __USDT__/__TON__)
USDT_ADDRESS = os.environ.get("USDT_ADDRESS", "TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
TON_ADDRESS = os.environ.get("TON_ADDRESS", "UQXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

DEMO_PHOTOS = [
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=600&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=600&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=400&h=600&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=400&h=600&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400&h=600&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=400&h=600&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1496440737103-cd596325d314?w=400&h=600&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=400&h=600&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=600&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1521146764736-56c929d59c83?w=400&h=600&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1504703395950-b89145a5425b?w=400&h=600&fit=crop&crop=face",
    "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?w=400&h=600&fit=crop&crop=face",
]

DEMO_NAMES = ["София", "Виктория", "Алиса", "Милана", "Валерия", "Кристина",
              "Камилла", "Эмилия", "Николь", "Ариана", "Стефания", "Аделина"]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manager_id INTEGER DEFAULT 0,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        height INTEGER,
        bust INTEGER,
        city TEXT NOT NULL,
        description TEXT,
        price_1h INTEGER NOT NULL,
        price_2h INTEGER,
        price_night INTEGER,
        main_photo TEXT DEFAULT '',
        gallery TEXT DEFAULT '[]',
        is_active INTEGER DEFAULT 1,
        is_verified INTEGER DEFAULT 0,
        tags TEXT DEFAULT '[]',
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_tg_id INTEGER,
        client_username TEXT,
        model_id INTEGER,
        model_name TEXT,
        duration TEXT,
        price INTEGER,
        payment_method TEXT,
        contact_method TEXT DEFAULT 'bot',
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id INTEGER,
        client_name TEXT,
        rating INTEGER,
        text TEXT,
        is_verified INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS cities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        is_active INTEGER DEFAULT 1
    )""")
    for city in ["Москва", "Санкт-Петербург", "Дубай", "Алматы", "Астана", "Екатеринбург"]:
        conn.execute("INSERT OR IGNORE INTO cities (name) VALUES (?)", (city,))
    conn.commit()
    conn.close()


init_db()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/api/cities")
def api_cities():
    db = get_db()
    cities = [dict(r) for r in db.execute("SELECT * FROM cities WHERE is_active=1 ORDER BY name").fetchall()]
    for c in cities:
        count = db.execute("SELECT COUNT(*) as cnt FROM models WHERE city=? AND is_active=1", (c['name'],)).fetchone()
        c['models_count'] = count['cnt'] if count else 0
    db.close()
    return jsonify(cities)


@app.route("/api/models/<city>")
def api_models(city):
    db = get_db()
    query = "SELECT * FROM models WHERE city=? AND is_active=1"
    params = [city]
    for f, op in [('price_min', '>='), ('price_max', '<='), ('age_min', '>='), ('age_max', '<=')]:
        v = request.args.get(f)
        if v:
            field = 'price_1h' if 'price' in f else 'age'
            query += f" AND {field} {op} ?"
            params.append(int(v))
    query += " ORDER BY is_verified DESC, created_at DESC"
    models = [dict(r) for r in db.execute(query, params).fetchall()]
    for i, m in enumerate(models):
        if not m.get('main_photo'):
            m['main_photo'] = DEMO_PHOTOS[i % len(DEMO_PHOTOS)]
        try:
            m['tags'] = json.loads(m.get('tags', '[]'))
        except:
            m['tags'] = []
        try:
            m['gallery'] = json.loads(m.get('gallery', '[]'))
        except:
            m['gallery'] = []
    db.close()
    return jsonify(models)


@app.route("/api/model/<int:model_id>")
def api_model(model_id):
    db = get_db()
    row = db.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Not found"}), 404
    m = dict(row)
    db.execute("UPDATE models SET views=views+1 WHERE id=?", (model_id,))
    db.commit()
    if not m.get('main_photo'):
        m['main_photo'] = DEMO_PHOTOS[model_id % len(DEMO_PHOTOS)]
    try:
        m['tags'] = json.loads(m.get('tags', '[]'))
    except:
        m['tags'] = []
    try:
        m['gallery'] = json.loads(m.get('gallery', '[]'))
    except:
        m['gallery'] = []
    reviews = [dict(r) for r in db.execute("SELECT * FROM reviews WHERE model_id=? ORDER BY created_at DESC", (model_id,)).fetchall()]
    m['reviews'] = reviews
    db.close()
    return jsonify(m)


@app.route("/api/like/<int:model_id>", methods=["POST"])
def api_like(model_id):
    db = get_db()
    db.execute("UPDATE models SET likes=likes+1 WHERE id=?", (model_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})


@app.route("/api/booking", methods=["POST"])
def api_booking():
    data = request.json
    db = get_db()
    cur = db.execute(
        "INSERT INTO bookings (client_tg_id, client_username, model_id, model_name, duration, price, payment_method, contact_method, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (data.get('client_id', 0), data.get('client_username', ''),
         data.get('model_id'), data.get('model_name', ''),
         data.get('duration', '1 час'), data.get('price', 0),
         data.get('payment_method', 'manager'),
         data.get('contact_method', 'bot'),
         datetime.now().isoformat())
    )
    db.commit()
    booking_id = cur.lastrowid
    db.close()
    return jsonify({"booking_id": booking_id, "status": "pending"})


@app.route("/api/seed-demo", methods=["GET", "POST"])
def seed_demo():
    db = get_db()
    db.execute("DELETE FROM models")
    db.execute("DELETE FROM reviews")
    cities = ["Москва", "Санкт-Петербург", "Дубай", "Алматы", "Екатеринбург"]
    descs = [
        "Обворожительная девушка, которая покорит вас с первого взгляда. Утончённая натура, безупречный стиль и умение создать атмосферу настоящего удовольствия.",
        "Воплощение элегантности и женственности. Изысканные манеры и врождённое чувство стиля. Составит великолепную компанию.",
        "Яркая, харизматичная и невероятно привлекательная. С ней каждый момент становится особенным. Чувственная и раскрепощённая.",
        "Роскошная и утончённая. Умеет создавать атмосферу настоящего праздника и подарит незабываемые впечатления.",
    ]
    for i in range(12):
        name = DEMO_NAMES[i % len(DEMO_NAMES)]
        age = random.randint(18, 27)
        city = random.choice(cities)
        price = random.choice([3000, 4000, 5000, 6000, 7000, 8000, 10000, 12000])
        desc = f"{name} — {random.choice(descs)}"
        tags = []
        if random.random() > 0.6:
            tags.append("Новинка")
        if random.random() > 0.8:
            tags.append("Горящая")
        db.execute(
            "INSERT INTO models (name, age, height, bust, city, description, price_1h, price_2h, price_night, main_photo, tags, is_verified, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (name, age, random.randint(160, 178), random.randint(1, 4),
             city, desc, price, int(price * 1.8), price * 5,
             DEMO_PHOTOS[i % len(DEMO_PHOTOS)],
             json.dumps(tags), 1 if random.random() > 0.4 else 0,
             datetime.now().isoformat())
        )
    models = db.execute("SELECT id FROM models").fetchall()
    review_texts = [
        ("Арсений", "Всё на высшем уровне. Рекомендую всем!"),
        ("Евгений", "Очень доволен, всё анонимно и быстро."),
        ("Инкогнито", "Девушка точно как на фото. Буду обращаться ещё."),
        ("Максим", "Потрясающий сервис. Всё чётко и без проблем."),
        ("Дмитрий", "Идеальный вечер. Спасибо LUNA!"),
        ("Александр", "Отличная модель, вежливая и красивая."),
    ]
    for m in models:
        for _ in range(random.randint(1, 3)):
            n, t = random.choice(review_texts)
            db.execute(
                "INSERT INTO reviews (model_id, client_name, rating, text, is_verified, created_at) VALUES (?,?,?,?,?,?)",
                (m['id'], n, 5, t, 1, datetime.now().isoformat())
            )
    db.commit()
    db.close()
    return jsonify({"ok": True, "message": "12 demo models + reviews created"})


@app.route("/")
def index():
    html = (WEBAPP_HTML
            .replace("__MGR__", MANAGER_USERNAME)
            .replace("__USDT__", USDT_ADDRESS)
            .replace("__TON__", TON_ADDRESS))
    return Response(html, mimetype="text/html")


WEBAPP_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>LUNA ESCORT</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;800&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent;-webkit-touch-callout:none}
:root{
  --bg:#0B0D1A;--bg2:#141628;--card:#1A1D30;--card2:#22263D;--card3:#2A2E48;
  --gold:#E5B547;--purple:#8B5CF6;--cyan:#22D3EE;--pink:#EC4899;--blue:#3B82F6;
  --green:#10B981;--red:#EF4444;--orange:#F97316;
  --t1:#FFFFFF;--t2:#B4B9D3;--t3:#6B7290;--t4:#4A5074;
  --border:rgba(255,255,255,.05);--border2:rgba(139,92,246,.15);
  --r:14px;--r2:20px;--rf:100px;
  --grad:linear-gradient(135deg,#8B5CF6,#EC4899,#22D3EE);
  --grad2:linear-gradient(135deg,#8B5CF6,#E5B547);
  --shadow:0 8px 24px rgba(0,0,0,.4);
  --glow:0 0 40px rgba(139,92,246,.25);
  --hero-glow:radial-gradient(ellipse at top,#1a1837 0%,var(--bg) 45%);
}
html.light{
  --bg:#F5F5FB;--bg2:#FFFFFF;--card:#FFFFFF;--card2:#F0EEF9;--card3:#E6E3F3;
  --t1:#16151F;--t2:#4C4C63;--t3:#8A8AA3;--t4:#B7B7CC;
  --border:rgba(20,20,40,.07);--border2:rgba(139,92,246,.22);
  --shadow:0 8px 24px rgba(90,80,150,.12);
  --hero-glow:radial-gradient(ellipse at top,#ede8ff 0%,var(--bg) 50%);
}
html,body{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--t1);min-height:100vh;overflow-x:hidden;-webkit-font-smoothing:antialiased;transition:background .4s ease,color .4s ease}
body{background:var(--hero-glow) fixed}
.screen{display:none;min-height:100vh;padding-bottom:90px;animation:fadeIn .35s ease}
.screen.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(1.15)}}
@keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
@keyframes bounceIn{0%{transform:scale(.4);opacity:0}60%{transform:scale(1.15)}100%{transform:scale(1);opacity:1}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes floaty{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}

/* ===== TOP BAR ===== */
.top{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;position:sticky;top:0;z-index:100;background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border-bottom:1px solid var(--border)}
.top-l{display:flex;align-items:center;gap:10px}
.top-badge{display:flex;align-items:center;gap:8px;padding:6px 12px;background:var(--card);border:1px solid var(--border2);border-radius:var(--rf)}
.top-badge-icon{width:22px;height:22px;background:var(--grad2);border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff}
.top-badge-icon svg{width:13px;height:13px}
.top-badge-txt{font-family:'Playfair Display',serif;font-weight:700;font-size:13px;letter-spacing:2px}
.top-city{display:flex;align-items:center;gap:6px;padding:6px 12px;background:var(--card);border:1px solid var(--border);border-radius:var(--rf);font-size:12px;font-weight:500;color:var(--t2)}
.top-city .dot{width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;box-shadow:0 0 8px var(--green)}
.top-city-cnt{color:var(--green);font-weight:700}
.top-city svg{width:12px;height:12px;opacity:.7}
.btn-i{background:none;border:none;color:var(--t2);cursor:pointer;padding:8px;border-radius:10px;transition:.2s;display:flex;align-items:center;justify-content:center}
.btn-i:active{background:color-mix(in srgb,var(--t1) 8%,transparent);transform:scale(.92)}
.btn-i svg{width:20px;height:20px}

/* ===== PULL TO REFRESH ===== */
.ptr{position:absolute;top:0;left:0;right:0;display:flex;align-items:center;justify-content:center;height:0;overflow:hidden;color:var(--purple);pointer-events:none;z-index:1}
.ptr svg{width:24px;height:24px}
.ptr.spin svg{animation:spin .7s linear infinite}

/* ===== CITY SCREEN ===== */
.hero{text-align:center;padding:44px 20px 20px;position:relative}
.hero::before{content:'';position:absolute;top:-20px;left:50%;transform:translateX(-50%);width:420px;height:420px;background:radial-gradient(circle,rgba(139,92,246,.18) 0%,transparent 60%);pointer-events:none;z-index:-1}
.brand{font-family:'Playfair Display',serif;font-size:56px;font-weight:700;letter-spacing:12px;background:var(--grad2);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:4px}
.sub{font-size:11px;letter-spacing:6px;color:var(--t3);font-weight:500}
.online{display:inline-flex;align-items:center;gap:10px;margin-top:22px;padding:10px 18px;background:var(--card);border:1px solid var(--border2);border-radius:var(--rf);font-size:12px;color:var(--t2);font-weight:500}
.online b{color:var(--green);font-weight:700}
.online .odot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;box-shadow:0 0 8px var(--green)}
.stitle{font-size:11px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--t3);padding:0 22px;margin:26px 0 12px}
.cities{padding:0 16px;display:flex;flex-direction:column;gap:10px}
.city-c{display:flex;align-items:center;justify-content:space-between;padding:18px 20px;background:var(--card);border-radius:var(--r2);cursor:pointer;border:1px solid var(--border);transition:.25s;position:relative;overflow:hidden}
.city-c::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--grad);opacity:0;transition:.3s}
.city-c:active{transform:scale(.98);background:var(--card2);border-color:var(--border2)}
.city-c:active::before{opacity:1}
.city-l2{display:flex;align-items:center;gap:14px}
.city-icon{width:42px;height:42px;background:rgba(139,92,246,.12);border-radius:12px;display:flex;align-items:center;justify-content:center;color:var(--purple)}
.city-icon svg{width:20px;height:20px}
.city-n{font-size:16px;font-weight:600}
.city-cnt{font-size:12px;color:var(--t3);margin-top:2px;font-weight:500}
.city-cnt b{color:var(--gold);font-weight:700}
.city-arr{color:var(--t3);display:flex}
.city-arr svg{width:18px;height:18px}
.foot{display:flex;justify-content:center;align-items:center;gap:16px;padding:30px 20px;font-size:10px;color:var(--t4);letter-spacing:1px}
.foot span{display:flex;align-items:center;gap:5px}

/* ===== SEARCH ===== */
.sbar{display:flex;align-items:center;gap:10px;padding:14px 16px}
.swrap{flex:1;display:flex;align-items:center;background:var(--card);border-radius:var(--rf);padding:12px 18px;border:1px solid var(--border);transition:.2s}
.swrap:focus-within{border-color:var(--purple);box-shadow:0 0 0 4px rgba(139,92,246,.1)}
.swrap svg{margin-right:10px;opacity:.5;flex-shrink:0}
.swrap input{background:none;border:none;color:var(--t1);font-size:14px;width:100%;outline:none;font-family:inherit}
.swrap input::placeholder{color:var(--t3)}
.btn-f{background:var(--card);border:1px solid var(--border);color:var(--t2);width:46px;height:46px;border-radius:var(--r);cursor:pointer;display:flex;align-items:center;justify-content:center;transition:.2s}
.btn-f.on{color:var(--pink);border-color:var(--border2)}
.btn-f:active{background:var(--card2);color:var(--purple);transform:scale(.95)}

/* ===== GRID ===== */
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;padding:0 12px}
.card{position:relative;border-radius:var(--r2);overflow:hidden;cursor:pointer;aspect-ratio:3/4;background:var(--card);box-shadow:var(--shadow);transition:.2s;animation:fadeIn .4s ease both}
.card:active{transform:scale(.96)}
.card img{width:100%;height:100%;object-fit:cover}
.card-tags{position:absolute;top:10px;left:10px;display:flex;flex-direction:column;gap:5px;z-index:2}
.tag{display:inline-flex;align-items:center;gap:3px;padding:4px 9px;border-radius:var(--rf);font-size:9px;font-weight:800;color:#fff;letter-spacing:.5px;backdrop-filter:blur(10px);text-transform:uppercase;box-shadow:0 2px 8px rgba(0,0,0,.3)}
.tag svg{width:9px;height:9px}
.tag-v{background:linear-gradient(135deg,#22D3EE,#3B82F6)}
.tag-n{background:linear-gradient(135deg,#8B5CF6,#EC4899)}
.tag-h{background:linear-gradient(135deg,#F97316,#EF4444)}
.card-like{position:absolute;top:10px;right:10px;background:rgba(0,0,0,.45);backdrop-filter:blur(10px);border:none;color:#fff;cursor:pointer;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;transition:.2s;z-index:2}
.card-like svg{width:16px;height:16px}
.card-like:active{transform:scale(1.25)}
.card-like.liked{background:rgba(236,72,153,.35);color:#EC4899}
.card-like.liked svg{fill:#EC4899}
.card-info{position:absolute;bottom:0;left:0;right:0;padding:40px 12px 12px;background:linear-gradient(transparent,rgba(0,0,0,.9))}
.card-name{font-family:'Playfair Display',serif;font-size:16px;font-weight:600;display:flex;align-items:center;gap:5px;line-height:1.2;color:#fff}
.vb{color:var(--cyan);display:inline-flex}
.vb svg{width:13px;height:13px}
.card-meta{display:flex;align-items:center;gap:6px;margin-top:5px;font-size:11px;color:#c9cde0}
.card-price{color:var(--gold);font-weight:700;font-size:12px}
.card-id{position:absolute;bottom:10px;right:10px;background:rgba(0,0,0,.55);backdrop-filter:blur(10px);padding:3px 8px;border-radius:var(--rf);font-size:9px;color:#c9cde0;font-weight:600;letter-spacing:.3px}

/* ===== SKELETON ===== */
.sk{position:relative;border-radius:var(--r2);overflow:hidden;aspect-ratio:3/4;background:var(--card)}
.sk::after{content:'';position:absolute;inset:0;background:linear-gradient(90deg,transparent,color-mix(in srgb,var(--t1) 7%,transparent),transparent);background-size:200% 100%;animation:shimmer 1.3s infinite}

/* ===== MODEL DETAIL ===== */
.det{min-height:100vh;padding-bottom:110px}
.slider{position:relative;width:100%;aspect-ratio:3/4;overflow:hidden;background:var(--card)}
.slider img{width:100%;height:100%;object-fit:cover;will-change:transform}
.slider-ov{position:absolute;bottom:0;left:0;right:0;padding:60px 20px 20px;background:linear-gradient(transparent,rgba(11,13,26,.98));z-index:3}
.slider-nav{position:absolute;top:16px;left:0;right:0;display:flex;justify-content:space-between;padding:0 14px;z-index:10}
.slider-btn{background:rgba(0,0,0,.5);backdrop-filter:blur(10px);border:none;color:#fff;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:.2s}
.slider-btn svg{width:20px;height:20px}
.slider-btn.liked svg{fill:#EC4899;stroke:#EC4899}
.slider-btn:active{transform:scale(.9)}
.det-name{font-family:'Playfair Display',serif;font-size:30px;font-weight:700;display:flex;align-items:center;gap:8px;line-height:1;color:#fff}
.det-id{font-size:14px;color:#9aa0bd;font-weight:500;font-family:'Inter',sans-serif;margin-left:auto}
.det-stats{display:flex;gap:14px;margin-top:10px;font-size:12px;color:#c9cde0}
.det-stats span{display:flex;align-items:center;gap:5px}
.det-stats svg{width:14px;height:14px;opacity:.85}

.infos{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:16px}
.info{background:var(--card);border-radius:var(--r);padding:14px 8px;text-align:center;border:1px solid var(--border);transition:.2s}
.info:active{transform:scale(.97);border-color:var(--border2)}
.info-l{font-size:9px;color:var(--t3);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;font-weight:600}
.info-v{font-size:18px;font-weight:800}
.info-v.price{color:var(--gold);font-size:14px}

.sec{padding:18px 16px}
.sec-t{display:flex;align-items:center;gap:10px;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--gold);margin-bottom:12px}
.sec-t::before{content:'';width:20px;height:2px;background:var(--grad2);border-radius:2px}
.desc{font-size:14px;line-height:1.75;color:var(--t2)}

.gscroll{display:flex;gap:10px;overflow-x:auto;padding:0 16px 10px;scrollbar-width:none}
.gscroll::-webkit-scrollbar{display:none}
.gitem{flex:0 0 130px;height:170px;border-radius:var(--r);overflow:hidden;position:relative;cursor:pointer}
.gitem img{width:100%;height:100%;object-fit:cover;filter:blur(20px) brightness(.5)}
.glock{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;color:var(--gold)}
.glock svg{width:22px;height:22px}
.glock-t{font-size:9px;letter-spacing:2px;font-weight:700}

/* ===== PRICE LIST ===== */
.plist{display:flex;flex-direction:column;gap:8px;padding:0 16px}
.pitem{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;background:var(--card);border-radius:var(--r);border:1px solid var(--border);cursor:pointer;transition:.2s;position:relative;overflow:hidden}
.pitem::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--grad);opacity:0;transition:.3s}
.pitem.sel{border-color:var(--purple);background:linear-gradient(135deg,rgba(139,92,246,.1),rgba(236,72,153,.05));box-shadow:var(--glow)}
.pitem.sel::before{opacity:1}
.pitem:active{transform:scale(.98)}
.pitem-l{display:flex;align-items:center;gap:12px}
.pitem-ic{width:36px;height:36px;background:rgba(229,181,71,.1);border-radius:10px;display:flex;align-items:center;justify-content:center;color:var(--gold)}
.pitem-ic svg{width:18px;height:18px}
.pitem-n{font-size:15px;font-weight:600}
.pitem-r{display:flex;align-items:center;gap:12px}
.pitem-c{font-size:16px;font-weight:800;color:var(--gold)}
.pradio{width:22px;height:22px;border-radius:50%;border:2px solid var(--t3);display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:.2s}
.pitem.sel .pradio{border-color:var(--purple);background:var(--purple);box-shadow:0 0 12px rgba(139,92,246,.5)}
.pitem.sel .pradio::after{content:'';width:8px;height:8px;border-radius:50%;background:#fff}

/* ===== BOOK BUTTON ===== */
.bookwrap{padding:20px 16px calc(20px + env(safe-area-inset-bottom));position:fixed;bottom:0;left:0;right:0;background:linear-gradient(transparent,var(--bg) 35%);z-index:50}
.btn-book{width:100%;padding:18px;border:none;border-radius:var(--rf);background:var(--grad);color:#fff;font-size:15px;font-weight:800;letter-spacing:2px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;box-shadow:0 8px 32px rgba(139,92,246,.5);transition:.2s;text-transform:uppercase}
.btn-book svg{width:18px;height:18px}
.btn-book:active{transform:scale(.97);box-shadow:0 4px 16px rgba(139,92,246,.4)}

/* ===== REVIEWS ===== */
.rev{background:var(--card);border-radius:var(--r);padding:16px;margin-bottom:10px;border:1px solid var(--border)}
.rev-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.rev-u{display:flex;align-items:center;gap:10px}
.rev-av{width:36px;height:36px;border-radius:50%;background:var(--grad2);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px;color:#fff}
.rev-n{font-weight:600;font-size:13px}
.rev-d{font-size:11px;color:var(--t3);font-weight:500}
.rev-s{color:var(--gold);font-size:14px;margin-bottom:8px;letter-spacing:2px}
.rev-t{font-size:13px;color:var(--t2);line-height:1.6;padding-left:12px;border-left:3px solid var(--purple);font-style:italic}

/* ===== MODAL ===== */
.modal{display:none;position:fixed;inset:0;z-index:200}
.modal.active{display:block}
.modal-ov{position:absolute;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(6px)}
.bsheet{position:absolute;bottom:0;left:0;right:0;background:var(--bg2);border-radius:var(--r2) var(--r2) 0 0;padding:24px 20px calc(40px + env(safe-area-inset-bottom));animation:slideUp .35s cubic-bezier(.2,.9,.3,1);max-height:88vh;overflow-y:auto;box-shadow:0 -12px 40px rgba(0,0,0,.6)}
.bsheet::before{content:'';display:block;width:40px;height:4px;background:var(--t4);border-radius:4px;margin:0 auto 20px}
.modal-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:22px}
.modal-h h3{font-family:'Playfair Display',serif;font-size:24px;font-weight:600}

/* ===== FILTERS ===== */
.fg{margin-bottom:18px}
.fg label{font-size:10px;font-weight:700;letter-spacing:2px;color:var(--t3);margin-bottom:10px;display:block;text-transform:uppercase}
.frow{display:flex;align-items:center;gap:12px}
.finp{flex:1;background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:14px 16px;color:var(--t1);font-size:15px;font-family:inherit;outline:none;transition:.2s;font-weight:500}
.finp:focus{border-color:var(--purple);background:var(--card2)}
.finp::placeholder{color:var(--t3)}
.factions{display:flex;gap:12px;margin-top:24px}
.btn-res{flex:1;padding:16px;border:none;border-radius:var(--rf);background:var(--card);color:var(--t2);font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;letter-spacing:1.5px;transition:.2s}
.btn-res:active{background:var(--card2);transform:scale(.98)}
.btn-app{flex:2;padding:16px;border:none;border-radius:var(--rf);background:var(--grad2);color:#fff;font-size:13px;font-weight:800;cursor:pointer;font-family:inherit;letter-spacing:1.5px;box-shadow:0 4px 16px rgba(139,92,246,.3);transition:.2s}
.btn-app:active{transform:scale(.98)}

/* ===== PAYMENT ===== */
.pay-amt{background:linear-gradient(135deg,var(--card),var(--card2));border-radius:var(--r2);padding:24px;text-align:center;margin-bottom:22px;border:1px solid var(--border2);position:relative;overflow:hidden}
.pay-amt::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle,rgba(139,92,246,.15) 0%,transparent 40%);pointer-events:none}
.pay-lbl{font-size:10px;letter-spacing:2px;color:var(--t3);font-weight:700;margin-bottom:8px;text-transform:uppercase;position:relative}
.pay-p{font-family:'Playfair Display',serif;font-size:36px;font-weight:800;color:var(--gold);position:relative;line-height:1}
.pay-d{font-size:13px;color:var(--cyan);margin-top:8px;font-weight:600;position:relative}

.pmethods{display:flex;flex-direction:column;gap:8px}
.pm{display:flex;align-items:center;gap:14px;padding:14px 16px;background:var(--card);border:1px solid var(--border);border-radius:var(--r);cursor:pointer;color:var(--t1);font-family:inherit;text-align:left;width:100%;transition:.2s}
.pm:active{background:var(--card2);border-color:var(--purple);transform:scale(.98)}
.pm-i{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.pm-i svg{width:20px;height:20px}
.pm-i.balance{background:rgba(34,211,238,.12);color:var(--cyan)}
.pm-i.card{background:rgba(139,92,246,.12);color:var(--purple)}
.pm-i.crypto{background:rgba(249,115,22,.12);color:var(--orange)}
.pm-i.mgr{background:rgba(59,130,246,.12);color:var(--blue)}
.pm-info{flex:1;display:flex;flex-direction:column}
.pm-n{font-size:15px;font-weight:600}
.pm-h{font-size:10px;color:var(--green);font-weight:700;letter-spacing:1px;margin-top:2px}
.pm-a{color:var(--t3);display:flex}
.pm-a svg{width:18px;height:18px}

/* ===== CONTACT METHOD ===== */
.contact-title{font-size:10px;font-weight:700;letter-spacing:2px;color:var(--t3);margin:20px 0 10px;text-transform:uppercase;display:flex;align-items:center;gap:8px}
.contact-title::before{content:'';width:16px;height:2px;background:var(--purple);border-radius:2px}
.contact-opts{display:flex;flex-direction:column;gap:8px;margin-bottom:18px}
.c-opt{display:flex;align-items:center;gap:12px;padding:14px 16px;background:var(--card);border:1px solid var(--border);border-radius:var(--r);cursor:pointer;color:var(--t1);font-family:inherit;text-align:left;width:100%;font-size:13px;transition:.2s}
.c-opt.sel{border-color:var(--purple);background:linear-gradient(135deg,rgba(139,92,246,.1),transparent)}
.c-opt:active{transform:scale(.98)}
.c-radio{width:20px;height:20px;border-radius:50%;border:2px solid var(--t3);display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:.2s}
.c-opt.sel .c-radio{border-color:var(--purple);background:var(--purple);box-shadow:0 0 12px rgba(139,92,246,.5)}
.c-opt.sel .c-radio::after{content:'';width:7px;height:7px;border-radius:50%;background:#fff}
.c-ic{width:32px;height:32px;background:var(--card2);border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--t2);flex-shrink:0}
.c-ic svg{width:16px;height:16px}
.c-info{flex:1}
.c-name{font-weight:600;font-size:14px}
.c-hint{font-size:11px;color:var(--t3);margin-top:2px;font-weight:500}

/* ===== CRYPTO GRID ===== */
.crypto-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}
.crypto-c{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:22px 12px;display:flex;flex-direction:column;align-items:center;gap:10px;cursor:pointer;transition:.2s}
.crypto-c:active{border-color:var(--purple);background:var(--card2);transform:scale(.97)}
.crypto-ic{width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:900;color:#fff}
.crypto-ic svg{width:26px;height:26px}
.crypto-ic.usdt{background:linear-gradient(135deg,#26A17B,#0F7A5A)}
.crypto-ic.btc{background:linear-gradient(135deg,#F7931A,#E27913)}
.crypto-ic.ton{background:linear-gradient(135deg,#3B82F6,#2563EB)}
.crypto-ic.eth{background:linear-gradient(135deg,#8B5CF6,#6D28D9)}
.crypto-n{font-size:13px;font-weight:800;letter-spacing:1px}
.crypto-addr{display:none;margin-top:16px}
.crypto-addr.show{display:block;animation:fadeIn .3s ease}
.addr-lbl{font-size:10px;font-weight:700;letter-spacing:2px;color:var(--t3);text-transform:uppercase;margin-bottom:8px}
.addr-box{display:flex;align-items:center;gap:10px;background:var(--card);border:1px solid var(--border2);border-radius:var(--r);padding:14px 16px;word-break:break-all;font-size:13px;color:var(--t1);font-weight:500}
.addr-copy{margin-top:12px;width:100%;padding:15px;border:none;border-radius:var(--rf);background:var(--grad2);color:#fff;font-size:13px;font-weight:800;letter-spacing:1.5px;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:8px}
.addr-copy svg{width:16px;height:16px}
.addr-copy:active{transform:scale(.98)}
.addr-done{margin-top:10px;width:100%;padding:15px;border:1px solid var(--green);border-radius:var(--rf);background:transparent;color:var(--green);font-size:13px;font-weight:700;letter-spacing:1px;cursor:pointer;font-family:inherit}
.addr-done:active{transform:scale(.98)}

/* ===== BOTTOM BAR ===== */
.bbar{position:fixed;bottom:0;left:0;right:0;display:flex;background:color-mix(in srgb,var(--bg) 90%,transparent);backdrop-filter:blur(24px);border-top:1px solid var(--border);z-index:100;padding:10px 0 max(10px,env(safe-area-inset-bottom))}
.bbtn{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px;background:none;border:none;color:var(--t3);cursor:pointer;font-family:inherit;transition:.2s;position:relative}
.bbtn.active{color:var(--cyan)}
.bbtn.active::after{content:'';position:absolute;bottom:0;width:4px;height:4px;border-radius:50%;background:var(--cyan);box-shadow:0 0 8px var(--cyan)}
.bbtn svg{width:22px;height:22px}
.bbtn small{font-size:10px;font-weight:600}

/* ===== PROFILE ===== */
.prof-hero{padding:30px 20px 20px;text-align:center}
.prof-av-wrap{position:relative;display:inline-block;margin-bottom:16px}
.prof-av{width:120px;height:120px;border-radius:50%;background:var(--grad);padding:3px}
.prof-av-inner{width:100%;height:100%;border-radius:50%;background:var(--bg);display:flex;align-items:center;justify-content:center;overflow:hidden;font-size:44px;font-weight:800;color:var(--t1)}
.prof-av-inner img{width:100%;height:100%;object-fit:cover}
.prof-name{font-family:'Playfair Display',serif;font-size:26px;font-weight:700;margin-bottom:4px}
.prof-meta{font-size:12px;color:var(--t3);font-weight:500}
.prof-meta b{color:var(--purple)}

.prof-balance{margin:24px 16px 0;background:var(--card);border:1px solid var(--border2);border-radius:var(--r2);padding:20px;text-align:center;position:relative;overflow:hidden}
.prof-balance::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle,rgba(34,211,238,.1) 0%,transparent 40%);pointer-events:none}
.pb-lbl{font-size:10px;letter-spacing:2px;color:var(--t3);font-weight:700;text-transform:uppercase;margin-bottom:8px;position:relative}
.pb-v{font-family:'Playfair Display',serif;font-size:36px;font-weight:800;color:var(--gold);margin-bottom:16px;position:relative}
.pb-btn{width:100%;padding:14px;border:none;border-radius:var(--rf);background:var(--card2);color:var(--t1);font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:6px;transition:.2s;position:relative}
.pb-btn svg{width:16px;height:16px}
.pb-btn:active{background:var(--card3);transform:scale(.98)}

.set-list{margin-top:20px;padding:0 16px;display:flex;flex-direction:column;gap:8px}
.set-item{display:flex;align-items:center;gap:14px;padding:16px 18px;background:var(--card);border:1px solid var(--border);border-radius:var(--r)}
.set-icon{width:36px;height:36px;background:var(--card2);border-radius:10px;display:flex;align-items:center;justify-content:center;color:var(--t2)}
.set-icon svg{width:18px;height:18px}
.set-name{flex:1;font-size:14px;font-weight:600}
.set-cnt{color:var(--gold);font-weight:700;font-size:14px}
.toggle{position:relative;width:46px;height:26px;background:var(--card3);border-radius:13px;cursor:pointer;transition:.2s;flex-shrink:0}
.toggle.on{background:var(--green)}
.toggle::after{content:'';position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:#fff;transition:.2s;box-shadow:0 2px 4px rgba(0,0,0,.3)}
.toggle.on::after{left:23px}

.hist-empty{margin:24px 16px 0;background:var(--card);border:2px dashed var(--border);border-radius:var(--r2);padding:36px 20px;text-align:center}
.hist-icon{color:var(--t3);margin-bottom:10px;display:flex;justify-content:center}
.hist-icon svg{width:34px;height:34px}
.hist-txt{font-size:13px;color:var(--t3);font-weight:500}

.support-btn{margin:20px 16px calc(20px + env(safe-area-inset-bottom));padding:16px;border:1px solid var(--purple);border-radius:var(--rf);background:transparent;color:var(--t1);font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:8px;width:calc(100% - 32px);transition:.2s}
.support-btn svg{width:18px;height:18px}
.support-btn:active{background:rgba(139,92,246,.1);transform:scale(.98)}

/* ===== EMPTY STATE ===== */
.empty{text-align:center;padding:56px 24px;grid-column:1/-1}
.empty-ill{width:132px;height:132px;margin:0 auto 20px;animation:floaty 4s ease-in-out infinite}
.empty-t{font-size:16px;color:var(--t1);font-weight:700;margin-bottom:6px}
.empty-s{font-size:13px;color:var(--t3);font-weight:500}

/* ===== ONBOARDING ===== */
.onb{position:fixed;inset:0;z-index:500;background:var(--hero-glow);background-color:var(--bg);display:none;flex-direction:column}
.onb.active{display:flex;animation:fadeIn .4s ease}
.onb-skip{position:absolute;top:calc(14px + env(safe-area-inset-top));right:18px;background:none;border:none;color:var(--t3);font-size:13px;font-weight:600;font-family:inherit;cursor:pointer;padding:8px;z-index:2}
.onb-track{flex:1;display:flex;overflow:hidden}
.onb-slide{min-width:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 34px;transition:opacity .4s ease}
.onb-ic{width:150px;height:150px;border-radius:38px;display:flex;align-items:center;justify-content:center;margin-bottom:36px;color:#fff;box-shadow:var(--glow);animation:floaty 4s ease-in-out infinite}
.onb-ic.a{background:var(--grad2)}
.onb-ic.b{background:linear-gradient(135deg,#22D3EE,#3B82F6)}
.onb-ic.c{background:linear-gradient(135deg,#EC4899,#8B5CF6)}
.onb-ic svg{width:66px;height:66px}
.onb-t{font-family:'Playfair Display',serif;font-size:30px;font-weight:700;margin-bottom:14px;line-height:1.15;max-width:300px}
.onb-d{font-size:15px;color:var(--t2);line-height:1.6;max-width:300px}
.onb-foot{padding:24px 24px calc(30px + env(safe-area-inset-bottom));display:flex;flex-direction:column;align-items:center;gap:22px}
.onb-dots{display:flex;gap:8px}
.onb-dot{width:8px;height:8px;border-radius:50%;background:var(--card3);transition:.3s}
.onb-dot.on{width:26px;background:var(--grad2);border-radius:4px}
.onb-btn{width:100%;padding:18px;border:none;border-radius:var(--rf);background:var(--grad);color:#fff;font-size:15px;font-weight:800;letter-spacing:1.5px;cursor:pointer;font-family:inherit;box-shadow:0 8px 32px rgba(139,92,246,.45);transition:.2s}
.onb-btn:active{transform:scale(.97)}

/* ===== TOAST ===== */
.toast-wrap{position:fixed;left:0;right:0;bottom:calc(24px + env(safe-area-inset-bottom));z-index:600;display:flex;flex-direction:column;align-items:center;gap:8px;pointer-events:none;padding:0 20px}
.toast{max-width:340px;width:100%;display:flex;align-items:center;gap:10px;padding:14px 16px;border-radius:var(--r);background:var(--card2);border:1px solid var(--border2);color:var(--t1);font-size:13px;font-weight:600;box-shadow:var(--shadow);animation:toastIn .35s cubic-bezier(.2,.9,.3,1)}
.toast.out{animation:toastOut .3s ease forwards}
.toast svg{width:18px;height:18px;flex-shrink:0}
.toast.ok svg{color:var(--green)}
.toast.err svg{color:var(--red)}
.toast.info svg{color:var(--cyan)}
@keyframes toastIn{from{transform:translateY(30px);opacity:0}to{transform:translateY(0);opacity:1}}
@keyframes toastOut{to{transform:translateY(30px);opacity:0}}

/* ===== CONFETTI ===== */
#confetti{position:fixed;inset:0;z-index:590;pointer-events:none;display:none}
#confetti.on{display:block}
</style>
</head>
<body>

<!-- ============ ONBOARDING ============ -->
<div id="onb" class="onb">
  <button class="onb-skip" onclick="onbSkip()">Пропустить</button>
  <div class="onb-track" id="onb-track">
    <div class="onb-slide">
      <div class="onb-ic a"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg></div>
      <div class="onb-t">Добро пожаловать в LUNA</div>
      <div class="onb-d">Премиальное эскорт-агентство. Элегантность, безупречный вкус и полная анонимность в каждой детали.</div>
    </div>
    <div class="onb-slide">
      <div class="onb-ic b"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg></div>
      <div class="onb-t">Полная конфиденциальность</div>
      <div class="onb-d">Ваши данные под надёжной защитой. Никаких следов и лишних вопросов — только безопасность и приватность.</div>
    </div>
    <div class="onb-slide">
      <div class="onb-ic c"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 2l2.4 6.9L21 9.2l-5.2 4.4L17.4 21 12 17l-5.4 4 1.6-7.4L3 9.2l6.6-.3z"/></svg></div>
      <div class="onb-t">Лучшие модели города</div>
      <div class="onb-d">Только проверенные анкеты в топовых городах. Найдите свою и забронируйте в пару касаний.</div>
    </div>
  </div>
  <div class="onb-foot">
    <div class="onb-dots">
      <div class="onb-dot on" data-d="0"></div>
      <div class="onb-dot" data-d="1"></div>
      <div class="onb-dot" data-d="2"></div>
    </div>
    <button class="onb-btn" id="onb-btn" onclick="onbNext()">Далее</button>
  </div>
</div>

<!-- ============ ГОРОДА ============ -->
<div id="s-cities" class="screen active">
  <div class="top">
    <div class="top-l">
      <div class="top-badge">
        <div class="top-badge-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg></div>
        <span class="top-badge-txt">LUNA</span>
      </div>
    </div>
    <button class="btn-i" onclick="tgClose()" aria-label="Закрыть">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>
  </div>
  <div class="hero">
    <div class="brand">LUNA</div>
    <div class="sub">ESCORT AGENCY</div>
    <div class="online">
      <span class="odot"></span>
      <span>Сейчас свободны: <b id="total-on">0</b></span>
    </div>
  </div>
  <div class="stitle">Выберите город</div>
  <div class="cities" id="cities-list"></div>
  <div class="foot">
    <span>Безопасно</span><span>•</span><span>18+</span><span>•</span><span>Анонимно</span>
  </div>
</div>

<!-- ============ КАТАЛОГ ============ -->
<div id="s-catalog" class="screen">
  <div class="ptr" id="ptr"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg></div>
  <div class="top">
    <div class="top-l">
      <div class="top-badge">
        <div class="top-badge-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg></div>
        <span class="top-badge-txt">LUNA</span>
      </div>
      <div class="top-city">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 12-9 12s-9-5-9-12a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        <span id="cur-city">Москва</span>
        <span class="dot"></span>
        <span class="top-city-cnt" id="m-count">0</span>
      </div>
    </div>
    <button class="btn-i" onclick="go('cities')" aria-label="Назад">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
    </button>
  </div>
  <div class="sbar">
    <div class="swrap">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" id="sinput" placeholder="Поиск по ID модели..." onkeyup="doSearch(event)">
    </div>
    <button class="btn-f" onclick="showM('filters')" aria-label="Фильтры">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/><circle cx="8" cy="6" r="2" fill="currentColor"/><circle cx="16" cy="12" r="2" fill="currentColor"/><circle cx="10" cy="18" r="2" fill="currentColor"/></svg>
    </button>
    <button class="btn-f" onclick="toggleFav()" id="fav-btn" aria-label="Избранное">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
    </button>
  </div>
  <div class="grid" id="grid"></div>
  <div class="bbar">
    <button class="bbtn active" onclick="goTab('catalog')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
      <small>Каталог</small>
    </button>
    <button class="bbtn" onclick="goTab('profile')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      <small>Профиль</small>
    </button>
  </div>
</div>

<!-- ============ МОДЕЛЬ ============ -->
<div id="s-model" class="screen"><div id="model-c"></div></div>

<!-- ============ ПРОФИЛЬ ============ -->
<div id="s-profile" class="screen">
  <div class="top">
    <div class="top-l">
      <div class="top-badge">
        <div class="top-badge-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg></div>
        <span class="top-badge-txt">LUNA</span>
      </div>
      <div class="top-city">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 12-9 12s-9-5-9-12a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        <span id="prof-city">Москва</span>
      </div>
    </div>
    <button class="btn-i" onclick="tgClose()" aria-label="Закрыть">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>
  </div>
  <div class="prof-hero">
    <div class="prof-av-wrap">
      <div class="prof-av">
        <div class="prof-av-inner" id="prof-avatar">U</div>
      </div>
    </div>
    <div class="prof-name" id="prof-name">Пользователь</div>
    <div class="prof-meta">ID: <b id="prof-id">—</b> &nbsp;•&nbsp; <b id="prof-username">@user</b></div>
  </div>
  <div class="prof-balance">
    <div class="pb-lbl">Баланс</div>
    <div class="pb-v"><span id="prof-balance">0</span> ₽</div>
    <button class="pb-btn" onclick="askManager()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> Пополнить
    </button>
  </div>
  <div class="stitle" style="margin-top:26px">Настройки</div>
  <div class="set-list">
    <div class="set-item">
      <div class="set-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="7" y="2" width="10" height="20" rx="2"/><line x1="11" y1="18" x2="13" y2="18"/></svg></div>
      <div class="set-name">Вибрация</div>
      <div class="toggle on" id="tog-vib" onclick="tog(this,'vib')"></div>
    </div>
    <div class="set-item">
      <div class="set-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/></svg></div>
      <div class="set-name">Звуки</div>
      <div class="toggle on" id="tog-snd" onclick="tog(this,'snd')"></div>
    </div>
    <div class="set-item">
      <div class="set-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.2" y1="4.2" x2="5.6" y2="5.6"/><line x1="18.4" y1="18.4" x2="19.8" y2="19.8"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.2" y1="19.8" x2="5.6" y2="18.4"/><line x1="18.4" y1="5.6" x2="19.8" y2="4.2"/></svg></div>
      <div class="set-name">Светлая тема</div>
      <div class="toggle" id="tog-theme" onclick="toggleTheme(this)"></div>
    </div>
    <div class="set-item">
      <div class="set-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z"/></svg></div>
      <div class="set-name">Избранное</div>
      <div class="set-cnt" id="prof-fav-cnt">0</div>
    </div>
  </div>
  <div class="stitle" style="margin-top:26px">История операций</div>
  <div class="hist-empty">
    <div class="hist-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg></div>
    <div class="hist-txt">История пуста</div>
  </div>
  <button class="support-btn" onclick="askManager()">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
    Написать в поддержку
  </button>
  <div class="bbar">
    <button class="bbtn" onclick="goTab('catalog')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
      <small>Каталог</small>
    </button>
    <button class="bbtn active" onclick="goTab('profile')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      <small>Профиль</small>
    </button>
  </div>
</div>

<!-- ============ ФИЛЬТРЫ ============ -->
<div id="m-filters" class="modal">
  <div class="modal-ov" onclick="hideM('filters')"></div>
  <div class="bsheet">
    <div class="modal-h">
      <h3>Фильтры</h3>
      <button class="btn-i" onclick="hideM('filters')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
    </div>
    <div class="fg">
      <label>Цена за час (₽)</label>
      <div class="frow">
        <input class="finp" type="number" id="fp-min" placeholder="От">
        <span style="color:var(--t3);font-weight:600">—</span>
        <input class="finp" type="number" id="fp-max" placeholder="До">
      </div>
    </div>
    <div class="fg">
      <label>Возраст</label>
      <div class="frow">
        <input class="finp" type="number" id="fa-min" placeholder="От 18" value="18">
        <span style="color:var(--t3);font-weight:600">—</span>
        <input class="finp" type="number" id="fa-max" placeholder="До">
      </div>
    </div>
    <div class="factions">
      <button class="btn-res" onclick="resetF()">Сброс</button>
      <button class="btn-app" onclick="applyF()">Показать</button>
    </div>
  </div>
</div>

<!-- ============ ОПЛАТА ============ -->
<div id="m-pay" class="modal">
  <div class="modal-ov" onclick="hideM('pay')"></div>
  <div class="bsheet">
    <div class="modal-h">
      <h3>Оплата</h3>
      <button class="btn-i" onclick="hideM('pay')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
    </div>
    <div class="pay-amt">
      <div class="pay-lbl">Сумма к оплате</div>
      <div class="pay-p" id="pay-p">0 ₽</div>
      <div class="pay-d" id="pay-d">Время бронирования: 1 час</div>
    </div>

    <div class="contact-title">Способ связи с менеджером</div>
    <div class="contact-opts">
      <button class="c-opt sel" onclick="selContact(this,'bot')">
        <div class="c-radio"></div>
        <div class="c-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/></svg></div>
        <div class="c-info"><div class="c-name">Через бота</div><div class="c-hint">Менеджер ответит в чат бота</div></div>
      </button>
      <button class="c-opt" onclick="selContact(this,'direct')">
        <div class="c-radio"></div>
        <div class="c-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div>
        <div class="c-info"><div class="c-name">Написать напрямую</div><div class="c-hint">Откроется чат с @__MGR__</div></div>
      </button>
      <button class="c-opt" onclick="selContact(this,'manager_writes')">
        <div class="c-radio"></div>
        <div class="c-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.9.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/></svg></div>
        <div class="c-info"><div class="c-name">Менеджер напишет мне</div><div class="c-hint">Если у вас спам-блок в Telegram</div></div>
      </button>
    </div>

    <div class="contact-title">Способ оплаты</div>
    <div class="pmethods">
      <button class="pm" onclick="pay('balance')">
        <span class="pm-i balance"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 12V8H6a2 2 0 0 1 0-4h12v4"/><path d="M4 6v12a2 2 0 0 0 2 2h14v-4"/><path d="M18 12a2 2 0 0 0 0 4h4v-4z"/></svg></span>
        <div class="pm-info"><span class="pm-n">Баланс</span><span class="pm-h">Мгновенно</span></div>
        <span class="pm-a"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg></span>
      </button>
      <button class="pm" onclick="pay('card')">
        <span class="pm-i card"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg></span>
        <div class="pm-info"><span class="pm-n">Банковская карта</span></div>
        <span class="pm-a"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg></span>
      </button>
      <button class="pm" onclick="openCrypto()">
        <span class="pm-i crypto"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 8h5a2.5 2.5 0 0 1 0 5H9zM9 13h5.5a2.5 2.5 0 0 1 0 5H9zM9 5v14"/><path d="M11 5V3M14 5V3M11 21v-2M14 21v-2"/></svg></span>
        <div class="pm-info"><span class="pm-n">Криптовалюта</span></div>
        <span class="pm-a"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg></span>
      </button>
      <button class="pm" onclick="pay('manager')">
        <span class="pm-i mgr"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></span>
        <div class="pm-info"><span class="pm-n">Менеджер</span><span class="pm-h">Ручной приём оплаты</span></div>
        <span class="pm-a"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg></span>
      </button>
    </div>
  </div>
</div>

<!-- ============ КРИПТА ============ -->
<div id="m-crypto" class="modal">
  <div class="modal-ov" onclick="hideM('crypto')"></div>
  <div class="bsheet">
    <div class="modal-h">
      <div style="display:flex;align-items:center;gap:10px">
        <button class="btn-i" onclick="hideM('crypto');showM('pay')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg></button>
        <h3>Криптовалюта</h3>
      </div>
      <button class="btn-i" onclick="hideM('crypto')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
    </div>
    <div class="crypto-grid">
      <div class="crypto-c" onclick="selCrypto('usdt')"><div class="crypto-ic usdt">$</div><div class="crypto-n">USDT</div></div>
      <div class="crypto-c" onclick="selCrypto('btc')"><div class="crypto-ic btc">₿</div><div class="crypto-n">BTC</div></div>
      <div class="crypto-c" onclick="selCrypto('ton')"><div class="crypto-ic ton"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/></svg></div><div class="crypto-n">TON</div></div>
      <div class="crypto-c" onclick="selCrypto('eth')"><div class="crypto-ic eth">Ξ</div><div class="crypto-n">ETH</div></div>
    </div>
    <div class="crypto-addr" id="crypto-addr">
      <div class="addr-lbl" id="addr-lbl">Адрес кошелька</div>
      <div class="addr-box" id="addr-box"></div>
      <button class="addr-copy" onclick="copyAddr()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Копировать адрес</button>
      <button class="addr-done" id="addr-done">Я оплатил</button>
    </div>
  </div>
</div>

<!-- ============ TOAST + CONFETTI ============ -->
<div class="toast-wrap" id="toast-wrap"></div>
<canvas id="confetti"></canvas>

<script>
const API='';
const MGR='__MGR__';
const CRYPTO_ADDR={usdt:'__USDT__',ton:'__TON__'};
const CRYPTO_LABEL={usdt:'USDT (TRC-20)',btc:'BTC',ton:'TON',eth:'ETH'};
const FB='https://via.placeholder.com/400x600/1A1D30/E5B547?text=LUNA';
let city='',models=[],allModels=[],selPrice=null,selModel=null,contactMethod='bot',curCrypto=null;
let favs=JSON.parse(localStorage.getItem('luna_fav')||'[]');
let showingFavs=false;

/* ---------- INIT ---------- */
document.addEventListener('DOMContentLoaded',()=>{
  if(localStorage.getItem('luna_theme')==='light')document.documentElement.classList.add('light');
  applyThemeColors();
  if(window.Telegram&&Telegram.WebApp){
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
    initProfile();
  }
  // restore toggles
  if(localStorage.getItem('luna_vib')==='0')document.getElementById('tog-vib').classList.remove('on');
  if(localStorage.getItem('luna_snd')==='0')document.getElementById('tog-snd').classList.remove('on');
  if(localStorage.getItem('luna_theme')==='light')document.getElementById('tog-theme').classList.add('on');
  loadCities();
  if(!localStorage.getItem('luna_onboarded'))document.getElementById('onb').classList.add('active');
  initPTR();
  window.addEventListener('scroll',parallax,{passive:true});
});

/* ---------- ONBOARDING ---------- */
let onbIdx=0;
function onbGo(i){
  onbIdx=i;
  document.getElementById('onb-track').style.transform='translateX(-'+(i*100)+'%)';
  document.querySelectorAll('.onb-dot').forEach((d,k)=>d.classList.toggle('on',k===i));
  document.getElementById('onb-btn').textContent=i===2?'Начать':'Далее';
  sfx('tick');haptic('light');
}
function onbNext(){ if(onbIdx<2)onbGo(onbIdx+1); else onbSkip(); }
function onbSkip(){
  localStorage.setItem('luna_onboarded','1');
  const o=document.getElementById('onb');
  o.style.transition='opacity .35s ease';o.style.opacity='0';
  setTimeout(()=>{o.classList.remove('active');o.style.opacity='';o.style.transition='';},350);
  haptic('medium');
}
document.getElementById('onb-track').style.transition='transform .4s cubic-bezier(.2,.9,.3,1)';

/* ---------- TELEGRAM / PROFILE ---------- */
function initProfile(){
  const u=Telegram.WebApp.initDataUnsafe&&Telegram.WebApp.initDataUnsafe.user;
  if(u){
    document.getElementById('prof-name').textContent=u.first_name||'Пользователь';
    document.getElementById('prof-id').textContent=u.id||'—';
    document.getElementById('prof-username').textContent=u.username?('@'+u.username):'—';
    document.getElementById('prof-avatar').textContent=(u.first_name||'U').charAt(0).toUpperCase();
  }
  document.getElementById('prof-fav-cnt').textContent=favs.length;
}
function tgClose(){if(window.Telegram)Telegram.WebApp.close()}
function haptic(t){
  if(localStorage.getItem('luna_vib')==='0')return;
  try{
    if(window.Telegram&&Telegram.WebApp.HapticFeedback){
      if(t==='success'||t==='error'||t==='warning')Telegram.WebApp.HapticFeedback.notificationOccurred(t);
      else Telegram.WebApp.HapticFeedback.impactOccurred(t||'light');
    }
  }catch(e){}
}
function applyThemeColors(){
  const light=document.documentElement.classList.contains('light');
  const c=light?'#F5F5FB':'#0B0D1A';
  try{if(window.Telegram&&Telegram.WebApp){Telegram.WebApp.setHeaderColor(c);Telegram.WebApp.setBackgroundColor(c);}}catch(e){}
}

/* ---------- SOUND ENGINE (Web Audio API) ---------- */
let AC=null;
function sfx(type){
  if(localStorage.getItem('luna_snd')==='0')return;
  try{
    AC=AC||new (window.AudioContext||window.webkitAudioContext)();
    if(AC.state==='suspended')AC.resume();
    const t=AC.currentTime;
    if(type==='success'){
      [523,659,784,1047].forEach((f,i)=>beep(f,t+i*0.09,0.14,'sine',0.14));
    }else if(type==='whoosh'){
      const o=AC.createOscillator(),g=AC.createGain();
      o.type='sine';o.frequency.setValueAtTime(180,t);o.frequency.exponentialRampToValueAtTime(520,t+0.18);
      g.gain.setValueAtTime(0.0001,t);g.gain.exponentialRampToValueAtTime(0.12,t+0.05);g.gain.exponentialRampToValueAtTime(0.0001,t+0.22);
      o.connect(g);g.connect(AC.destination);o.start(t);o.stop(t+0.24);
    }else if(type==='error'){
      beep(160,t,0.22,'square',0.12);
    }else{
      beep(820,t,0.045,'sine',0.09);
    }
  }catch(e){}
}
function beep(freq,at,dur,wave,vol){
  const o=AC.createOscillator(),g=AC.createGain();
  o.type=wave||'sine';o.frequency.value=freq;
  g.gain.setValueAtTime(0.0001,at);g.gain.exponentialRampToValueAtTime(vol||0.1,at+0.01);
  g.gain.exponentialRampToValueAtTime(0.0001,at+dur);
  o.connect(g);g.connect(AC.destination);o.start(at);o.stop(at+dur+0.02);
}

/* ---------- NAV ---------- */
function go(n){
  document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));
  document.getElementById('s-'+n).classList.add('active');
  window.scrollTo(0,0);
  sfx('tick');haptic('light');
}
function goTab(n){
  go(n);
  if(n==='profile'){document.getElementById('prof-city').textContent=city||'Все города';document.getElementById('prof-fav-cnt').textContent=favs.length}
}
function showM(n){document.getElementById('m-'+n).classList.add('active');sfx('whoosh');haptic('medium')}
function hideM(n){document.getElementById('m-'+n).classList.remove('active')}
function fmt(p){return p?p.toLocaleString('ru-RU')+' ₽':'—'}
function fmtD(d){if(!d)return'';let x=new Date(d);return x.toLocaleDateString('ru-RU',{day:'2-digit',month:'2-digit',year:'numeric'})}

function tog(el,key){el.classList.toggle('on');localStorage.setItem('luna_'+key,el.classList.contains('on')?'1':'0');sfx('tick');haptic('light');toast(el.classList.contains('on')?'Включено':'Выключено','info')}
function toggleTheme(el){
  const on=!el.classList.contains('on');
  el.classList.toggle('on',on);
  document.documentElement.classList.toggle('light',on);
  localStorage.setItem('luna_theme',on?'light':'dark');
  applyThemeColors();sfx('tick');haptic('light');
  toast(on?'Светлая тема':'Тёмная тема','info');
}

/* ---------- CITIES ---------- */
async function loadCities(){
  let c;
  try{let r=await fetch(API+'/api/cities');c=await r.json()}catch(e){c=[]}
  let t=0;
  document.getElementById('cities-list').innerHTML=c.map(x=>{
    t+=x.models_count||0;
    return `<div class="city-c" data-city="${x.name}" onclick="selCity(this.dataset.city)">
      <div class="city-l2">
        <div class="city-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 12-9 12s-9-5-9-12a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg></div>
        <div><div class="city-n">${x.name}</div><div class="city-cnt"><b>${x.models_count||0}</b> моделей онлайн</div></div>
      </div>
      <span class="city-arr"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg></span>
    </div>`;
  }).join('');
  document.getElementById('total-on').textContent=t;
}
async function selCity(n){
  city=n;
  document.getElementById('cur-city').textContent=n;
  document.getElementById('prof-city').textContent=n;
  go('catalog');
  await loadModels();
}

/* ---------- MODELS ---------- */
function skeleton(){
  document.getElementById('grid').innerHTML=Array(6).fill('<div class="sk"></div>').join('');
}
async function loadModels(f){
  f=f||{};
  showingFavs=false;
  document.getElementById('fav-btn').classList.remove('on');
  skeleton();
  try{
    let u=API+'/api/models/'+encodeURIComponent(city);
    let p=new URLSearchParams();
    if(f.price_min)p.set('price_min',f.price_min);
    if(f.price_max)p.set('price_max',f.price_max);
    if(f.age_min)p.set('age_min',f.age_min);
    if(f.age_max)p.set('age_max',f.age_max);
    if(p.toString())u+='?'+p;
    let r=await fetch(u);
    allModels=await r.json();
    models=allModels;
  }catch(e){models=[];allModels=[];toast('Не удалось загрузить','err')}
  renderGrid();
}
function renderGrid(){
  let g=document.getElementById('grid');
  document.getElementById('m-count').textContent=models.length;
  if(!models.length){
    g.innerHTML=`<div class="empty">
      <svg class="empty-ill" viewBox="0 0 120 120" fill="none">
        <circle cx="60" cy="60" r="46" fill="rgba(139,92,246,.10)"/>
        <path d="M78 46a20 20 0 1 1-21.6-19.4A15.5 15.5 0 0 0 78 46z" fill="url(#mg)"/>
        <circle cx="34" cy="34" r="2.6" fill="#E5B547"/><circle cx="90" cy="42" r="2" fill="#22D3EE"/><circle cx="86" cy="82" r="2.4" fill="#EC4899"/><circle cx="30" cy="80" r="1.8" fill="#8B5CF6"/>
        <defs><linearGradient id="mg" x1="40" y1="26" x2="78" y2="66"><stop stop-color="#8B5CF6"/><stop offset="1" stop-color="#E5B547"/></linearGradient></defs>
      </svg>
      <div class="empty-t">Моделей не найдено</div>
      <div class="empty-s">${showingFavs?'В избранном пока пусто':'Попробуйте изменить фильтры или город'}</div>
    </div>`;
    return;
  }
  g.innerHTML=models.map((m,i)=>{
    let liked=favs.indexOf(m.id)>-1;
    let tags='';
    if(m.is_verified)tags+='<span class="tag tag-v"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg>VERIF</span>';
    (m.tags||[]).forEach(t=>{
      if(t==='Новинка')tags+='<span class="tag tag-n">NEW</span>';
      if(t==='Горящая')tags+='<span class="tag tag-h">HOT</span>';
    });
    let vb=m.is_verified?'<span class="vb"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg></span>':'';
    let heart=liked?'<svg viewBox="0 0 24 24" fill="#EC4899" stroke="#EC4899" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z"/></svg>':'<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z"/></svg>';
    return `<div class="card" style="animation-delay:${i*40}ms" onclick="openM(${m.id})">
      <img src="${m.main_photo}" loading="lazy" alt="${m.name}" onerror="this.src='${FB}'">
      <div class="card-tags">${tags}</div>
      <button class="card-like ${liked?'liked':''}" onclick="event.stopPropagation();togLike(${m.id},this)">${heart}</button>
      <div class="card-info"><div class="card-name">${m.name} ${vb}</div><div class="card-meta"><span class="card-price">${fmt(m.price_1h)}/ч</span><span>•</span><span>${m.age} лет</span></div></div>
      <div class="card-id">#${m.id}</div>
    </div>`;
  }).join('');
}

async function openM(id){
  let m;
  try{let r=await fetch(API+'/api/model/'+id);m=await r.json()}catch(e){m=null}
  if(!m||m.error){toast('Модель недоступна','err');return}
  selModel=m;
  selPrice={dur:'1 час',price:m.price_1h};
  let liked=favs.indexOf(m.id)>-1;
  let vb=m.is_verified?'<span class="vb"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg></span>':'';
  let galArr=(m.gallery&&m.gallery.length)?m.gallery:[m.main_photo,m.main_photo,m.main_photo,m.main_photo];
  let gal=galArr.map(p=>`<div class="gitem"><img src="${p}" alt="18+" onerror="this.src='${FB}'"><div class="glock"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg><div class="glock-t">18+</div></div></div>`).join('');
  let revs=(m.reviews||[]).map(r=>`<div class="rev"><div class="rev-h"><div class="rev-u"><div class="rev-av">${(r.client_name||'A').charAt(0)}</div><span class="rev-n">${r.client_name}</span></div><span class="rev-d">${fmtD(r.created_at)}</span></div><div class="rev-s">${'★'.repeat(r.rating)}</div><div class="rev-t">${r.text}</div></div>`).join('');
  let heartBtn=liked?'liked':'';
  let heartSvg='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z"/></svg>';
  let p2=m.price_2h?`<div class="pitem" onclick="selP(this,'2 часа',${m.price_2h})"><div class="pitem-l"><div class="pitem-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg></div><span class="pitem-n">2 часа</span></div><div class="pitem-r"><span class="pitem-c">${fmt(m.price_2h)}</span><div class="pradio"></div></div></div>`:'';
  let pn=m.price_night?`<div class="pitem" onclick="selP(this,'Ночь',${m.price_night})"><div class="pitem-l"><div class="pitem-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg></div><span class="pitem-n">Ночь</span></div><div class="pitem-r"><span class="pitem-c">${fmt(m.price_night)}</span><div class="pradio"></div></div></div>`:'';

  document.getElementById('model-c').innerHTML=`<div class="det">
    <div class="slider">
      <img id="det-img" src="${m.main_photo}" alt="${m.name}" onerror="this.src='${FB}'">
      <div class="slider-nav">
        <button class="slider-btn" onclick="go('catalog')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg></button>
        <button class="slider-btn ${heartBtn}" onclick="togLike(${m.id},this)">${heartSvg}</button>
      </div>
      <div class="slider-ov">
        <div class="det-name">${m.name} ${vb}<span class="det-id">#${m.id}</span></div>
        <div class="det-stats">
          <span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>${m.views||0}</span>
          <span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z"/></svg>${m.likes||0}</span>
          <span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 12-9 12s-9-5-9-12a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>${m.city}</span>
        </div>
      </div>
    </div>
    <div class="infos">
      <div class="info"><div class="info-l">Возраст</div><div class="info-v">${m.age}</div></div>
      <div class="info"><div class="info-l">Рост</div><div class="info-v">${m.height||'—'}</div></div>
      <div class="info"><div class="info-l">Бюст</div><div class="info-v">${m.bust||'—'}</div></div>
      <div class="info"><div class="info-l">Цена</div><div class="info-v price">${fmt(m.price_1h)}</div></div>
    </div>
    <div class="sec"><div class="sec-t">О модели</div><div class="desc">${m.description||'Описание не указано.'}</div></div>
    <div class="sec" style="padding-bottom:0"><div class="sec-t">Галерея 18+</div></div>
    <div class="gscroll">${gal}</div>
    <div class="sec"><div class="sec-t">Прайс-лист</div></div>
    <div class="plist">
      <div class="pitem sel" onclick="selP(this,'1 час',${m.price_1h})"><div class="pitem-l"><div class="pitem-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg></div><span class="pitem-n">1 час</span></div><div class="pitem-r"><span class="pitem-c">${fmt(m.price_1h)}</span><div class="pradio"></div></div></div>
      ${p2}${pn}
    </div>
    ${revs?`<div class="sec"><div class="sec-t">Отзывы</div></div><div style="padding:0 16px">${revs}</div>`:''}
    <div class="bookwrap">
      <button class="btn-book" onclick="openPayment()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z"/></svg> Забронировать</button>
    </div>
  </div>`;
  go('model');
  haptic('medium');
}

/* ---------- PARALLAX ---------- */
let pTick=false;
function parallax(){
  if(pTick)return;pTick=true;
  requestAnimationFrame(()=>{
    pTick=false;
    if(!document.getElementById('s-model').classList.contains('active'))return;
    const img=document.getElementById('det-img');
    if(!img)return;
    const y=window.scrollY;
    img.style.transform='translateY('+(y*0.35)+'px) scale('+(1+Math.min(y,300)/2500)+')';
    const ov=img.parentElement.querySelector('.slider-ov');
    if(ov)ov.style.opacity=Math.max(0,1-y/260);
  });
}

/* ---------- BOOKING FLOW ---------- */
function openPayment(){
  if(!selPrice||!selModel)return;
  document.getElementById('pay-p').textContent=fmt(selPrice.price);
  document.getElementById('pay-d').textContent='Время бронирования: '+selPrice.dur;
  showM('pay');
}
function selP(el,dur,price){
  document.querySelectorAll('.pitem').forEach(i=>i.classList.remove('sel'));
  el.classList.add('sel');
  selPrice={dur:dur,price:price};
  sfx('tick');haptic('light');
}
function selContact(el,method){
  contactMethod=method;
  document.querySelectorAll('.c-opt').forEach(o=>o.classList.remove('sel'));
  el.classList.add('sel');
  sfx('tick');haptic('light');
}
function openCrypto(){
  document.getElementById('crypto-addr').classList.remove('show');
  curCrypto=null;
  hideM('pay');showM('crypto');
}
function selCrypto(coin){
  curCrypto=coin;
  sfx('tick');haptic('light');
  const box=document.getElementById('crypto-addr');
  if(coin==='usdt'||coin==='ton'){
    document.getElementById('addr-lbl').textContent='Адрес '+CRYPTO_LABEL[coin];
    document.getElementById('addr-box').textContent=CRYPTO_ADDR[coin];
    document.getElementById('addr-done').onclick=()=>pay('crypto_'+coin);
    box.classList.add('show');
    box.scrollIntoView({behavior:'smooth',block:'nearest'});
  }else{
    box.classList.remove('show');
    pay('crypto_'+coin);
  }
}
function copyAddr(){
  if(!curCrypto)return;
  const txt=CRYPTO_ADDR[curCrypto];
  const done=()=>{toast('Адрес скопирован','ok');sfx('tick');haptic('success')};
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(txt).then(done).catch(()=>fallbackCopy(txt,done));
  }else fallbackCopy(txt,done);
}
function fallbackCopy(txt,done){
  const ta=document.createElement('textarea');ta.value=txt;ta.style.position='fixed';ta.style.opacity='0';
  document.body.appendChild(ta);ta.select();
  try{document.execCommand('copy');done()}catch(e){toast('Скопируйте вручную','err')}
  document.body.removeChild(ta);
}

function togLike(id,btn){
  let i=favs.indexOf(id);
  const fill='<svg viewBox="0 0 24 24" fill="#EC4899" stroke="#EC4899" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z"/></svg>';
  const line='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z"/></svg>';
  if(i>-1){
    favs.splice(i,1);
    if(btn){btn.classList.remove('liked');if(btn.classList.contains('card-like'))btn.innerHTML=line}
  }else{
    favs.push(id);
    if(btn){btn.classList.add('liked');if(btn.classList.contains('card-like'))btn.innerHTML=fill;btn.style.animation='bounceIn .45s';setTimeout(()=>{if(btn)btn.style.animation=''},450)}
    fetch(API+'/api/like/'+id,{method:'POST'}).catch(()=>{});
    burstConfetti(0.5,0.35,26);
  }
  localStorage.setItem('luna_fav',JSON.stringify(favs));
  document.getElementById('prof-fav-cnt').textContent=favs.length;
  sfx('tick');haptic('light');
}

function toggleFav(){
  const btn=document.getElementById('fav-btn');
  if(showingFavs){
    models=allModels;showingFavs=false;btn.classList.remove('on');
  }else{
    if(!favs.length){toast('В избранном пока пусто','info');return}
    models=allModels.filter(m=>favs.indexOf(m.id)>-1);showingFavs=true;btn.classList.add('on');
  }
  sfx('tick');haptic('light');renderGrid();
}

function doSearch(e){
  if(e.key==='Enter'&&!(e.isComposing||e.keyCode===229)){
    let q=document.getElementById('sinput').value.trim().replace('#','');
    if(q&&!isNaN(q)){
      let m=allModels.find(x=>x.id===parseInt(q));
      if(m)openM(m.id);
      else toast('Модель с ID #'+q+' не найдена','err');
    }
  }
}
function resetF(){
  document.getElementById('fp-min').value='';
  document.getElementById('fp-max').value='';
  document.getElementById('fa-min').value='18';
  document.getElementById('fa-max').value='';
  loadModels();hideM('filters');
}
function applyF(){
  let f={
    price_min:document.getElementById('fp-min').value||null,
    price_max:document.getElementById('fp-max').value||null,
    age_min:document.getElementById('fa-min').value||null,
    age_max:document.getElementById('fa-max').value||null
  };
  loadModels(f);hideM('filters');
}

function pay(method){
  if(!selModel||!selPrice)return;
  hideM('pay');hideM('crypto');
  let data={
    action:'booking',
    model_id:selModel.id,
    model_name:selModel.name,
    duration:selPrice.dur,
    price:selPrice.price,
    payment_method:method,
    contact_method:contactMethod
  };
  // celebrate first, then hand off to the bot
  sfx('success');haptic('success');burstConfetti();
  toast('Бронирование создано! Менеджер свяжется с вами','ok');
  setTimeout(()=>{
    if(window.Telegram&&Telegram.WebApp.sendData){
      Telegram.WebApp.sendData(JSON.stringify(data));
    }else{
      fetch(API+'/api/booking',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
        .then(r=>r.json()).then(d=>toast('Заявка #'+d.booking_id+' принята','ok')).catch(()=>toast('Заявка отправлена','ok'));
    }
  },950);
}

function askManager(){
  sfx('tick');haptic('medium');
  if(window.Telegram){
    if(Telegram.WebApp.openTelegramLink)Telegram.WebApp.openTelegramLink('https://t.me/'+MGR);
    else if(Telegram.WebApp.showAlert)Telegram.WebApp.showAlert('Свяжитесь с @'+MGR);
    else toast('Напишите @'+MGR,'info');
  }else toast('Напишите @'+MGR,'info');
}

/* ---------- TOAST ---------- */
function toast(msg,type){
  const wrap=document.getElementById('toast-wrap');
  const el=document.createElement('div');
  el.className='toast '+(type||'info');
  let ic='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
  if(type==='ok')ic='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M20 6L9 17l-5-5"/></svg>';
  if(type==='err')ic='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
  el.innerHTML=ic+'<span>'+msg+'</span>';
  wrap.appendChild(el);
  setTimeout(()=>{el.classList.add('out');setTimeout(()=>el.remove(),300)},2600);
}

/* ---------- CONFETTI ---------- */
function burstConfetti(cx,cy,count){
  const cv=document.getElementById('confetti');
  const ctx=cv.getContext('2d');
  cv.width=innerWidth;cv.height=innerHeight;
  cv.classList.add('on');
  const cols=['#8B5CF6','#EC4899','#22D3EE','#E5B547','#10B981','#3B82F6'];
  const ox=(cx!=null?cx:0.5)*innerWidth, oy=(cy!=null?cy:0.42)*innerHeight;
  const N=count||120;
  let ps=[];
  for(let i=0;i<N;i++){
    const a=Math.random()*Math.PI*2, sp=4+Math.random()*8;
    ps.push({x:ox,y:oy,vx:Math.cos(a)*sp,vy:Math.sin(a)*sp-4,g:0.16+Math.random()*0.1,
      s:5+Math.random()*6,r:Math.random()*Math.PI,vr:(Math.random()-0.5)*0.3,
      c:cols[i%cols.length],life:0,max:70+Math.random()*40});
  }
  let raf;
  function frame(){
    ctx.clearRect(0,0,cv.width,cv.height);
    let alive=false;
    ps.forEach(p=>{
      if(p.life>p.max)return;
      alive=true;p.life++;
      p.vy+=p.g;p.x+=p.vx;p.y+=p.vy;p.r+=p.vr;
      ctx.save();ctx.translate(p.x,p.y);ctx.rotate(p.r);
      ctx.globalAlpha=Math.max(0,1-p.life/p.max);
      ctx.fillStyle=p.c;ctx.fillRect(-p.s/2,-p.s/2,p.s,p.s*0.6);
      ctx.restore();
    });
    if(alive)raf=requestAnimationFrame(frame);
    else{cancelAnimationFrame(raf);ctx.clearRect(0,0,cv.width,cv.height);cv.classList.remove('on')}
  }
  frame();
}

/* ---------- PULL TO REFRESH ---------- */
function initPTR(){
  const ptr=document.getElementById('ptr');
  let startY=0,pull=0,active=false;
  document.addEventListener('touchstart',e=>{
    if(!document.getElementById('s-catalog').classList.contains('active'))return;
    if(window.scrollY>0)return;
    startY=e.touches[0].clientY;active=true;pull=0;
  },{passive:true});
  document.addEventListener('touchmove',e=>{
    if(!active)return;
    pull=e.touches[0].clientY-startY;
    if(pull>0){
      const d=Math.min(pull*0.5,80);
      ptr.style.height=d+'px';
      ptr.style.opacity=Math.min(d/60,1);
      ptr.querySelector('svg').style.transform='rotate('+(d*4)+'deg)';
    }
  },{passive:true});
  document.addEventListener('touchend',()=>{
    if(!active)return;active=false;
    if(pull>70){
      ptr.style.height='46px';ptr.classList.add('spin');
      sfx('whoosh');haptic('medium');
      loadModels().then(()=>{
        setTimeout(()=>{ptr.classList.remove('spin');ptr.style.height='0';ptr.style.opacity='0';toast('Каталог обновлён','ok')},400);
      });
    }else{
      ptr.style.height='0';ptr.style.opacity='0';
    }
    pull=0;
  },{passive:true});
}
</script>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
