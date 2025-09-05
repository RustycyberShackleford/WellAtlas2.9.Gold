
import os, sqlite3, random, datetime, secrets
from flask import Flask, render_template, request, jsonify, abort, url_for

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
    cur.execute("CREATE TABLE IF NOT EXISTS sites(id INTEGER PRIMARY KEY, customer_id INTEGER, name TEXT, description TEXT, latitude REAL, longitude REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, site_id INTEGER, job_number TEXT, job_category TEXT, description TEXT, depth_ft REAL, casing_diameter_in REAL, pump_hp REAL, flow_rate_gpm REAL, static_level_ft REAL, drawdown_ft REAL, install_date TEXT, status TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS job_notes(id INTEGER PRIMARY KEY, job_id INTEGER, body TEXT, created_at TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS shares(token TEXT PRIMARY KEY, scope TEXT, target_id INTEGER, created_at TEXT)")
    c.commit(); c.close()

def seed_data():
    c = db(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM customers")
    if cur.fetchone()[0]>0: c.close(); return

    presidents = [
        "Washington","Adams","Jefferson","Madison","Monroe","JQ Adams","Jackson","Van Buren","Harrison","Tyler",
        "Polk","Taylor","Fillmore","Pierce","Buchanan","Lincoln","Johnson","Grant","Hayes","Garfield",
        "Arthur","Cleveland","Harrison2","Cleveland2","McKinley","TRoosevelt","Taft","Wilson","Harding","Coolidge",
        "Hoover","FDR","Truman","Eisenhower","Kennedy","LBJ","Nixon","Ford","Carter","Reagan"
    ]
    mining_terms = [
        "Mother Lode","Prospector's Claim","Stamp Mill","Ore Vein","Pay Dirt","Hydraulic Pit","Tailings Pile","Mine Shaft",
        "Pan Creek","Drift Tunnel","Headframe","Sluice Box","Bedrock Bend","Quartz Ridge","Assay Flats","Nugget Gulch",
        "Pickaxe Point","Rocker Reach","Gold Pan Flat","Tailrace Trail","Cradle Wash","Reef Edge","Alluvial Run","Creek Bend"
    ]

    rnd = random.Random(1337)
    job_no = 25001
    for pres in presidents:  # 40 customers
        addr = f"{rnd.randint(100,9999)} Main St, North State, CA"
        phone = f"(555) {rnd.randint(200,999)}-{rnd.randint(1000,9999)}"
        email = f"service@{pres.replace(' ','').lower()}.example"
        notes = "Key account. Routine service quarterly. Contact via dispatch. Field region: Cottonwood–Orland corridor."
        cur.execute("INSERT INTO customers(name,address,phone,email,notes) VALUES(?,?,?,?,?)",(pres,addr,phone,email,notes))
        cust_id = cur.lastrowid

        site_names = rnd.sample(mining_terms, k=len(mining_terms))
        for i in range(10):  # 10 sites each
            sname = site_names[i % len(site_names)]
            lat = 39.9 + rnd.uniform(-0.35,0.35)
            lon = -122.0 + rnd.uniform(-0.35,0.35)
            sdesc = f"Site '{sname}' near North State ag parcels; access gate requires advance call. Soil is sandy alluvium; recommended sanitary seal."
            cur.execute("INSERT INTO sites(customer_id,name,description,latitude,longitude) VALUES(?,?,?,?,?)",(cust_id,sname,sdesc,lat,lon))
            site_id = cur.lastrowid

            # One primary job per site for demo; could be expanded if needed
            cat = rnd.choice(["Domestic","Drilling","Ag","Electrical"])
            depth = rnd.choice([120,160,200,240,280,320,360,400])
            casing = rnd.choice([4,6,8])
            pump = rnd.choice([2,3,5,7.5,10])
            flow = rnd.choice([15,25,35,45,60])
            static = rnd.choice([20,30,40,50,60])
            draw = rnd.choice([5,10,15,20,25])
            status = rnd.choice(["Scheduled","In Progress","Complete"])
            jdesc = (f"{cat} well scope: target depth ~{depth} ft with {casing} in steel casing. "
                     f"Pump {pump} HP; expected yield {flow} GPM. Static water level {static} ft; drawdown {draw} ft under test. "
                     "Includes geologging, gravel pack, sanitary seal, chlorination, and electrical panel verification. "
                     "Deliverables: as-built, test curves, warranty card, and startup briefing.")
            cur.execute("""INSERT INTO jobs(site_id,job_number,job_category,description,depth_ft,casing_diameter_in,pump_hp,flow_rate_gpm,
                        static_level_ft,drawdown_ft,install_date,status)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (site_id,str(job_no),cat,jdesc,depth,casing,pump,flow,static,draw,str(datetime.date.today()),status))
            job_id = cur.lastrowid

            # Rich notes (4–7 entries)
            note_templates = [
                "Pre-construction meeting held with owner; utility locates requested. Crew: {crew}.",
                "Mobilized rig; staked pad; safety tailgate completed; GPS set at {lat:.5f}, {lon:.5f}.",
                "Began drilling in silty sands; penetration steady; fluid returns clear at 200 gpm.",
                "Casing set to {depth} ft; annulus gravel-packed; sanitary seal poured per spec.",
                "Installed {pump} HP pump; panel inspected; set pressure switch; wired per NEC.",
                "Test pumped at {flow} GPM; water clear at 30 min; drawdown at {draw} ft; static {static} ft.",
                "As-built recorded; site cleaned; turnover with owner; warranty and maintenance schedule provided."
            ]
            crews = ["Diaz","Kim","O'Neil","Harper","Singh","Ramirez","Nguyen"]
            k = rnd.randint(4,7)
            for t in note_templates[:k]:
                body = t.format(crew=rnd.choice(crews), lat=lat, lon=lon, depth=depth, pump=pump, flow=flow, draw=draw, static=static)
                cur.execute("INSERT INTO job_notes(job_id,body,created_at) VALUES(?,?,?)",(job_id, body, str(datetime.datetime.now())))

            job_no += 1

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

# ---------- Share links ----------
def _new_token(): return secrets.token_urlsafe(16)

@app.route("/share/customer/<int:cid>", methods=["POST"])
def share_create_customer(cid):
    c=db();cur=c.cursor()
    cur.execute("SELECT id FROM customers WHERE id=?", (cid,))
    if not cur.fetchone(): c.close(); abort(404)
    token=_new_token()
    cur.execute("INSERT INTO shares(token,scope,target_id,created_at) VALUES(?,?,?,?)",(token,"customer",cid,str(datetime.datetime.now())))
    c.commit(); c.close()
    return jsonify({"url": url_for("share_open", token=token, _external=True)})

@app.route("/share/job/<int:job_id>", methods=["POST"])
def share_create_job(job_id):
    c=db();cur=c.cursor()
    cur.execute("SELECT id FROM jobs WHERE id=?", (job_id,))
    if not cur.fetchone(): c.close(); abort(404)
    token=_new_token()
    cur.execute("INSERT INTO shares(token,scope,target_id,created_at) VALUES(?,?,?,?)",(token,"job",job_id,str(datetime.datetime.now())))
    c.commit(); c.close()
    return jsonify({"url": url_for("share_open", token=token, _external=True)})

@app.route("/share/<token>")
def share_open(token):
    c=db();cur=c.cursor()
    cur.execute("SELECT * FROM shares WHERE token=?", (token,)); sh=cur.fetchone()
    if not sh: c.close(); abort(404)
    if sh["scope"]=="customer":
        cid = sh["target_id"]
        cur.execute("SELECT * FROM customers WHERE id=?", (cid,)); customer=cur.fetchone()
        cur.execute("SELECT * FROM sites WHERE customer_id=? ORDER BY name", (cid,))
        sites = [dict(r) for r in cur.fetchall()]
        for s in sites:
            cur.execute("SELECT * FROM jobs WHERE site_id=? ORDER BY job_number", (s["id"],))
            s["jobs"] = [dict(r) for r in cur.fetchall()]
        c.close()
        return render_template("share_customer.html", customer=dict(customer), sites=sites)
    elif sh["scope"]=="job":
        jid = sh["target_id"]
        cur.execute("SELECT jobs.*, sites.name as site_name, sites.customer_id as customer_id FROM jobs JOIN sites ON sites.id=jobs.site_id WHERE jobs.id=?", (jid,))
        job = cur.fetchone()
        if not job: c.close(); abort(404)
        cur.execute("SELECT name FROM customers WHERE id=?", (job["customer_id"],)); cn=cur.fetchone()[0]
        cur.execute("SELECT * FROM job_notes WHERE job_id=? ORDER BY datetime(created_at) DESC", (jid,))
        notes=[dict(r) for r in cur.fetchall()]; c.close()
        return render_template("share_job.html", job=dict(job), customer_name=cn, site_name=job["site_name"], notes=notes)
    else:
        c.close(); abort(404)

# ---------- API ----------
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
    joins = ""; params = []; wh = []
    if job or q:
        joins += " LEFT JOIN jobs ON jobs.site_id = sites.id"
    if job:
        wh.append("jobs.job_category = ?"); params.append(job)
    if customer:
        wh.append("customers.name = ?"); params.append(customer)
    if q:
        like = f"%{q}%"
        wh.append("(customers.name LIKE ? OR sites.name LIKE ? OR sites.description LIKE ? OR jobs.job_number LIKE ? OR jobs.description LIKE ? OR EXISTS(SELECT 1 FROM job_notes jn WHERE jn.job_id = jobs.id AND jn.body LIKE ?))")
        params += [like, like, like, like, like, like]
    if wh:
        sql += joins + " WHERE " + " AND ".join(wh)
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
