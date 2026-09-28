"""AttackWeave: zero-dependency demo backend for BYTEATHON 2026."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import hashlib, hmac, json, os, secrets, sqlite3, time

ROOT = Path(__file__).parent
DB = ROOT / "data" / "attackweave.db"
SESSIONS = {}

def conn():
    db = sqlite3.connect(DB); db.row_factory = sqlite3.Row; return db

def init_db():
    db = conn()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, title TEXT NOT NULL, severity TEXT NOT NULL, risk INTEGER NOT NULL, confidence INTEGER NOT NULL, status TEXT DEFAULT 'Investigating', timeline TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id));
    """)
    db.commit(); db.close()

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180000).hex()
    return f"{salt}${digest}"

def password_ok(password, stored):
    salt, digest = stored.split("$", 1)
    return hmac.compare_digest(password_hash(password, salt).split("$", 1)[1], digest)

DEFAULT_TIMELINE = [
    {"time":"09:12","event":"Unusual sign-in accepted","detail":"Finance user authenticated through an unfamiliar VPN exit node.","mitre":"T1078","stage":"Initial Access"},
    {"time":"09:14","event":"Malicious DNS beacon","detail":"LAPTOP-07 resolved update-check[.]cloud for the first time.","mitre":"T1071.004","stage":"Command & Control"},
    {"time":"09:17","event":"Encoded PowerShell launched","detail":"An obfuscated command ran from a newly-created user context.","mitre":"T1059.001","stage":"Execution"},
    {"time":"09:21","event":"Lateral movement to FILE-02","detail":"An uncommon ADMIN$ share route was opened from LAPTOP-07.","mitre":"T1021.002","stage":"Lateral Movement"},
    {"time":"09:25","event":"Domain ticket at risk","detail":"JUMP-01 requested a service ticket with abnormal source context.","mitre":"T1550.003","stage":"Credential Access"}
]

def incident_payload(row):
    item = dict(row); item["timeline"] = json.loads(item["timeline"]); return item

class App(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT / "static"), **kwargs)
    def json(self, status, payload):
        body=json.dumps(payload).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def body(self):
        try: return json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))).decode() or "{}")
        except json.JSONDecodeError: return {}
    def user(self):
        token=self.headers.get("Authorization","").removeprefix("Bearer "); return SESSIONS.get(token)
    def require_user(self):
        user=self.user()
        if not user: self.json(401,{"error":"Please sign in to continue."}); return None
        return user
    def do_GET(self):
        if self.path == "/api/session":
            user=self.user(); return self.json(200,{"user":user} if user else {"user":None})
        if self.path == "/api/incidents":
            user=self.require_user()
            if not user:return
            db=conn(); rows=db.execute("SELECT * FROM incidents WHERE user_id=? ORDER BY id DESC",(user["id"],)).fetchall(); db.close()
            return self.json(200,{"incidents":[incident_payload(x) for x in rows]})
        return super().do_GET()
    def do_POST(self):
        data=self.body()
        if self.path == "/api/auth/register":
            name=data.get("name","").strip(); email=data.get("email","").strip().lower(); password=data.get("password","")
            if len(name)<2 or "@" not in email or len(password)<6:return self.json(400,{"error":"Enter a name, valid email, and password of at least 6 characters."})
            try:
                db=conn(); cur=db.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",(name,email,password_hash(password))); db.commit(); uid=cur.lastrowid; db.close()
            except sqlite3.IntegrityError:return self.json(409,{"error":"An account with this email already exists."})
            return self.start_session(uid,name,email)
        if self.path == "/api/auth/login":
            db=conn(); row=db.execute("SELECT * FROM users WHERE email=?",(data.get("email","").strip().lower(),)).fetchone(); db.close()
            if not row or not password_ok(data.get("password",""),row["password_hash"]):return self.json(401,{"error":"Incorrect email or password."})
            return self.start_session(row["id"],row["name"],row["email"])
        if self.path == "/api/auth/logout":
            SESSIONS.pop(self.headers.get("Authorization","").removeprefix("Bearer "),None); return self.json(200,{"ok":True})
        user=self.require_user()
        if not user:return
        if self.path == "/api/incidents/demo":
            return self.create_incident(user, "Credential-to-domain escalation", DEFAULT_TIMELINE)
        if self.path == "/api/incidents/upload":
            logs=data.get("logs",[])
            if not isinstance(logs,list) or not logs:return self.json(400,{"error":"Upload a JSON array with at least one event."})
            timeline=[]
            for i,log in enumerate(logs[:20]):
                text=json.dumps(log).lower(); stage="Observed"; mitre="T1078"
                if "dns" in text: stage,mitre="Command & Control","T1071.004"
                if "powershell" in text or "process" in text: stage,mitre="Execution","T1059.001"
                if "smb" in text or "remote" in text: stage,mitre="Lateral Movement","T1021"
                timeline.append({"time":log.get("time",f"09:{12+i:02}"),"event":log.get("event",log.get("message","Security event")),"detail":log.get("detail",str(log)[:150]),"mitre":mitre,"stage":stage})
            return self.create_incident(user, data.get("title","Uploaded telemetry investigation")[:80], timeline)
        if self.path.endswith("/contain"):
            incident_id=int(self.path.split("/")[3]); db=conn(); db.execute("UPDATE incidents SET status='Contained' WHERE id=? AND user_id=?",(incident_id,user["id"])); db.commit(); db.close(); return self.json(200,{"status":"Contained","action":"LAPTOP-07 isolated and service credentials marked for reset."})
        self.json(404,{"error":"Unknown endpoint"})
    def start_session(self, uid, name, email):
        token=secrets.token_urlsafe(32); user={"id":uid,"name":name,"email":email}; SESSIONS[token]=user; self.json(200,{"token":token,"user":user})
    def create_incident(self,user,title,timeline):
        risk=min(98,60+len(timeline)*7); confidence=min(97,72+len(timeline)*5)
        db=conn(); cur=db.execute("INSERT INTO incidents(user_id,title,severity,risk,confidence,timeline) VALUES(?,?,?,?,?,?)",(user["id"],title,"Critical" if risk>85 else "High",risk,confidence,json.dumps(timeline))); db.commit(); row=db.execute("SELECT * FROM incidents WHERE id=?",(cur.lastrowid,)).fetchone(); db.close(); self.json(201,{"incident":incident_payload(row),"narrative":f"AttackWeave correlated {len(timeline)} signals into one evidence-backed attack chain. The likely next target is DC-01 (87% confidence)."})

if __name__ == "__main__":
    init_db(); print("AttackWeave running at http://localhost:8000"); ThreadingHTTPServer(("127.0.0.1",8000),App).serve_forever()
