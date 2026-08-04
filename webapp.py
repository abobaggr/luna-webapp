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
    html = WEBAPP_HTML.replace("__MGR__", MANAGER_USERNAME)
    return Response(html, mimetype="text/html")


WEBAPP_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>LUNA ESCORT</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
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
}
html,body{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--t1);min-height:100vh;overflow-x:hidden;-webkit-font-smoothing:antialiased}
body{background:radial-gradient(ellipse at top,#1a1837 0%,var(--bg) 45%) fixed}
.screen{display:none;min-height:100vh;padding-bottom:90px;animation:fadeIn .35s ease}
.screen.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.7;transform:scale(1.08)}}
@keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}

/* ===== TOP BAR ===== */
.top{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;position:sticky;top:0;z-index:100;background:rgba(11,13,26,.85);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border-bottom:1px solid var(--border)}
.top-l{display:flex;align-items:center;gap:10px}
.top-badge{display:flex;align-items:center;gap:8px;padding:6px 12px;background:var(--card);border:1px solid var(--border2);border-radius:var(--rf)}
.top-badge-icon{width:22px;height:22px;background:var(--grad2);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px}
.top-badge-txt{font-family:'Playfair Display',serif;font-weight:700;font-size:13px;letter-spacing:2px}
.top-city{display:flex;align-items:center;gap:6px;padding:6px 12px;background:var(--card);border:1px solid var(--border);border-radius:var(--rf);font-size:12px;font-weight:500;color:var(--t2)}
.top-city .dot{width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;box-shadow:0 0 8px var(--green)}
.top-city-cnt{color:var(--green);font-weight:700}
.btn-i{background:none;border:none;color:var(--t2);cursor:pointer;padding:8px;border-radius:10px;transition:.2s;display:flex;align-items:center;justify-content:center}
.btn-i:active{background:rgba(255,255,255,.06);transform:scale(.92)}
.btn-i svg{width:20px;height:20px}

/* ===== CITY SCREEN ===== */
.hero{text-align:center;padding:40px 20px 20px;position:relative}
.hero::before{content:'';position:absolute;top:-20px;left:50%;transform:translateX(-50%);width:400px;height:400px;background:radial-gradient(circle,rgba(139,92,246,.18) 0%,transparent 60%);pointer-events:none;z-index:-1}
.brand{font-family:'Playfair Display',serif;font-size:56px;font-weight:700;letter-spacing:12px;background:var(--grad2);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:4px}
.sub{font-size:11px;letter-spacing:6px;color:var(--t3);font-weight:400}
.online{display:inline-flex;align-items:center;gap:10px;margin-top:22px;padding:10px 18px;background:var(--card);border:1px solid var(--border2);border-radius:var(--rf);font-size:12px;color:var(--t2);font-weight:500}
.online b{color:var(--green);font-weight:700}
.stitle{font-size:11px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--t3);padding:0 22px;margin:26px 0 12px}
.cities{padding:0 16px;display:flex;flex-direction:column;gap:10px}
.city-c{display:flex;align-items:center;justify-content:space-between;padding:18px 20px;background:var(--card);border-radius:var(--r2);cursor:pointer;border:1px solid var(--border);transition:.25s;position:relative;overflow:hidden}
.city-c::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--grad);opacity:0;transition:.3s}
.city-c:active{transform:scale(.98);background:var(--card2);border-color:var(--border2)}
.city-c:active::before{opacity:1}
.city-l2{display:flex;align-items:center;gap:14px}
.city-icon{width:42px;height:42px;background:rgba(139,92,246,.12);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:18px}
.city-n{font-size:16px;font-weight:600}
.city-cnt{font-size:12px;color:var(--t3);margin-top:2px;font-weight:500}
.city-cnt b{color:var(--gold);font-weight:700}
.city-arr{color:var(--t3);font-size:22px;font-weight:300}
.foot{display:flex;justify-content:center;align-items:center;gap:20px;padding:30px 20px;font-size:10px;color:var(--t4);letter-spacing:1px}
.foot span{display:flex;align-items:center;gap:5px}

/* ===== SEARCH ===== */
.sbar{display:flex;align-items:center;gap:10px;padding:14px 16px}
.swrap{flex:1;display:flex;align-items:center;background:var(--card);border-radius:var(--rf);padding:12px 18px;border:1px solid var(--border);transition:.2s}
.swrap:focus-within{border-color:var(--purple);box-shadow:0 0 0 4px rgba(139,92,246,.1)}
.swrap svg{margin-right:10px;opacity:.5;flex-shrink:0}
.swrap input{background:none;border:none;color:var(--t1);font-size:14px;width:100%;outline:none;font-family:inherit}
.swrap input::placeholder{color:var(--t3)}
.btn-f{background:var(--card);border:1px solid var(--border);color:var(--t2);width:46px;height:46px;border-radius:var(--r);cursor:pointer;display:flex;align-items:center;justify-content:center;transition:.2s}
.btn-f:active{background:var(--card2);color:var(--purple);transform:scale(.95)}

/* ===== GRID ===== */
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;padding:0 12px}
.card{position:relative;border-radius:var(--r2);overflow:hidden;cursor:pointer;aspect-ratio:3/4;background:var(--card);box-shadow:var(--shadow);transition:.2s}
.card:active{transform:scale(.96)}
.card img{width:100%;height:100%;object-fit:cover}
.card-tags{position:absolute;top:10px;left:10px;display:flex;flex-direction:column;gap:5px;z-index:2}
.tag{padding:4px 9px;border-radius:var(--rf);font-size:9px;font-weight:800;color:#fff;letter-spacing:.5px;backdrop-filter:blur(10px);text-transform:uppercase;box-shadow:0 2px 8px rgba(0,0,0,.3)}
.tag-v{background:linear-gradient(135deg,#22D3EE,#3B82F6)}
.tag-n{background:linear-gradient(135deg,#8B5CF6,#EC4899)}
.tag-h{background:linear-gradient(135deg,#F97316,#EF4444)}
.card-like{position:absolute;top:10px;right:10px;background:rgba(0,0,0,.5);backdrop-filter:blur(10px);border:none;color:#fff;font-size:16px;cursor:pointer;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;transition:.2s;z-index:2}
.card-like:active{transform:scale(1.2)}
.card-like.liked{background:rgba(236,72,153,.35);color:#EC4899}
.card-info{position:absolute;bottom:0;left:0;right:0;padding:40px 12px 12px;background:linear-gradient(transparent,rgba(0,0,0,.9))}
.card-name{font-family:'Playfair Display',serif;font-size:16px;font-weight:600;display:flex;align-items:center;gap:5px;line-height:1.2}
.vb{color:var(--cyan);font-size:12px}
.card-meta{display:flex;align-items:center;gap:6px;margin-top:5px;font-size:11px;color:var(--t2)}
.card-price{color:var(--gold);font-weight:700;font-size:12px}
.card-id{position:absolute;bottom:10px;right:10px;background:rgba(0,0,0,.6);backdrop-filter:blur(10px);padding:3px 8px;border-radius:var(--rf);font-size:9px;color:var(--t2);font-weight:600;letter-spacing:.3px}

/* ===== MODEL DETAIL ===== */
.det{min-height:100vh;padding-bottom:110px}
.slider{position:relative;width:100%;aspect-ratio:3/4;overflow:hidden}
.slider img{width:100%;height:100%;object-fit:cover}
.slider-ov{position:absolute;bottom:0;left:0;right:0;padding:60px 20px 20px;background:linear-gradient(transparent,rgba(11,13,26,.98))}
.slider-nav{position:absolute;top:16px;left:0;right:0;display:flex;justify-content:space-between;padding:0 14px;z-index:10}
.slider-btn{background:rgba(0,0,0,.5);backdrop-filter:blur(10px);border:none;color:#fff;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:.2s}
.slider-btn:active{transform:scale(.9)}
.det-name{font-family:'Playfair Display',serif;font-size:30px;font-weight:700;display:flex;align-items:center;gap:8px;line-height:1}
.det-id{font-size:14px;color:var(--t3);font-weight:500;font-family:'Inter',sans-serif;margin-left:auto}
.det-stats{display:flex;gap:12px;margin-top:10px;font-size:12px;color:var(--t2)}
.det-stats span{display:flex;align-items:center;gap:4px}

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
.glock-i{font-size:24px}
.glock-t{font-size:9px;letter-spacing:2px;font-weight:700}

/* ===== PRICE LIST ===== */
.plist{display:flex;flex-direction:column;gap:8px;padding:0 16px}
.pitem{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;background:var(--card);border-radius:var(--r);border:1px solid var(--border);cursor:pointer;transition:.2s;position:relative;overflow:hidden}
.pitem::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--grad);opacity:0;transition:.3s}
.pitem.sel{border-color:var(--purple);background:linear-gradient(135deg,rgba(139,92,246,.1),rgba(236,72,153,.05));box-shadow:var(--glow)}
.pitem.sel::before{opacity:1}
.pitem:active{transform:scale(.98)}
.pitem-l{display:flex;align-items:center;gap:12px}
.pitem-ic{width:36px;height:36px;background:rgba(229,181,71,.1);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px}
.pitem-n{font-size:15px;font-weight:600}
.pitem-r{display:flex;align-items:center;gap:12px}
.pitem-c{font-size:16px;font-weight:800;color:var(--gold)}
.pradio{width:22px;height:22px;border-radius:50%;border:2px solid var(--t3);display:flex;align-items:center;justify-content:center;flex-shrink:0}
.pitem.sel .pradio{border-color:var(--purple);background:var(--purple);box-shadow:0 0 12px rgba(139,92,246,.5)}
.pitem.sel .pradio::after{content:'✓';color:#fff;font-size:12px;font-weight:800}

/* ===== BOOK BUTTON ===== */
.bookwrap{padding:20px 16px;position:fixed;bottom:0;left:0;right:0;background:linear-gradient(transparent,var(--bg) 35%);z-index:50}
.btn-book{width:100%;padding:18px;border:none;border-radius:var(--rf);background:var(--grad);color:#fff;font-size:15px;font-weight:800;letter-spacing:2px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;box-shadow:0 8px 32px rgba(139,92,246,.5);transition:.2s;text-transform:uppercase}
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
.rev-hd{display:flex;align-items:center;justify-content:space-between;padding:0 16px;margin-bottom:12px}
.rev-ver{display:flex;align-items:center;gap:5px;font-size:10px;color:var(--cyan);font-weight:600;letter-spacing:.5px}

/* ===== MODAL ===== */
.modal{display:none;position:fixed;inset:0;z-index:200}
.modal.active{display:block}
.modal-ov{position:absolute;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(6px)}
.bsheet{position:absolute;bottom:0;left:0;right:0;background:var(--bg2);border-radius:var(--r2) var(--r2) 0 0;padding:24px 20px 40px;animation:slideUp .35s cubic-bezier(.2,.9,.3,1);max-height:88vh;overflow-y:auto;box-shadow:0 -12px 40px rgba(0,0,0,.6)}
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
.pm-i{font-size:20px;width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.pm-i.balance{background:rgba(34,211,238,.12);color:var(--cyan)}
.pm-i.card{background:rgba(139,92,246,.12);color:var(--purple)}
.pm-i.crypto{background:rgba(249,115,22,.12);color:var(--orange)}
.pm-i.mgr{background:rgba(59,130,246,.12);color:var(--blue)}
.pm-info{flex:1;display:flex;flex-direction:column}
.pm-n{font-size:15px;font-weight:600}
.pm-h{font-size:10px;color:var(--green);font-weight:700;letter-spacing:1px;margin-top:2px}
.pm-a{color:var(--t3);font-size:22px;font-weight:300}

/* ===== CONTACT METHOD ===== */
.contact-title{font-size:10px;font-weight:700;letter-spacing:2px;color:var(--t3);margin:20px 0 10px;text-transform:uppercase;display:flex;align-items:center;gap:8px}
.contact-title::before{content:'';width:16px;height:2px;background:var(--purple);border-radius:2px}
.contact-opts{display:flex;flex-direction:column;gap:8px;margin-bottom:18px}
.c-opt{display:flex;align-items:center;gap:12px;padding:14px 16px;background:var(--card);border:1px solid var(--border);border-radius:var(--r);cursor:pointer;color:var(--t1);font-family:inherit;text-align:left;width:100%;font-size:13px;transition:.2s}
.c-opt.sel{border-color:var(--purple);background:linear-gradient(135deg,rgba(139,92,246,.1),transparent)}
.c-opt:active{transform:scale(.98)}
.c-radio{width:20px;height:20px;border-radius:50%;border:2px solid var(--t3);display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:.2s}
.c-opt.sel .c-radio{border-color:var(--purple);background:var(--purple);box-shadow:0 0 12px rgba(139,92,246,.5)}
.c-opt.sel .c-radio::after{content:'✓';color:#fff;font-size:11px;font-weight:800}
.c-ic{width:32px;height:32px;background:var(--card2);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.c-info{flex:1}
.c-name{font-weight:600;font-size:14px}
.c-hint{font-size:11px;color:var(--t3);margin-top:2px;font-weight:500}

/* ===== CRYPTO GRID ===== */
.crypto-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}
.crypto-c{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:22px 12px;display:flex;flex-direction:column;align-items:center;gap:10px;cursor:pointer;transition:.2s}
.crypto-c:active{border-color:var(--purple);background:var(--card2);transform:scale(.97)}
.crypto-ic{width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:900;color:#fff}
.crypto-ic.usdt{background:linear-gradient(135deg,#26A17B,#0F7A5A)}
.crypto-ic.btc{background:linear-gradient(135deg,#F7931A,#E27913)}
.crypto-ic.ton{background:linear-gradient(135deg,#3B82F6,#2563EB)}
.crypto-ic.eth{background:linear-gradient(135deg,#8B5CF6,#6D28D9)}
.crypto-n{font-size:13px;font-weight:800;letter-spacing:1px}

/* ===== BOTTOM BAR ===== */
.bbar{position:fixed;bottom:0;left:0;right:0;display:flex;background:rgba(11,13,26,.92);backdrop-filter:blur(24px);border-top:1px solid var(--border);z-index:100;padding:10px 0 max(10px,env(safe-area-inset-bottom))}
.bbtn{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px;background:none;border:none;color:var(--t3);cursor:pointer;font-family:inherit;transition:.2s;position:relative}
.bbtn.active{color:var(--cyan)}
.bbtn.active::after{content:'';position:absolute;bottom:0;width:4px;height:4px;border-radius:50%;background:var(--cyan);box-shadow:0 0 8px var(--cyan)}
.bbtn svg{width:22px;height:22px}
.bbtn small{font-size:10px;font-weight:600}

/* ===== PROFILE ===== */
.prof-hero{padding:30px 20px 20px;text-align:center}
.prof-av-wrap{position:relative;display:inline-block;margin-bottom:16px}
.prof-av{width:120px;height:120px;border-radius:50%;background:var(--grad);padding:3px;position:relative}
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
.pb-btn:active{background:var(--card3);transform:scale(.98)}

.set-list{margin-top:20px;padding:0 16px;display:flex;flex-direction:column;gap:8px}
.set-item{display:flex;align-items:center;gap:14px;padding:16px 18px;background:var(--card);border:1px solid var(--border);border-radius:var(--r)}
.set-icon{width:36px;height:36px;background:var(--card2);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:16px}
.set-name{flex:1;font-size:14px;font-weight:600}
.toggle{position:relative;width:46px;height:26px;background:var(--card3);border-radius:13px;cursor:pointer;transition:.2s}
.toggle.on{background:var(--green)}
.toggle::after{content:'';position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:#fff;transition:.2s;box-shadow:0 2px 4px rgba(0,0,0,.3)}
.toggle.on::after{left:23px}

.hist-empty{margin:24px 16px 0;background:var(--card);border:2px dashed var(--border);border-radius:var(--r2);padding:36px 20px;text-align:center}
.hist-icon{font-size:32px;color:var(--t3);margin-bottom:10px}
.hist-txt{font-size:13px;color:var(--t3);font-weight:500}

.support-btn{margin:20px 16px 0;padding:16px;border:1px solid var(--purple);border-radius:var(--rf);background:transparent;color:var(--t1);font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:8px;width:calc(100% - 32px);transition:.2s}
.support-btn:active{background:rgba(139,92,246,.1);transform:scale(.98)}

.empty{text-align:center;padding:60px 20px;grid-column:1/-1}
.empty-i{font-size:48px;margin-bottom:14px;opacity:.5}
.empty-t{font-size:14px;color:var(--t2);font-weight:500}
</style>
</head>
<body>

<!-- ============ ГОРОДА ============ -->
<div id="s-cities" class="screen active">
  <div class="top">
    <div class="top-l">
      <div class="top-badge">
        <div class="top-badge-icon">🌙</div>
        <span class="top-badge-txt">LUNA</span>
      </div>
    </div>
    <button class="btn-i" onclick="tgClose()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>
  </div>
  <div class="hero">
    <div class="brand">LUNA</div>
    <div class="sub">ESCORT AGENCY</div>
    <div class="online">
      <span style="width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;box-shadow:0 0 8px var(--green)"></span>
      <span>Сейчас свободны: <b id="total-on">0</b></span>
    </div>
  </div>
  <div class="stitle">Выберите город</div>
  <div class="cities" id="cities-list"></div>
  <div class="foot">
    <span>🔒 Безопасно</span>
    <span>•</span>
    <span>18+</span>
    <span>•</span>
    <span>Анонимно</span>
  </div>
</div>

<!-- ============ КАТАЛОГ ============ -->
<div id="s-catalog" class="screen">
  <div class="top">
    <div class="top-l">
      <div class="top-badge">
        <div class="top-badge-icon">🌙</div>
        <span class="top-badge-txt">LUNA</span>
      </div>
      <div class="top-city">
        <span>📍</span>
        <span id="cur-city">Москва</span>
        <span class="dot"></span>
        <span class="top-city-cnt" id="m-count">0</span>
      </div>
    </div>
    <button class="btn-i" onclick="go('cities')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
    </button>
  </div>
  <div class="sbar">
    <div class="swrap">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" id="sinput" placeholder="Поиск по ID модели..." onkeyup="doSearch(event)">
    </div>
    <button class="btn-f" onclick="showM('filters')">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/><circle cx="8" cy="6" r="2" fill="currentColor"/><circle cx="16" cy="12" r="2" fill="currentColor"/><circle cx="10" cy="18" r="2" fill="currentColor"/></svg>
    </button>
    <button class="btn-f" onclick="toggleFav()" id="fav-btn">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
    </button>
  </div>
  <div class="grid" id="grid"></div>
  <div class="bbar">
    <button class="bbtn active" onclick="goTab('catalog')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" 
