
import os, sqlite3, random, datetime
from flask import Flask, render_template, request, jsonify, abort

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "wellatlas.db")

app = Flask(__name__)

def db():
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def ensure_schema():
    c = db(); cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, name TEXT UNIQUE, address TEXT, phone TEXT, email TEXT, notes TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS sites(id INTEGER PRIMARY KEY, customer_id INTEGER, name TEXT, latitude REAL, longitude REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, site_id INTEGER, job_number TEXT, job_category TEXT, description TEXT, depth_ft REAL, casing_diameter_in REAL, pump_hp REAL, flow_rate_gpm REAL, static_level_ft REAL, drawdown_ft REAL, install_date TEXT, status TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS job_notes(id INTEGER PRIMARY KEY, job_id INTEGER, body TEXT, created_at TEXT)")
    c.commit(); c.close()

def seed_data():
    c = db(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM customers")
    if cur.fetchone()[0]>0: c.close(); return
    presidents = ["Washington","Lincoln","Jefferson","Roosevelt","Kennedy","Adams","Madison","Jackson","Grant","Truman"]
    terms = ["Mother Lode","Prospector's Claim","Stamp Mill","Ore Vein","Pay Dirt","Hydraulic Pit","Tailings Pile","Mine Shaft","Pan Creek","Drift Tunnel"]*10
    random.shuffle(terms)
    job_no = 25001
    for pres in presidents:
        cur.execute("INSERT INTO customers(name,address,phone,email,notes) VALUES(?,?,?,?,?)",(pres+" Well Co.","","555-01%02d"%random.randint(0,99),"info@%s.com"%pres.lower(),"VIP account"))
        cust_id = cur.lastrowid
        for i in range(10):
            site_name = terms.pop()
            lat = 39.9 + random.uniform(-0.3,0.3)
            lon = -122.0 + random.uniform(-0.3,0.3)
            cur.execute("INSERT INTO sites(customer_id,name,latitude,longitude) VALUES(?,?,?,?)",(cust_id,site_name,lat,lon))
            site_id = cur.lastrowid
            depth = random.choice([120,160,200,240,280,320])
            casing = random.choice([4,6,8])
            pump = random.choice([2,3,5,7.5])
            flow = random.choice([15,25,35,45])
            static = random.choice([20,30,40,50])
            draw = random.choice([5,10,15,20])
            status = random.choice(["Scheduled","In Progress","Complete"])
            cur.execute("""INSERT INTO jobs(site_id,job_number,job_category,description,depth_ft,casing_diameter_in,pump_hp,flow_rate_gpm,static_level_ft,drawdown_ft,install_date,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (site_id,str(job_no),random.choice(["Domestic","Drilling","Ag","Electrical"]),"Demo job description",depth,casing,pump,flow,static,draw,str(datetime.date.today()),status))
            job_id = cur.lastrowid
            for n in ["Mobilized crew","Drilling operations underway","Installed pump and tested"]:
                cur.execute("INSERT INTO job_notes(job_id,body,created_at) VALUES(?,?,?)",(job_id,n,str(datetime.datetime.now())))
            job_no+=1
    c.commit(); c.close()

@app.route("/")
def index():
    return render_template("index.html", maptiler_key=os.getenv("MAPTILER_KEY",""))

@app.route("/customers")
def customers_index():
    c=db();cur=c.cursor();cur.execute("SELECT * FROM customers ORDER BY name")
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template("customers.html", customers=rows)

@app.route("/sites")
def sites_index():
    c=db();cur=c.cursor()
    cur.execute("SELECT sites.*, customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id ORDER BY customers.name, sites.name")
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template("sites.html", sites=rows)

@app.route("/jobs")
def jobs_index():
    c=db();cur=c.cursor()
    cur.execute("SELECT jobs.*, sites.name as site_name FROM jobs JOIN sites ON sites.id=jobs.site_id ORDER BY job_number")
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template("jobs.html", jobs=rows)

@app.route("/customer/<int:cid>")
def customer_detail(cid):
    c=db();cur=c.cursor()
    cur.execute("SELECT * FROM customers WHERE id=?", (cid,)); customer=cur.fetchone()
    if not customer: c.close(); abort(404)
    cur.execute("SELECT * FROM sites WHERE customer_id=? ORDER BY name", (cid,))
    sites=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template("customer_detail.html", customer=dict(customer), sites=sites)

@app.route("/site/<int:site_id>")
def site_detail(site_id):
    c=db();cur=c.cursor()
    cur.execute("SELECT sites.*, customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id WHERE sites.id=?", (site_id,))
    site=cur.fetchone()
    if not site: c.close(); abort(404)
    cur.execute("SELECT * FROM jobs WHERE site_id=? ORDER BY job_number", (site_id,))
    jobs=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template("site_detail.html", site=dict(site), jobs=jobs)

@app.route("/site/<int:site_id>/job/<int:job_id>")
def job_detail(site_id,job_id):
    c=db();cur=c.cursor()
    cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,)); job=cur.fetchone()
    if not job or job["site_id"]!=site_id: c.close(); abort(404)
    cur.execute("SELECT sites.*, customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id WHERE sites.id=?", (site_id,))
    site=cur.fetchone()
    cur.execute("SELECT * FROM job_notes WHERE job_id=? ORDER BY datetime(created_at) DESC", (job_id,))
    notes=[dict(r) for r in cur.fetchall()]; c.close()
    return render_template("job_detail.html", site=dict(site), job=dict(job), notes=notes)

@app.route("/api/customers")
def api_customers():
    c=db();cur=c.cursor();cur.execute("SELECT * FROM customers ORDER BY name")
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return jsonify(rows)

@app.route("/api/sites")
def api_sites():
    q = (request.args.get("q") or "").strip()
    job = (request.args.get("job") or "").strip()
    customer = (request.args.get("customer") or "").strip()
    c=db();cur=c.cursor()
    sql = "SELECT DISTINCT sites.*, customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id"
    params = []
    if job or q:
        sql += " LEFT JOIN jobs ON jobs.site_id = sites.id"
    wh = []
    if job:
        wh.append("jobs.job_category = ?"); params.append(job)
    if customer:
        wh.append("customers.name = ?"); params.append(customer)
    if q:
        like = f"%{q}%"
        wh.append("(customers.name LIKE ? OR sites.name LIKE ? OR jobs.job_number LIKE ? OR jobs.description LIKE ?)")
        params += [like, like, like, like]
    if wh: sql += " WHERE " + " AND ".join(wh)
    sql += " ORDER BY customers.name, sites.name"
    cur.execute(sql, params)
    rows=[dict(r) for r in cur.fetchall()]; c.close()
    return jsonify(rows)

@app.route("/healthz")
def healthz(): return "ok"

@app.errorhandler(404)
def nf(e): return ("Not found", 404)
@app.errorhandler(500)
def ie(e): return ("Internal error", 500)

if __name__ == "__main__":
    ensure_schema(); seed_data()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
else:
    ensure_schema(); seed_data()
