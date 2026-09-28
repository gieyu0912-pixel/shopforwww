#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEOUL closet｜韓選衣櫥 — 韓式服裝電商（Python 標準庫）"""
import hashlib
import http.cookies
import http.server
import json
import os
import secrets
import sqlite3
import time
import urllib.parse
from datetime import datetime, timedelta
from email.parser import BytesParser
from email.policy import default as email_policy

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
UPLOADS = os.path.join(PUBLIC, "uploads")
DATA = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA, "shop.db")
SECRET = "seoul-closet-secret-key-change-me"
DEFAULT_USER = "admin"
DEFAULT_PASS = "2wsxcde3"
PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")

os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(DATA, exist_ok=True)
os.makedirs(os.path.join(PUBLIC, "images"), exist_ok=True)

PRODUCT_TEMPLATES = [
    ("오버사이즈 가디건", "韓系寬鬆針織外套", "針織", 1280),
    ("와이드 팬츠", "高腰垂墜寬褲", "褲裝", 980),
    ("플리츠 미니스커트", "學院風百褶迷你裙", "裙裝", 790),
    ("트렌치 코트", "經典駱駝色風衣", "外套", 1890),
    ("크롭 니트", "方領短版針織上衣", "針織", 690),
    ("린넨 블라우스", "亞麻澎袖襯衫", "上衣", 860),
    ("데님 자켓", "水洗牛仔外套", "外套", 1480),
    ("미디 스커트", "A 字過膝裙", "裙裝", 920),
    ("슬랙스", "修身西裝褲", "褲裝", 1080),
    ("후드 집업", "薄款連帽外套", "外套", 890),
    ("셔링 원피스", "抓皺方領洋裝", "洋裝", 1380),
    ("크롭 티", "短版素色上衣", "上衣", 490),
    ("카고 팬츠", "工裝寬褲", "褲裝", 1180),
    ("니트 베스트", "V 領針織背心", "針織", 720),
    ("플리츠 원피스", "百褶長洋裝", "洋裝", 1580),
    ("크롭 가디건", "短版排釦外套", "針織", 880),
    ("데님 스커트", "丹寧中長裙", "裙裝", 990),
    ("셔츠 원피스", "襯衫式洋裝", "洋裝", 1290),
    ("볼레로", "短版開襟罩衫", "外套", 650),
    ("하이웨스트 진", "高腰直筒牛仔褲", "褲裝", 1190),
]


def hash_pw(pw, salt=None):
    if salt is None:
        salt = secrets.token_hex(8)
    digest = hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def check_pw(pw, stored):
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return stored == pw
    return hashlib.sha256((salt + pw).encode("utf-8")).hexdigest() == digest


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = db()
    c = conn.cursor()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_kr TEXT,
            category TEXT,
            price INTEGER NOT NULL,
            image TEXT,
            stock INTEGER DEFAULT 20,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            store_711 TEXT NOT NULL,
            items_json TEXT NOT NULL,
            total INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            shipped_at TEXT
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            created_at TEXT
        );
        """
    )
    row = c.execute("SELECT value FROM settings WHERE key='password'").fetchone()
    if not row:
        now = datetime.now().strftime("%Y-%m-%d")
        c.execute("INSERT INTO settings(key,value) VALUES('password',?)", (hash_pw(DEFAULT_PASS),))
        c.execute("INSERT INTO settings(key,value) VALUES('password_changed',?)", (now,))
        c.execute("INSERT INTO settings(key,value) VALUES('username',?)", (DEFAULT_USER,))

    count = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        images = [f"p{str(i).zfill(2)}.jpg" for i in range(1, 10)]
        extra = ["0CLnX.jpg", "2KCvm.jpg", "5Fohd.jpg", "HQoZ1.jpg"]
        all_imgs = images + extra
        now = datetime.now().isoformat(timespec="seconds")
        colors = ["米白", "燕麥", "焦糖", "墨黑", "霧灰", "奶茶", "亞麻", "燕麥灰", "燕麥駝", "奶油"]
        for i in range(50):
            base = PRODUCT_TEMPLATES[i % len(PRODUCT_TEMPLATES)]
            color = colors[i % len(colors)]
            variant = (i // len(PRODUCT_TEMPLATES)) + 1
            name = f"{color}{base[1]}"
            if variant > 1:
                name = f"{name} Vol.{variant}"
            price = base[3] + (i % 5) * 50
            img = all_imgs[i % len(all_imgs)]
            c.execute(
                "INSERT INTO products(name,name_kr,category,price,image,stock,created_at) VALUES(?,?,?,?,?,?,?)",
                (name, base[0], base[2], price, img, 20 + (i % 8), now),
            )
    conn.commit()
    conn.close()


def get_setting(key, default=""):
    conn = db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = db()
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()


def parse_multipart(body, content_type):
    """Parse multipart/form-data without the removed cgi module (Python 3.13+)."""
    fields = {}
    files = []
    if not body or "multipart/form-data" not in (content_type or ""):
        return fields, files
    header = ("Content-Type: %s\r\nMIME-Version: 1.0\r\n\r\n" % content_type).encode("utf-8")
    msg = BytesParser(policy=email_policy).parsebytes(header + body)
    parts = list(msg.iter_parts()) or ([msg] if msg.get_content_disposition() else [])
    for part in parts:
        disp = part.get_content_disposition()
        name = part.get_param("name", header="content-disposition")
        filename = part.get_filename()
        payload = part.get_payload(decode=True)
        if payload is None:
            payload = b""
        if filename:
            files.append({"field": name or "images", "filename": filename, "data": payload})
        elif name:
            fields.setdefault(name, [])
            try:
                fields[name].append(payload.decode("utf-8"))
            except Exception:
                fields[name].append("")
    return fields, files


def password_due():
    raw = get_setting("password_changed", "")
    try:
        changed = datetime.strptime(raw[:10], "%Y-%m-%d")
    except Exception:
        return True, 90
    days = (datetime.now() - changed).days
    return days >= 90, max(0, 90 - days)


def make_session():
    token = secrets.token_hex(24)
    conn = db()
    conn.execute(
        "INSERT INTO sessions(token,created_at) VALUES(?,?)",
        (token, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    return token


def valid_session(token):
    if not token:
        return False
    conn = db()
    row = conn.execute("SELECT created_at FROM sessions WHERE token=?", (token,)).fetchone()
    conn.close()
    if not row:
        return False
    try:
        created = datetime.fromisoformat(row["created_at"])
    except Exception:
        return False
    return datetime.now() - created < timedelta(days=7)


MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "SeoulCloset/1.0"

    def log_message(self, fmt, *args):
        print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), fmt % args))

    def _cookie(self):
        raw = self.headers.get("Cookie", "")
        c = http.cookies.SimpleCookie()
        try:
            c.load(raw)
        except Exception:
            pass
        return c

    def session_token(self):
        c = self._cookie()
        if "sc_session" in c:
            return c["sc_session"].value
        return ""

    def is_admin(self):
        return valid_session(self.session_token())

    def send_json(self, obj, status=200, extra_headers=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, status=200):
        if not os.path.isfile(path):
            self.send_error(404, "Not Found")
            return
        ext = os.path.splitext(path)[1].lower()
        ctype = MIME.get(ext, "application/octet-stream")
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".css", ".js"):
            self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/api/products":
            conn = db()
            rows = conn.execute(
                "SELECT * FROM products ORDER BY id DESC"
            ).fetchall()
            conn.close()
            items = [dict(r) for r in rows]
            self.send_json({"ok": True, "products": items, "count": len(items)})
            return

        if path == "/api/admin/me":
            if not self.is_admin():
                self.send_json({"ok": False, "auth": False}, 401)
                return
            due, remain = password_due()
            self.send_json(
                {
                    "ok": True,
                    "auth": True,
                    "username": get_setting("username", DEFAULT_USER),
                    "password_due": due,
                    "days_remaining": remain,
                    "password_changed": get_setting("password_changed", ""),
                }
            )
            return

        if path == "/api/admin/orders":
            if not self.is_admin():
                self.send_json({"ok": False}, 401)
                return
            conn = db()
            rows = conn.execute(
                "SELECT * FROM orders ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, id ASC"
            ).fetchall()
            conn.close()
            orders = []
            for r in rows:
                o = dict(r)
                try:
                    o["items"] = json.loads(o.pop("items_json") or "[]")
                except Exception:
                    o["items"] = []
                orders.append(o)
            self.send_json({"ok": True, "orders": orders})
            return

        if path == "/api/admin/stats":
            if not self.is_admin():
                self.send_json({"ok": False}, 401)
                return
            conn = db()
            pending = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
            shipped = conn.execute("SELECT COUNT(*) FROM orders WHERE status='shipped'").fetchone()[0]
            products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            revenue = conn.execute("SELECT COALESCE(SUM(total),0) FROM orders").fetchone()[0]
            conn.close()
            self.send_json(
                {"ok": True, "pending": pending, "shipped": shipped, "products": products, "revenue": revenue}
            )
            return

        # static / pages（相容 GitHub 把 css/js/images 放在根目錄或 public/）
        def resolve_static(*rel_parts):
            candidates = [
                os.path.normpath(os.path.join(PUBLIC, *rel_parts)),
                os.path.normpath(os.path.join(ROOT, *rel_parts)),
            ]
            for cand in candidates:
                if os.path.isfile(cand) and (cand.startswith(PUBLIC) or cand.startswith(ROOT)):
                    return cand
            return None

        if path in ("/", "/index.html"):
            found = resolve_static("index.html")
            if found:
                self.send_file(found)
                return
        if path in ("/admin", "/admin/", "/admin.html"):
            found = resolve_static("admin.html")
            if found:
                self.send_file(found)
                return
        if path.startswith("/images/") or path.startswith("/uploads/") or path.startswith("/css/") or path.startswith("/js/"):
            found = resolve_static(path.lstrip("/"))
            if found:
                self.send_file(found)
                return
        found = resolve_static(path.lstrip("/"))
        if found:
            self.send_file(found)
            return
        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/checkout":
            data = self.read_json()
            name = (data.get("name") or "").strip()
            phone = (data.get("phone") or "").strip()
            store = (data.get("store") or "").strip()
            items = data.get("items") or []
            if not name or not phone or not store or not items:
                self.send_json({"ok": False, "error": "請填寫姓名、手機、7-11 門市，並選擇商品"}, 400)
                return
            if not phone.replace("+", "").replace("-", "").replace(" ", "").isdigit() or len(phone) < 8:
                self.send_json({"ok": False, "error": "手機號碼格式不正確"}, 400)
                return
            total = 0
            clean_items = []
            conn = db()
            for it in items:
                try:
                    pid = int(it.get("id"))
                    qty = max(1, int(it.get("qty") or 1))
                except Exception:
                    continue
                row = conn.execute("SELECT id,name,price FROM products WHERE id=?", (pid,)).fetchone()
                if not row:
                    continue
                total += row["price"] * qty
                clean_items.append({"id": row["id"], "name": row["name"], "price": row["price"], "qty": qty})
            if not clean_items:
                conn.close()
                self.send_json({"ok": False, "error": "購物車沒有有效商品"}, 400)
                return
            now = datetime.now().isoformat(timespec="seconds")
            cur = conn.execute(
                "INSERT INTO orders(customer_name,phone,store_711,items_json,total,status,created_at) VALUES(?,?,?,?,?,?,?)",
                (name, phone, store, json.dumps(clean_items, ensure_ascii=False), total, "pending", now),
            )
            oid = cur.lastrowid
            conn.commit()
            conn.close()
            self.send_json({"ok": True, "order_id": oid, "total": total})
            return

        if path == "/api/admin/login":
            data = self.read_json()
            user = (data.get("username") or "").strip()
            pw = data.get("password") or ""
            if user != get_setting("username", DEFAULT_USER) or not check_pw(pw, get_setting("password")):
                time.sleep(0.4)
                self.send_json({"ok": False, "error": "帳號或密碼錯誤"}, 401)
                return
            token = make_session()
            cookie = "sc_session=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800" % token
            due, remain = password_due()
            self.send_json(
                {"ok": True, "password_due": due, "days_remaining": remain},
                extra_headers={"Set-Cookie": cookie},
            )
            return

        if path == "/api/admin/logout":
            token = self.session_token()
            if token:
                conn = db()
                conn.execute("DELETE FROM sessions WHERE token=?", (token,))
                conn.commit()
                conn.close()
            self.send_json(
                {"ok": True},
                extra_headers={"Set-Cookie": "sc_session=; Path=/; Max-Age=0"},
            )
            return

        if path == "/api/admin/password":
            if not self.is_admin():
                self.send_json({"ok": False}, 401)
                return
            data = self.read_json()
            old = data.get("old") or ""
            new = data.get("new") or ""
            if not check_pw(old, get_setting("password")):
                self.send_json({"ok": False, "error": "舊密碼不正確"}, 400)
                return
            if len(new) < 8:
                self.send_json({"ok": False, "error": "新密碼至少 8 碼"}, 400)
                return
            set_setting("password", hash_pw(new))
            set_setting("password_changed", datetime.now().strftime("%Y-%m-%d"))
            self.send_json({"ok": True})
            return

        if path.startswith("/api/admin/ship/"):
            if not self.is_admin():
                self.send_json({"ok": False}, 401)
                return
            try:
                oid = int(path.rsplit("/", 1)[-1])
            except ValueError:
                self.send_json({"ok": False, "error": "訂單編號錯誤"}, 400)
                return
            conn = db()
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE orders SET status='shipped', shipped_at=? WHERE id=? AND status='pending'",
                (now, oid),
            )
            conn.commit()
            conn.close()
            self.send_json({"ok": True, "id": oid})
            return

        if path == "/api/admin/upload":
            if not self.is_admin():
                self.send_json({"ok": False, "error": "未登入"}, 401)
                return
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(n) if n else b""
            try:
                fields, files = parse_multipart(body, self.headers.get("Content-Type", ""))
            except Exception as e:
                self.send_json({"ok": False, "error": "無法解析上傳檔案: %s" % e}, 400)
                return

            files = [f for f in files if (f.get("field") or "images") == "images" or f.get("filename")]
            if not files:
                self.send_json({"ok": False, "error": "請選擇圖片（欄位名稱 images）"}, 400)
                return

            created = []
            conn = db()
            now = datetime.now().isoformat(timespec="seconds")
            max_files = 30
            for idx, f in enumerate(files[:max_files]):
                raw = f.get("filename") or ""
                if not raw:
                    continue
                ext = os.path.splitext(raw)[1].lower()
                if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                    continue
                fname = "u_%s_%s%s" % (int(time.time()), secrets.token_hex(4), ext)
                dest = os.path.join(UPLOADS, fname)
                try:
                    with open(dest, "wb") as out:
                        out.write(f.get("data") or b"")
                except Exception:
                    continue
                base = os.path.splitext(os.path.basename(raw))[0]
                name = (base[:40] if base else "韓系單品 %s" % datetime.now().strftime("%m%d"))
                price = 890 + (idx % 9) * 100
                cat = "新品"
                conn.execute(
                    "INSERT INTO products(name,name_kr,category,price,image,stock,created_at) VALUES(?,?,?,?,?,?,?)",
                    (name, "신상", cat, price, "uploads/" + fname, 20, now),
                )
                created.append({"name": name, "image": "uploads/" + fname, "price": price})
            conn.commit()
            conn.close()
            self.send_json({"ok": True, "added": len(created), "products": created})
            return

        self.send_error(404, "Not Found")


def main():
    init_db()
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print("=" * 56)
    print("  SEOUL closet｜韓選衣櫥")
    print("  前台  http://127.0.0.1:%s/" % PORT)
    print("  後台  http://127.0.0.1:%s/admin" % PORT)
    print("  帳號  admin")
    print("  密碼  2wsxcde3")
    print("=" * 56)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
        server.server_close()


if __name__ == "__main__":
    main()
