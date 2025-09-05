
import os, sqlite3, random
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, abort

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "wellatlas.db")
os.makedirs(DATA_DIR, exist_ok=True)

CUSTOMER_NAMES = [
    "Washington Drilling Co.","Lincoln Pump & Well","Jefferson Water Systems","Roosevelt Groundwater Services","Kennedy HydroTech",
    "Adams Well & Pump","Madison Waterworks","Jackson Ag & Irrigation","Grant Pumping Solutions","Truman Drilling & Pump Service"
]
CATEGORIES = ["Domestic","Drilling","Ag","Electrical"]
MINING_TERMS = [
    "Mother Lode","Pay Dirt","Sluice Box","Stamp Mill","Placer Claim","Drift Mine","Hydraulic Pit","Gold Pan","Tailings","Bedrock",
    "Pick and Shovel","Ore Cart","Quartz Vein","Mine Shaft","Black Sand","Rocker Box","Prospect Hole","Hard Rock","Assay Office","Grubstake",
    "Lode Claim","Panning Dish","Cradle Rock","Dust Gold","Nugget Patch","Timbering","Creek Claim","Pay Streak","Ventilation Shaft","Bucket Line",
    "Dredge Cut","Amalgam Press","Prospector's Camp","Claim Jumper","Mining Camp","Gold Dust","Mine Portal","Crosscut Drift","Incline Shaft","Strike Zone",
    "Wash Plant","Headframe","Drill Core","Stope Chamber","Milling House","Hoist House","Smelter Works","Ore Bin","Tunnel Bore","Grizzly Screen",
    "Hydraulic Monitor","Pay Streak North","Bedrock Bench","Tailrace","Assayer Cabin","Prospect Ridge","Quartz Ledge","Stope Ladder","Ore Chute","Mill Tailings",
    "Gulch Claim","Placer Bench","Hardrock Portal","Sluice Run","Settling Pond","Stamp Battery","Headframe East","Headframe West","Sump Shaft","Timber Set",
    "Carbide Lamp","Blacksmith Shop","Gold Pocket","Creek Box","Bunkhouse","Prospect Drift","Muck Pile","Vent Raise","Winze Shaft","Crosscut East",
    "Crosscut West","Assay Lab","Tramway","Sorting Shed","Crusher House","Jig Plant","Ball Mill","Pan Station","Gold Room","Assay Scales",
    "Raise Station","Spiral Chute","Belt House","Gate Valve","Water Box","Pipe Manifold","Control Shed","Yard Pit","Mix Plant","Well Yard"
]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_schema():
    c = db(); cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, address TEXT, phone TEXT, email TEXT, notes TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS sites (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, customer TEXT, description TEXT, latitude REAL, longitude REAL, deleted INTEGER DEFAULT 0, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, site_id INTEGER, job_number TEXT, job_category TEXT, description TEXT, deleted INTEGER DEFAULT 0, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, site_id INTEGER, body TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS job_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER, body TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS share_tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, target_id INTEGER, token TEXT UNIQUE, created_at TEXT)")
    c.commit(); c.close()

def seed_demo_if_empty():
    c = db(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM sites"); have = cur.fetchone()[0]
    if have > 0: c.close(); return
    now = datetime.utcnow().isoformat()
    for name in CUSTOMER_NAMES:
        cur.execute("INSERT OR IGNORE INTO customers (name,address,phone,email,notes,created_at) VALUES (?,?,?,?,?,?)",
                    (name, "123 Demo Rd, North State, CA", "(530) 555-0123", "demo@example.com", "Preferred customer.", now))
    region = [(40.385,-122.280),(40.178,-122.240),(39.927,-122.180),(39.728,-121.837),(39.747,-122.194)]
    terms = MINING_TERMS[:100]; random.shuffle(terms)
    job_no = 25001; idx = 0
    for cust in CUSTOMER_NAMES:
        for _ in range(10):
            name = terms[idx]; idx += 1
            lat, lon = random.choice(region)
            cur.execute("INSERT INTO sites (name,customer,description,latitude,longitude,created_at,deleted) VALUES (?,?,?,?,?,?,0)", (name, cust, f"Primary site for {name}.", lat, lon, now))
            sid = cur.lastrowid
            cat = random.choice(CATEGORIES)
            cur.execute("INSERT INTO jobs (site_id,job_number,job_category,description,created_at,deleted) VALUES (?,?,?,?,?,0)", (sid, str(job_no), cat, f"Job #{job_no} at {name}.", now))
            job_no += 1
    c.commit(); c.close()

ensure_schema()
seed_demo_if_empty()

MAPTILER_KEY = os.environ.get("MAPTILER_KEY","")
app = Flask(__name__)

@app.route("/healthz")
def healthz(): return "ok", 200

@app.route("/")
def index(): return render_template("index.html", maptiler_key=MAPTILER_KEY)

# APIs
@app.route("/api/customers")
def api_customers():
    c = db(); cur = c.cursor()
    cur.execute("SELECT id,name FROM customers ORDER BY name ASC")
    out = [dict(r) for r in cur.fetchall()]; c.close(); return jsonify(out)

@app.route("/api/sites")
def api_sites():
    q = (request.args.get("q") or "").strip()
    job = (request.args.get("job") or "").strip()
    cust = (request.args.get("customer") or "").strip()
    c = db(); cur = c.cursor()
    clauses = ["s.deleted=0"]; params = []
    if q:
        clauses.append("(s.name LIKE ? OR s.description LIKE ? OR s.customer LIKE ? OR EXISTS (SELECT 1 FROM notes n WHERE n.site_id=s.id AND n.body LIKE ?) OR EXISTS (SELECT 1 FROM job_notes jn WHERE jn.job_id IN (SELECT id FROM jobs WHERE site_id=s.id) AND jn.body LIKE ?))")
        params += [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"]
    if job:
        clauses.append("EXISTS (SELECT 1 FROM jobs j WHERE j.site_id=s.id AND j.deleted=0 AND j.job_category=?)"); params.append(job)
    if cust:
        clauses.append("s.customer=?"); params.append(cust)
    sql = "SELECT s.* FROM sites s WHERE " + " AND ".join(clauses) + " ORDER BY datetime(s.created_at) DESC"
    cur.execute(sql, params); rows = [dict(r) for r in cur.fetchall()]
    c.close(); return jsonify(rows)

# Quick Add
@app.route("/api/quick_add", methods=["POST"])
def api_quick_add():
    payload = request.get_json(force=True)
    name = (payload.get("customer_name") or "").strip()
    if not name: return jsonify({"ok":False,"error":"Missing customer name"}), 400
    c = db(); cur = c.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("INSERT OR IGNORE INTO customers (name, created_at) VALUES (?,?)", (name, now))
    site_name = (payload.get("site_name") or "New Site").strip()
    lat = payload.get("latitude") or ""
    lon = payload.get("longitude") or ""
    try: latf = float(lat) if lat != "" else None; lonf = float(lon) if lon != "" else None
    except ValueError: latf = lonf = None
    cur.execute("INSERT INTO sites (name, customer, latitude, longitude, created_at, deleted) VALUES (?,?,?,?,?,0)", (site_name, name, latf, lonf, now))
    sid = cur.lastrowid
    jnum = (payload.get("job_number") or "25999").strip()
    jcat = (payload.get("job_category") or "Domestic").strip()
    cur.execute("INSERT INTO jobs (site_id, job_number, job_category, created_at, deleted) VALUES (?,?,?,?,0)", (sid, jnum, jcat, now))
    c.commit(); c.close()
    return jsonify({"ok":True,"site_id":sid})

# Pages + create forms
@app.route("/customers", methods=["GET"])
def customers_index():
    c = db(); cur = c.cursor()
    cur.execute("SELECT * FROM customers ORDER BY name"); rows = cur.fetchall(); c.close()
    return render_template("customers.html", customers=rows)

@app.route("/customers/create", methods=["POST"])
def create_customer():
    f = request.form; now = datetime.utcnow().isoformat()
    c = db(); cur = c.cursor()
    cur.execute("INSERT OR IGNORE INTO customers (name,phone,email,address,notes,created_at) VALUES (?,?,?,?,?,?)",
                (f.get("name"), f.get("phone"), f.get("email"), f.get("address"), f.get("notes"), now))
    c.commit(); c.close()
    return redirect(url_for("customers_index"))

@app.route("/sites", methods=["GET"])
def sites_index():
    c = db(); cur = c.cursor()
    cur.execute("SELECT * FROM sites WHERE deleted=0 ORDER BY name"); rows = cur.fetchall(); c.close()
    return render_template("sites.html", sites=rows)

@app.route("/sites/create", methods=["POST"])
def create_site():
    f = request.form; now = datetime.utcnow().isoformat()
    lat = f.get("latitude"); lon = f.get("longitude")
    try: latf = float(lat) if lat else None; lonf = float(lon) if lon else None
    except ValueError: latf = lonf = None
    c = db(); cur = c.cursor()
    cur.execute("INSERT INTO sites (name,customer,latitude,longitude,description,created_at,deleted) VALUES (?,?,?,?,?,?,0)",
                (f.get("name"), f.get("customer"), latf, lonf, f.get("description"), now))
    c.commit(); c.close()
    return redirect(url_for("sites_index"))

@app.route("/jobs", methods=["GET"])
def jobs_index():
    c = db(); cur = c.cursor()
    cur.execute("SELECT * FROM jobs WHERE deleted=0 ORDER BY CAST(job_number AS INTEGER)"); rows = cur.fetchall(); c.close()
    return render_template("jobs.html", jobs=rows)

@app.route("/jobs/create", methods=["POST"])
def create_job_global():
    f = request.form; now = datetime.utcnow().isoformat()
    c = db(); cur = c.cursor()
    cur.execute("INSERT INTO jobs (site_id,job_number,job_category,description,created_at,deleted) VALUES (?,?,?,?,?,0)",
                (f.get("site_id"), f.get("job_number"), f.get("job_category"), f.get("description"), now))
    c.commit(); c.close()
    return redirect(url_for("jobs_index"))

@app.route("/site/<int:site_id>")
def site_detail(site_id):
    c = db(); cur = c.cursor()
    cur.execute("SELECT * FROM sites WHERE id=?", (site_id,)); site = cur.fetchone()
    if not site: c.close(); abort(404)
    cur.execute("SELECT * FROM jobs WHERE site_id=? AND deleted=0 ORDER BY datetime(created_at) DESC", (site_id,)); jobs = cur.fetchall()
    c.close()
    return render_template("site_detail.html", site=site, jobs=jobs)

@app.route("/site/<int:site_id>/job/create", methods=["POST"])
def create_job(site_id):
    f = request.form; now = datetime.utcnow().isoformat()
    c = db(); cur = c.cursor()
    cur.execute("INSERT INTO jobs (site_id,job_number,job_category,description,created_at,deleted) VALUES (?,?,?,?,?,0)",
                (site_id, f.get("job_number"), f.get("job_category"), f.get("description"), now))
    c.commit(); c.close()
    return redirect(url_for("site_detail", site_id=site_id))

@app.route("/customer/<int:cid>")
def customer_detail(cid):
    c = db(); cur = c.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (cid,)); customer = cur.fetchone()
    if not customer: c.close(); abort(404)
    cur.execute("SELECT * FROM sites WHERE customer=? AND deleted=0 ORDER BY name", (customer["name"],)); sites = cur.fetchall()
    c.close()
    return render_template("customer_detail.html", customer=customer, sites=sites)

# Share links
def create_share_token(kind, target_id):
    import secrets
    tok = secrets.token_urlsafe(16)
    c = db(); cur = c.cursor()
    cur.execute("INSERT INTO share_tokens (kind,target_id,token,created_at) VALUES (?,?,?,?)",(kind,target_id,tok,datetime.utcnow().isoformat()))
    c.commit(); c.close(); return tok

@app.route("/share/create/customer/<int:cid>", methods=["POST"])
def share_create_customer(cid):
    tok = create_share_token("customer", cid)
    return jsonify({"link": url_for("share_view_customer", token=tok, _external=True)})

@app.route("/share/create/job/<int:job_id>", methods=["POST"])
def share_create_job(job_id):
    tok = create_share_token("job", job_id)
    return jsonify({"link": url_for("share_view_job", token=tok, _external=True)})

@app.route("/s/customer/<token>")
def share_view_customer(token):
    c = db(); cur = c.cursor()
    cur.execute("SELECT * FROM share_tokens WHERE kind='customer' AND token=?", (token,)); t = cur.fetchone()
    if not t: c.close(); abort(404)
    cur.execute("SELECT * FROM customers WHERE id=?", (t["target_id"],)); customer = cur.fetchone()
    cur.execute("SELECT * FROM sites WHERE customer=? AND deleted=0 ORDER BY name", (customer["name"],)); sites = cur.fetchall()
    cur.execute("SELECT j.* FROM jobs j JOIN sites s ON s.id=j.site_id WHERE s.customer=? AND j.deleted=0 ORDER BY CAST(j.job_number AS INTEGER)", (customer["name"],)); jobs = cur.fetchall()
    c.close()
    return render_template("share_customer.html", customer=customer, sites=sites, jobs=jobs)

@app.route("/s/job/<token>")
def share_view_job(token):
    c = db(); cur = c.cursor()
    cur.execute("SELECT * FROM share_tokens WHERE kind='job' AND token=?", (token,)); t = cur.fetchone()
    if not t: c.close(); abort(404)
    cur.execute("SELECT * FROM jobs WHERE id=?", (t["target_id"],)); job = cur.fetchone()
    cur.execute("SELECT * FROM sites WHERE id=?", (job["site_id"],)); site = cur.fetchone()
    c.close()
    return render_template("share_job.html", job=job, site=site)

MAPTILER_KEY = os.environ.get("MAPTILER_KEY","")
app.config["MAPTILER_KEY"] = MAPTILER_KEY

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
