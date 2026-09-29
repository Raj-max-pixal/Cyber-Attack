"""Vercel serverless API for the AttackWeave demo."""
import hashlib, json, os, secrets, sqlite3
from flask import Flask, jsonify, request
from itsdangerous import URLSafeTimedSerializer, BadSignature

app = Flask(__name__)
DB = "/tmp/attackweave.db"
signer = URLSafeTimedSerializer(os.environ.get("ATTACKWEAVE_SECRET", "byteathon-demo-secret-change-me"))
TIMELINE=[{"time":"09:12","event":"Unusual sign-in accepted","detail":"Finance user authenticated through an unfamiliar VPN exit node.","mitre":"T1078"},{"time":"09:14","event":"Malicious DNS beacon","detail":"LAPTOP-07 resolved update-check[.]cloud for the first time.","mitre":"T1071.004"},{"time":"09:17","event":"Encoded PowerShell launched","detail":"An obfuscated command ran from a newly-created user context.","mitre":"T1059.001"},{"time":"09:21","event":"Lateral movement to FILE-02","detail":"An uncommon ADMIN$ share route was opened from LAPTOP-07.","mitre":"T1021.002"},{"time":"09:25","event":"Domain ticket at risk","detail":"JUMP-01 requested a service ticket with abnormal source context.","mitre":"T1550.003"}]
def db():
    c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.executescript("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT);CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY,user_id INTEGER,title TEXT,severity TEXT,risk INTEGER,confidence INTEGER,status TEXT,timeline TEXT);");c.commit();return c
def hash_password(x): return hashlib.sha256(x.encode()).hexdigest()
def auth():
    try:return signer.loads(request.headers.get("Authorization","").replace("Bearer ",""),max_age=86400)
    except BadSignature:return None
def need_user():
    u=auth()
    return u or (jsonify(error="Please sign in to continue."),401)
def pack(row):
    x=dict(row);x["timeline"]=json.loads(x["timeline"]);return x
def create(user,title,timeline):
    c=db();risk=min(98,60+len(timeline)*7);confidence=min(97,72+len(timeline)*5);cur=c.execute("INSERT INTO incidents(user_id,title,severity,risk,confidence,status,timeline) VALUES(?,?,?,?,?,?,?)",(user["id"],title,"Critical",risk,confidence,"Investigating",json.dumps(timeline)));c.commit();item=pack(c.execute("SELECT * FROM incidents WHERE id=?",(cur.lastrowid,)).fetchone());c.close();return jsonify(incident=item,narrative=f"AttackWeave correlated {len(timeline)} signals into one evidence-backed attack chain. The likely next target is DC-01 (87% confidence)."),201
@app.post("/api/auth/register")
def register():
    x=request.get_json() or {};name=x.get("name","").strip();email=x.get("email","").strip().lower();password=x.get("password","")
    if len(name)<2 or "@" not in email or len(password)<6:return jsonify(error="Enter a name, valid email, and password of at least 6 characters."),400
    try:c=db();cur=c.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",(name,email,hash_password(password)));c.commit();uid=cur.lastrowid;c.close()
    except sqlite3.IntegrityError:return jsonify(error="An account with this email already exists."),409
    user={"id":uid,"name":name,"email":email};return jsonify(token=signer.dumps(user),user=user)
@app.post("/api/auth/login")
def login():
    x=request.get_json() or {};c=db();row=c.execute("SELECT * FROM users WHERE email=? AND password=?",(x.get("email","").lower(),hash_password(x.get("password","")))).fetchone();c.close()
    if not row:return jsonify(error="Incorrect email or password."),401
    user={"id":row["id"],"name":row["name"],"email":row["email"]};return jsonify(token=signer.dumps(user),user=user)
@app.get("/api/session")
def session():return jsonify(user=auth())
@app.get("/api/incidents")
def incidents():
    u=auth()
    if not u:return jsonify(error="Please sign in to continue."),401
    c=db();rows=[pack(r) for r in c.execute("SELECT * FROM incidents WHERE user_id=? ORDER BY id DESC",(u["id"],))];c.close();return jsonify(incidents=rows)
@app.post("/api/incidents/demo")
def demo():
    u=auth()
    if not u:return jsonify(error="Please sign in to continue."),401
    return create(u,"Credential-to-domain escalation",TIMELINE)
@app.post("/api/incidents/upload")
def upload():
    u=auth();x=request.get_json() or {}
    if not u:return jsonify(error="Please sign in to continue."),401
    logs=x.get("logs",[])
    if not isinstance(logs,list) or not logs:return jsonify(error="Upload a JSON array with at least one event."),400
    events=[]
    for i,l in enumerate(logs[:20]):
        text=json.dumps(l).lower();mitre="T1078"
        if "dns" in text:mitre="T1071.004"
        elif "powershell" in text or "process" in text:mitre="T1059.001"
        elif "smb" in text or "remote" in text:mitre="T1021"
        events.append({"time":l.get("time",f"09:{12+i:02}"),"event":l.get("event",l.get("message","Security event")),"detail":l.get("detail",str(l)[:150]),"mitre":mitre})
    return create(u,x.get("title","Uploaded telemetry investigation")[:80],events)
@app.post("/api/incidents/<int:id>/contain")
def contain(id):return jsonify(status="Contained",action="LAPTOP-07 isolated and service credentials marked for reset.")
