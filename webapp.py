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

DB_PATH = "luna.db"
MANAGER_USERNAME = os.getenv("MANAGER_USERNAME", "Luna_Support3")

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

DEMO_NAMES = ["Милана", "Алиса", "Виктория", "Диана", "Кристина", "Анжела",
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

    cities = ["Москва", "Санкт-Петербург", "Дубай", "Алматы"]
    descs = [
        "Обворожительная девушка, которая покорит вас с первого взгляда.",
        "Воплощение элегантности и женственности.",
        "Яркая и невероятно привлекательная.",
        "Чувственная и раскрепощённая.",
    ]

    for i in range(12):
        name = DEMO_NAMES[i % len(DEMO_NAMES)]
        age = random.randint(18, 27)
        city = random.choice(cities)
        price = random.choice([3000, 4000, 5000, 6000, 7000, 8000, 10000])
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
        ("Арсений", "Всё на высшем уровне. Рекомендую!"),
        ("Евгений", "Очень доволен, всё анонимно и быстро."),
        ("Инкогнито", "Девушка точно как на фото."),
        ("Максим", "Потрясающий сервис."),
        ("Дмитрий", "Идеальный вечер. Спасибо LUNA!"),
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
    return Response(WEBAPP_HTML, mimetype="text/html")


WEBAPP_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>LUNA ESCORT</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{--bg:#0A0A14;--bg2:#12121F;--card:#1A1A2E;--card2:#222240;--gold:#D4A847;--purple:#8B5CF6;--cyan:#06B6D4;--pink:#EC4899;--green:#10B981;--red:#EF4444;--t1:#FFF;--t2:#9CA3AF;--t3:#6B7280;--border:rgba(255,255,255,.06);--r:12px;--r2:16px;--rf:50px}
html,body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--t1);min-height:100vh;overflow-x:hidden}
.screen{display:none;min-height:100vh;padding-bottom:80px}
.screen.active{display:block}
@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.top{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;position:sticky;top:0;z-index:100;background:rgba(10,10,20,.92);backdrop-filter:blur(20px);border-bottom:1px solid var(--border)}
.logo-t{font-family:'Playfair Display',serif;font-size:20px;font-weight:700;background:linear-gradient(135deg,var(--purple),var(--gold));-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:3px}
.btn-i{background:none;border:none;color:var(--t2);font-size:20px;cursor:pointer;padding:8px;border-radius:8px}
.hero{text-align:center;padding:50px 20px 30px;position:relative}
.hero::before{content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);width:300px;height:300px;background:radial-gradient(circle,rgba(139,92,246,.12) 0%,transparent 70%)}
.brand{font-family:'Playfair Display',serif;font-size:48px;font-weight:700;letter-spacing:10px;background:linear-gradient(135deg,var(--purple),var(--gold));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sub{font-size:11px;letter-spacing:6px;color:var(--t3);margin-top:4px}
.online{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:20px;font-size:13px;color:var(--t2)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;box-shadow:0 0 8px var(--green)}
.stitle{font-size:12px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--t3);padding:0 20px;margin-bottom:10px}
.cities{padding:0 16px;display:flex;flex-direction:column;gap:8px}
.city{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;background:var(--card);border-radius:var(--r2);cursor:pointer;border:1px solid var(--border)}
.city:active{transform:scale(.98);background:var(--card2)}
.city-l{display:flex;align-items:center;gap:12px}
.city-n{font-size:15px;font-weight:500}
.city-c{font-size:11px;color:var(--t3);margin-top:2px}
.foot{display:flex;justify-content:center;gap:16px;padding:28px 20px;font-size:10px;color:var(--t3)}
.sbar{display:flex;align-items:center;gap:10px;padding:10px 16px}
.swrap{flex:1;display:flex;align-items:center;background:var(--card);border-radius:var(--rf);padding:10px 14px;border:1px solid var(--border)}
.swrap input{background:none;border:none;color:var(--t1);font-size:14px;width:100%;outline:none;font-family:inherit}
.btn-f{background:var(--card);border:1px solid var(--border);color:var(--t2);padding:10px;border-radius:var(--r);cursor:pointer;font-size:18px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;padding:0 12px}
.card{position:relative;border-radius:var(--r2);overflow:hidden;cursor:pointer;aspect-ratio:3/4;background:var(--card)}
.card:active{transform:scale(.97)}
.card img{width:100%;height:100%;object-fit:cover}
.card-id{position:absolute;top:8px;left:8px;background:rgba(0,0,0,.6);backdrop-filter:blur(10px);padding:3px 8px;border-radius:var(--rf);font-size:10px;color:var(--t2)}
.card-like{position:absolute;top:8px;right:8px;background:rgba(0,0,0,.4);border:none;color:#fff;font-size:16px;cursor:pointer;padding:5px;border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center}
.card-like.liked{color:var(--red)}
.card-tags{position:absolute;top:8px;left:8px;display:flex;flex-direction:column;gap:3px}
.tag{padding:2px 7px;border-radius:var(--rf);font-size:9px;font-weight:600;color:#fff}
.tag-v{background:rgba(6,182,212,.8)}
.tag-n{background:rgba(139,92,246,.8)}
.tag-h{background:rgba(239,68,68,.8)}
.card-info{position:absolute;bottom:0;left:0;right:0;padding:35px 10px 10px;background:linear-gradient(transparent,rgba(0,0,0,.85))}
.card-name{font-family:'Playfair Display',serif;font-size:15px;font-weight:600;display:flex;align-items:center;gap:4px}
.vb{color:var(--cyan);font-size:12px}
.card-meta{display:flex;align-items:center;gap:6px;margin-top:3px;font-size:11px;color:var(--t2)}
.card-price{color:var(--gold);font-weight:600}
.det{min-height:100vh;padding-bottom:100px}
.slider{position:relative;width:100%;aspect-ratio:3/4;overflow:hidden}
.slider img{width:100%;height:100%;object-fit:cover}
.slider-ov{position:absolute;bottom:0;left:0;right:0;padding:50px 20px 16px;background:linear-gradient(transparent,rgba(10,10,20,.95))}
.slider-nav{position:absolute;top:14px;left:0;right:0;display:flex;justify-content:space-between;padding:0 14px;z-index:10}
.det-name{font-family:'Playfair Display',serif;font-size:26px;font-weight:700;display:flex;align-items:center;gap:8px}
.det-id{font-size:13px;color:var(--t3);font-weight:400;font-family:'Inter',sans-serif}
.infos{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;padding:14px}
.info{background:var(--card);border-radius:var(--r);padding:12px 6px;text-align:center;border:1px solid var(--border)}
.info-l{font-size:9px;color:var(--t3);letter-spacing:1px;text-transform:uppercase;margin-bottom:4px}
.info-v{font-size:16px;font-weight:700}
.info-v.price{color:var(--gold);font-size:13px}
.sec{padding:18px 16px}
.sec-t{font-size:12px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--gold);margin-bottom:10px}
.desc{font-size:13px;line-height:1.7;color:var(--t2)}
.gscroll{display:flex;gap:8px;overflow-x:auto;padding:0 16px 8px}
.gitem{flex:0 0 110px;height:150px;border-radius:var(--r);overflow:hidden;position:relative}
.gitem img{width:100%;height:100%;object-fit:cover;filter:blur(15px)}
.glock{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.3);font-size:22px}
.plist{display:flex;flex-direction:column;gap:6px;padding:0 16px}
.pitem{display:flex;align-items:center;justify-content:space-between;padding:14px;background:var(--card);border-radius:var(--r);border:1px solid var(--border);cursor:pointer}
.pitem.sel{border-color:var(--purple);background:rgba(139,92,246,.1)}
.pitem-l{display:flex;align-items:center;gap:10px}
.pitem-icon{font-size:18px}
.pitem-name{font-size:14px;font-weight:500}
.pitem-cost{font-size:15px;font-weight:700;color:var(--gold)}
.pradio{width:20px;height:20px;border-radius:50%;border:2px solid var(--t3);display:flex;align-items:center;justify-content:center}
.pitem.sel .pradio{border-color:var(--purple);background:var(--purple)}
.pitem.sel .pradio::after{content:'v';color:#fff;font-size:11px;font-weight:700}
.bookwrap{padding:18px 16px;position:fixed;bottom:0;left:0;right:0;background:linear-gradient(transparent,var(--bg) 30%);z-index:50}
.btn-book{width:100%;padding:16px;border:none;border-radius:var(--rf);background:linear-gradient(135deg,var(--purple),var(--pink),var(--cyan));color:#fff;font-size:15px;font-weight:700;letter-spacing:1px;cursor:pointer;box-shadow:0 4px 18px rgba(139,92,246,.4)}
.rev{background:var(--card);border-radius:var(--r);padding:14px;margin-bottom:8px;border:1px solid var(--border)}
.rev-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.rev-u{display:flex;align-items:center;gap:8px}
.rev-av{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--purple),var(--gold));display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px}
.rev-n{font-weight:600;font-size:13px}
.rev-d{font-size:11px;color:var(--t3)}
.rev-s{color:var(--gold);font-size:13px;margin-bottom:6px}
.rev-t{font-size:12px;color:var(--t2);line-height:1.5;padding-left:10px;border-left:2px solid var(--purple)}
.modal{display:none;position:fixed;inset:0;z-index:200}
.modal.active{display:block}
.modal-ov{position:absolute;inset:0;background:rgba(0,0,0,.6);backdrop-filter:blur(4px)}
.bsheet{position:absolute;bottom:0;left:0;right:0;background:var(--bg2);border-radius:var(--r2) var(--r2) 0 0;padding:22px 18px 36px;animation:slideUp .3s;max-height:85vh;overflow-y:auto}
.modal-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.modal-h h3{font-family:'Playfair Display',serif;font-size:20px;font-weight:600}
.fg{margin-bottom:16px}
.fg label{font-size:10px;font-weight:600;letter-spacing:2px;color:var(--t3);margin-bottom:8px;display:block}
.frow{display:flex;align-items:center;gap:10px}
.finp{flex:1;background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:12px 14px;color:var(--t1);font-size:14px;font-family:inherit;outline:none}
.factions{display:flex;gap:10px;margin-top:20px}
.btn-res{flex:1;padding:14px;border:none;border-radius:var(--rf);background:var(--card);color:var(--t2);font-size:13px;font-weight:600;cursor:pointer;font-family:inherit}
.btn-app{flex:2;padding:14px;border:none;border-radius:var(--rf);background:linear-gradient(135deg,var(--purple),var(--gold));color:#fff;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit}
.pay-amt{background:var(--card);border-radius:var(--r2);padding:22px;text-align:center;margin-bottom:20px;border:1px solid var(--border)}
.pay-p{font-family:'Playfair Display',serif;font-size:30px;font-weight:700;color:var(--gold)}
.pay-d{font-size:12px;color:var(--cyan);margin-top:4px}
.pms{display:flex;flex-direction:column;gap:6px}
.pm{display:flex;align-items:center;gap:12px;padding:14px 16px;background:var(--card);border:1px solid var(--border);border-radius:var(--r);cursor:pointer;color:var(--t1);font-family:inherit;text-align:left;width:100%}
.pm-i{font-size:20px;width:36px;height:36px;background:rgba(139,92,246,.1);border-radius:8px;display:flex;align-items:center;justify-content:center}
.pm-info{flex:1;display:flex;flex-direction:column}
.pm-n{font-size:14px;font-weight:500}
.pm-h{font-size:10px;color:var(--green);font-weight:600}
.pm-a{color:var(--t3);font-size:20px}
.contact-title{font-size:12px;font-weight:600;letter-spacing:1px;color:var(--t3);margin:16px 0 8px;text-transform:uppercase}
.contact-opts{display:flex;flex-direction:column;gap:6px;margin-bottom:16px}
.c-opt{display:flex;align-items:center;gap:10px;padding:12px 14px;background:var(--card);border:1px solid var(--border);border-radius:var(--r);cursor:pointer;color:var(--t1);font-family:inherit;text-align:left;width:100%;font-size:13px}
.c-opt.sel{border-color:var(--purple);background:rgba(139,92,246,.1)}
.c-radio{width:18px;height:18px;border-radius:50%;border:2px solid var(--t3);display:flex;align-items:center;justify-content:center;flex-shrink:0}
.c-opt.sel .c-radio{border-color:var(--purple);background:var(--purple)}
.c-opt.sel .c-radio::after{content:'v';color:#fff;font-size:10px}
.c-info{flex:1}
.c-name{font-weight:500}
.c-hint{font-size:10px;color:var(--t3);margin-top:2px}
.bbar{position:fixed;bottom:0;left:0;right:0;display:flex;background:rgba(10,10,20,.95);backdrop-filter:blur(20px);border-top:1px solid var(--border);z-index:100;padding:8px 0}
.bbtn{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;padding:8px;background:none;border:none;color:var(--t3);cursor:pointer;font-family:inherit}
.bbtn.active{color:var(--gold)}
.bbtn span{font-size:18px}
.bbtn small{font-size:9px;font-weight:500}
.empty{text-align:center;padding:50px 20px;grid-column:1/-1}
.empty-i{font-size:40px;margin-bottom:12px}
.empty-t{font-size:14px;color:var(--t2)}
</style>
</head>
<body>
<div id="s-cities" class="screen active">
  <div class="top">
    <div style="display:flex;align-items:center;gap:8px"><span style="font-size:22px">M</span><span class="logo-t">LUNA</span></div>
    <button class="btn-i" onclick="tgClose()">X</button>
  </div>
  <div class="hero"><div class="brand">LUNA</div><div class="sub">ESCORT AGENCY</div>
    <div class="online"><span class="dot"></span><span id="total-on">SVOBODNY: <b>0</b></span></div>
  </div>
  <div class="stitle">Vyberite gorod</div>
  <div class="cities" id="cities-list"></div>
  <div class="foot"><span>SECURE</span><span>18+</span><span>Privacy</span></div>
</div>

<div id="s-catalog" class="screen">
  <div class="top">
    <button class="btn-i" onclick="go('cities')">&lt;</button>
    <div style="display:flex;align-items:center;gap:5px;font-size:14px;font-weight:500"><span id="cur-city">Moscow</span><span id="m-count" style="color:var(--t3);font-size:12px">(0)</span></div>
    <button class="btn-i" onclick="toggleFav()">love</button>
  </div>
  <div class="sbar">
    <div class="swrap"><span style="font-size:13px;margin-right:8px;opacity:.5">S</span><input type="text" id="sinput" placeholder="Poisk po ID..." onkeyup="doSearch(event)"></div>
    <button class="btn-f" onclick="showM('filters')">F</button>
  </div>
  <div class="grid" id="grid"></div>
  <div class="bbar">
    <button class="bbtn active" onclick="go('catalog')"><span>H</span><small>Katalog</small></button>
    <button class="bbtn" onclick="showProfile()"><span>U</span><small>Profil</small></button>
  </div>
</div>

<div id="s-model" class="screen"><div id="model-c"></div></div>

<div id="m-filters" class="modal">
  <div class="modal-ov" onclick="hideM('filters')"></div>
  <div class="bsheet">
    <div class="modal-h"><h3>Filtry</h3><button class="btn-i" onclick="hideM('filters')">X</button></div>
    <div class="fg"><label>CENA ZA CHAS</label><div class="frow"><input class="finp" type="number" id="fp-min" placeholder="Ot"><span style="color:var(--t3)">-</span><input class="finp" type="number" id="fp-max" placeholder="Do"></div></div>
    <div class="fg"><label>VOZRAST</label><div class="frow"><input class="finp" type="number" id="fa-min" placeholder="Ot 18" value="18"><span style="color:var(--t3)">-</span><input class="finp" type="number" id="fa-max" placeholder="Do"></div></div>
    <div class="factions"><button class="btn-res" onclick="resetF()">SBROS</button><button class="btn-app" id="btn-apply" onclick="applyF()">POKAZAT</button></div>
  </div>
</div>

<div id="m-pay" class="modal">
  <div class="modal-ov" onclick="hideM('pay')"></div>
  <div class="bsheet">
    <div class="modal-h"><h3>Oplata</h3><button class="btn-i" onclick="hideM('pay')">X</button></div>
    <div class="pay-amt"><div class="pay-p" id="pay-p">0</div><div class="pay-d" id="pay-d">Vremya: 1 chas</div></div>
    <div class="contact-title">Svyaz s menedzherom</div>
    <div class="contact-opts">
      <button class="c-opt sel" onclick="selContact(this,'bot')"><div class="c-radio"></div><div class="c-info"><div class="c-name">Cherez bota</div><div class="c-hint">Otvet v chat bota</div></div></button>
      <button class="c-opt" onclick="selContact(this,'direct')"><div class="c-radio"></div><div class="c-info"><div class="c-name">Napisat napryamuyu</div><div class="c-hint">@MGR_HERE</div></div></button>
      <button class="c-opt" onclick="selContact(this,'manager_writes')"><div class="c-radio"></div><div class="c-info"><div class="c-name">Menedzher napishet mne</div><div class="c-hint">Esli spam-blok</div></div></button>
    </div>
    <div class="contact-title">Sposob oplaty</div>
    <div class="pms">
      <button class="pm" onclick="pay('balance')"><span class="pm-i">B</span><div class="pm-info"><span class="pm-n">Balance</span><span class="pm-h">INSTANT</span></div><span class="pm-a">&gt;</span></button>
      <button class="pm" onclick="pay('card')"><span class="pm-i">C</span><div class="pm-info"><span class="pm-n">Card</span></div><span class="pm-a">&gt;</span></button>
      <button class="pm" onclick="pay('crypto')"><span class="pm-i">$</span><div class="pm-info"><span class="pm-n">Crypto</span></div><span class="pm-a">&gt;</span></button>
      <button class="pm" onclick="pay('manager')"><span class="pm-i">M</span><div class="pm-info"><span class="pm-n">Manager</span><span class="pm-h">Ruchnoi</span></div><span class="pm-a">&gt;</span></button>
    </div>
  </div>
</div>

<script>
const API='';
const MGR='MGR_PLACEHOLDER';
let city='',models=[],selPrice=null,selModel=null,contactMethod='bot';
let favs=JSON.parse(localStorage.getItem('luna_fav')||'[]');
document.addEventListener('DOMContentLoaded',()=>{
  if(window.Telegram&&Telegram.WebApp){Telegram.WebApp.ready();Telegram.WebApp.expand();try{Telegram.WebApp.setHeaderColor('#0A0A14');Telegram.WebApp.setBackgroundColor('#0A0A14')}catch(e){}}
  loadCities();
});
function tgClose(){if(window.Telegram)Telegram.WebApp.close()}
function haptic(t){try{if(window.Telegram)Telegram.WebApp.HapticFeedback.impactOccurred(t||'light')}catch(e){}}
function go(n){document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));document.getElementById('s-'+n).classList.add('active');haptic()}
function showM(n){document.getElementById('m-'+n).classList.add('active')}
function hideM(n){document.getElementById('m-'+n).classList.remove('active')}
function fmt(p){return p?p.toLocaleString('ru-RU')+' RUB':'-'}
function fmtD(d){if(!d)return'';let x=new Date(d);return x.toLocaleDateString('ru-RU')}
async function loadCities(){
  let c;try{let r=await fetch(API+'/api/cities');c=await r.json()}catch(e){c=[]}
  let t=0;
  document.getElementById('cities-list').innerHTML=c.map(x=>{t+=x.models_count||0;return'<div class="city" onclick="selCity(\\''+x.name+'\\')"><div class="city-l"><span style="font-size:16px">P</span><div><div class="city-n">'+x.name+'</div><div class="city-c">'+(x.models_count||0)+' modelej</div></div></div><span style="color:var(--t3);font-size:18px">&gt;</span></div>'}).join('');
  document.getElementById('total-on').innerHTML='SVOBODNY: <b>'+t+'</b>';
}
async function selCity(n){city=n;document.getElementById('cur-city').textContent=n;go('catalog');await loadModels()}
async function loadModels(f){f=f||{};
  try{let u=API+'/api/models/'+encodeURIComponent(city);let p=new URLSearchParams();
    if(f.price_min)p.set('price_min',f.price_min);if(f.price_max)p.set('price_max',f.price_max);
    if(f.age_min)p.set('age_min',f.age_min);if(f.age_max)p.set('age_max',f.age_max);
    if(p.toString())u+='?'+p;let r=await fetch(u);models=await r.json();
  }catch(e){models=[]}
  renderGrid();
}
function renderGrid(){
  let g=document.getElementById('grid');
  document.getElementById('m-count').textContent='('+models.length+')';
  if(!models.length){g.innerHTML='<div class="empty"><div class="empty-i">M</div><div class="empty-t">Modeli ne najdeny</div></div>';return}
  g.innerHTML=models.map(m=>{
    let liked=favs.indexOf(m.id)>-1;let tags='';
    if(m.is_verified)tags+='<span class="tag tag-v">VERIF</span>';
    (m.tags||[]).forEach(t=>{if(t==='Новинка')tags+='<span class="tag tag-n">NEW</span>';if(t==='Горящая')tags+='<span class="tag tag-h">HOT</span>'});
    let vb=m.is_verified?'<span class="vb">v</span>':'';
    return'<div class="card" onclick="openM('+m.id+')"><img src="'+m.main_photo+'" loading="lazy"><div class="card-tags">'+tags+'</div><button class="card-like '+(liked?'liked':'')+'" onclick="event.stopPropagation();togLike('+m.id+',this)">'+(liked?'love':'o')+'</button><div class="card-info"><div class="card-name">'+m.name+' '+vb+'</div><div class="card-meta"><span class="card-price">'+fmt(m.price_1h)+'/h</span><span>-</span><span>'+m.age+' let</span></div></div><div class="card-id">#'+m.id+'</div></div>'
  }).join('');
}
async function openM(id){
  let m;try{let r=await fetch(API+'/api/model/'+id);m=await r.json()}catch(e){m=null}
  if(!m||m.error)return;
  selModel=m;selPrice={dur:'1 час',price:m.price_1h};
  let liked=favs.indexOf(m.id)>-1;let vb=m.is_verified?'<span class="vb">v</span>':'';
  let gal=(m.gallery||[]).map(p=>'<div class="gitem"><img src="'+p+'" alt="18"><div class="glock">L</div></div>').join('');
  let revs=(m.reviews||[]).map(r=>'<div class="rev"><div class="rev-h"><div class="rev-u"><div class="rev-av">'+r.client_name[0]+'</div><span class="rev-n">'+r.client_name+'</span></div><span class="rev-d">'+fmtD(r.created_at)+'</span></div><div class="rev-s">'+'*'.repeat(r.rating)+'</div><div class="rev-t">'+r.text+'</div></div>').join('');
  document.getElementById('model-c').innerHTML='<div class="det"><div class="slider"><img src="'+m.main_photo+'"><div class="slider-nav"><button class="btn-i" onclick="go(\\'catalog\\')" style="background:rgba(0,0,0,.5)">&lt;</button><button class="btn-i" onclick="togLike('+m.id+',this)" style="background:rgba(0,0,0,.5)">'+(liked?'love':'o')+'</button></div><div class="slider-ov"><div class="det-name">'+m.name+' '+vb+' <span class="det-id">#'+m.id+'</span></div></div></div><div class="infos"><div class="info"><div class="info-l">Vozrast</div><div class="info-v">'+m.age+'</div></div><div class="info"><div class="info-l">Rost</div><div class="info-v">'+(m.height||'-')+'</div></div><div class="info"><div class="info-l">Byust</div><div class="info-v">'+(m.bust||'-')+'</div></div><div class="info"><div class="info-l">Cena</div><div class="info-v price">'+fmt(m.price_1h)+'</div></div></div><div class="sec"><div class="sec-t">O modeli</div><div class="desc">'+(m.description||'')+'</div></div>'+(gal?'<div class="sec" style="padding-bottom:0"><div class="sec-t">Galereya 18+</div></div><div class="gscroll">'+gal+'</div>':'')+'<div class="sec"><div class="sec-t">Prajs-list</div></div><div class="plist"><div class="pitem sel" onclick="selP(this,\\'1 час\\','+m.price_1h+')"><div class="pitem-l"><span class="pitem-icon">C</span><span class="pitem-name">1 chas</span></div><span class="pitem-cost">'+fmt(m.price_1h)+'</span><div class="pradio"></div></div>'+(m.price_2h?'<div class="pitem" onclick="selP(this,\\'2 часа\\','+m.price_2h+')"><div class="pitem-l"><span class="pitem-icon">C</span><span class="pitem-name">2 chasa</span></div><span class="pitem-cost">'+fmt(m.price_2h)+'</span><div class="pradio"></div></div>':'')+(m.price_night?'<div class="pitem" onclick="selP(this,\\'Ночь\\','+m.price_night+')"><div class="pitem-l"><span class="pitem-icon">M</span><span class="pitem-name">Noch</span></div><span class="pitem-cost">'+fmt(m.price_night)+'</span><div class="pradio"></div></div>':'')+'</div>'+(revs?'<div class="sec"><div class="sec-t">Otzyvy</div>'+revs+'</div>':'')+'<div class="bookwrap"><button class="btn-book" onclick="showM(\\'pay\\')">ZABRONIROVAT</button></div></div>';
  go('model');haptic('medium');
}
function selP(el,dur,price){document.querySelectorAll('.pitem').forEach(i=>i.classList.remove('sel'));el.classList.add('sel');selPrice={dur:dur,price:price};haptic('light')}
function togLike(id,btn){
  let i=favs.indexOf(id);
  if(i>-1){favs.splice(i,1);if(btn){btn.classList.remove('liked');btn.innerHTML='o'}}
  else{favs.push(id);if(btn){btn.classList.add('liked');btn.innerHTML='love'};fetch(API+'/api/like/'+id,{method:'POST'}).catch(()=>{})}
  localStorage.setItem('luna_fav',JSON.stringify(favs));haptic()
}
function toggleFav(){if(!favs.length)return;let fm=models.filter(m=>favs.indexOf(m.id)>-1);if(fm.length){let s=models;models=fm;renderGrid();models=s}}
function doSearch(e){if(e.key==='Enter'){let q=document.getElementById('sinput').value.trim().replace('#','');if(q&&!isNaN(q)){let m=models.find(x=>x.id===parseInt(q));if(m)openM(m.id)}}}
function resetF(){document.getElementById('fp-min').value='';document.getElementById('fp-max').value='';document.getElementById('fa-min').value='18';document.getElementById('fa-max').value='';loadModels();hideM('filters')}
function applyF(){let f={price_min:document.getElementById('fp-min').value||null,price_max:document.getElementById('fp-max').value||null,age_min:document.getElementById('fa-min').value||null,age_max:document.getElementById('fa-max').value||null};loadModels(f);hideM('filters')}
function selContact(el,method){contactMethod=method;document.querySelectorAll('.c-opt').forEach(o=>o.classList.remove('sel'));el.classList.add('sel');haptic()}
function pay(method){
  if(!selModel||!selPrice)return;
  hideM('pay');haptic('medium');
  let data={action:'booking',model_id:selModel.id,model_name:selModel.name,duration:selPrice.dur,price:selPrice.price,payment_method:method,contact_method:contactMethod};
  if(window.Telegram&&Telegram.WebApp.sendData){Telegram.WebApp.sendData(JSON.stringify(data));}
  else{fetch(API+'/api/booking',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).then(r=>r.json()).then(d=>{alert('Bronirovanie #'+d.booking_id+' sozdano!')}).catch(()=>alert('Zayavka otpravlena!'))}
}
function showProfile(){if(window.Telegram&&Telegram.WebApp.initDataUnsafe&&Telegram.WebApp.initDataUnsafe.user){let u=Telegram.WebApp.initDataUnsafe.user;Telegram.WebApp.showAlert('User: '+u.first_name+'\\nFav: '+favs.length)}}
</script>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
