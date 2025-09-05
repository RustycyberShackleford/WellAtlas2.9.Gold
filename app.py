
import os, sqlite3, random, datetime
from flask import Flask, render_template, request, jsonify, abort, url_for

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'wellatlas.db')

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def ensure_schema():
    c = db(); cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS sites(id INTEGER PRIMARY KEY, customer_id INTEGER, name TEXT, latitude REAL, longitude REAL, FOREIGN KEY(customer_id) REFERENCES customers(id))")
    cur.execute("CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, site_id INTEGER, job_number TEXT, job_category TEXT, description TEXT, depth_ft REAL, casing_diameter_in REAL, pump_hp REAL, flow_rate_gpm REAL, static_level_ft REAL, drawdown_ft REAL, install_date TEXT, status TEXT, FOREIGN KEY(site_id) REFERENCES sites(id))")
    cur.execute("CREATE TABLE IF NOT EXISTS job_notes(id INTEGER PRIMARY KEY, job_id INTEGER, body TEXT, created_at TEXT, FOREIGN KEY(job_id) REFERENCES jobs(id))")
    c.commit(); c.close()

def seed_data():
    c = db(); cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM customers"); 
    if cur.fetchone()[0]>0: c.close(); return
    presidents = ["Washington","Lincoln","Jefferson","Roosevelt","Kennedy","Adams","Madison","Jackson","Grant","Truman"]
    terms = ["Mother Lode","Prospector's Claim","Stamp Mill","Ore Vein","Pay Dirt","Hydraulic Pit","Tailings Pile","Mine Shaft","Pan Creek","Drift Tunnel"]*10
    random.shuffle(terms)
    job_no = 25001
    for pres in presidents:
        cur.execute("INSERT INTO customers(name,phone,email) VALUES(?,?,?)",(pres+" Well Co.","555-0100","info@%s.com"%pres.lower()))
        cust_id = cur.lastrowid
        for i in range(10):
            site_name = terms.pop()
            lat = 39.9 + random.uniform(-0.3,0.3)
            lon = -122.0 + random.uniform(-0.3,0.3)
            cur.execute("INSERT INTO sites(customer_id,name,latitude,longitude) VALUES(?,?,?,?)",(cust_id,site_name,lat,lon))
            site_id = cur.lastrowid
            depth = random.choice([120,160,200,240,280])
            casing = random.choice([4,6,8])
            pump = random.choice([2,3,5,7.5])
            flow = random.choice([15,25,35,45])
            static = random.choice([20,30,40,50])
            draw = random.choice([5,10,15])
            status = random.choice(["Scheduled","In Progress","Complete"])
            cur.execute("INSERT INTO jobs(site_id,job_number,job_category,description,depth_ft,casing_diameter_in,pump_hp,flow_rate_gpm,static_level_ft,drawdown_ft,install_date,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (site_id,str(job_no),random.choice(["Domestic","Drilling","Ag","Electrical"]),"Demo job description",depth,casing,pump,flow,static,draw,str(datetime.date.today()),status))
            job_id = cur.lastrowid
            for n in ["Mobilized crew","Drilling operations underway","Installed pump and tested"]:
                cur.execute("INSERT INTO job_notes(job_id,body,created_at) VALUES(?,?,?)",(job_id,n,str(datetime.datetime.now())))
            job_no+=1
    c.commit(); c.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/customers")
def api_customers():
    c=db();cur=c.cursor();cur.execute("SELECT * FROM customers");rows=[dict(r) for r in cur.fetchall()];c.close();return jsonify(rows)

@app.route("/api/sites")
def api_sites():
    c=db();cur=c.cursor();cur.execute("SELECT sites.*,customers.name as customer FROM sites JOIN customers ON customers.id=sites.customer_id");rows=[dict(r) for r in cur.fetchall()];c.close();return jsonify(rows)

@app.route("/site/<int:site_id>/job/<int:job_id>")
def job_detail(site_id,job_id):
    c=db();cur=c.cursor()
    cur.execute("SELECT * FROM jobs WHERE id=?",(job_id,));job=cur.fetchone()
    cur.execute("SELECT * FROM sites WHERE id=?",(site_id,));site=cur.fetchone()
    cur.execute("SELECT * FROM job_notes WHERE job_id=?",(job_id,));notes=cur.fetchall()
    c.close()
    if not job or not site: abort(404)
    return render_template("job_detail.html",site=site,job=job,notes=notes)

@app.route("/healthz")
def healthz(): return "ok"

ensure_schema(); seed_data()
