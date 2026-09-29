"""CyberTrace AI Phase 1 API."""
import csv, io, json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from .core.database import SessionLocal, TelemetryBatch, TelemetryEvent, Host, Incident, Relationship, AttackTechnique, init_db
from .schemas.telemetry import AnalysisRequest, TelemetryUpload
from .telemetry.service import normalize
from .correlation.engine import relationships
from .mitre.registry import TECHNIQUES

app=FastAPI(title="CyberTrace AI",description="Multi-Stage Attack Reconstruction & Lateral Movement Prediction Platform",version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.on_event("startup")
def startup():
    init_db()
    with SessionLocal() as db:
        for tid,item in TECHNIQUES.items():
            if not db.scalar(select(AttackTechnique).where(AttackTechnique.technique_id==tid)): db.add(AttackTechnique(technique_id=tid,**item))
        db.commit()
@app.get("/api/health")
def health(): return {"status":"ok","service":"CyberTrace AI"}
def ingest(payload:TelemetryUpload):
    normalized=[normalize(event,i) for i,event in enumerate(payload.events)]
    with SessionLocal() as db:
        batch=TelemetryBatch(filename=payload.filename,source_type=payload.source_type,event_count=len(normalized));db.add(batch);db.flush()
        hosts={e.host for e in normalized if e.host}|{e.source_host for e in normalized if e.source_host}|{e.destination_host for e in normalized if e.destination_host}
        for hostname in sorted(hosts):
            if hostname and not db.scalar(select(Host).where(Host.hostname==hostname)): db.add(Host(hostname=hostname,asset_type="server" if "SERVER" in hostname or "DB" in hostname else "endpoint",criticality=85 if "DB" in hostname else 50))
        for e in normalized: db.add(TelemetryEvent(event_id=e.event_id,timestamp=e.timestamp,event_type=e.event_type,host=e.host,source_host=e.source_host,destination_host=e.destination_host,username=e.username,source_ip=e.source_ip,destination_ip=e.destination_ip,action=e.action,severity=e.severity,raw_data=e.raw_data,batch_id=batch.id))
        for rel in relationships(normalized): db.add(Relationship(**rel))
        db.commit();return batch.id,len(normalized),len(hosts)
@app.post("/api/telemetry/upload")
def upload(payload:TelemetryUpload):
    batch_id,count,_=ingest(payload);return {"batch_id":batch_id,"events_received":len(payload.events),"events_normalized":count,"status":"ready_for_analysis"}
@app.post("/api/telemetry/upload-csv")
async def upload_csv(request:Request):
    rows=list(csv.DictReader(io.StringIO((await request.body()).decode("utf-8"))));return upload(TelemetryUpload(events=rows,filename="upload.csv",source_type="csv"))
@app.post("/api/telemetry/demo")
def demo():
    path=Path(__file__).resolve().parents[2]/"data"/"demo"/"cybertrace_scenario.json";return upload(TelemetryUpload(events=json.loads(path.read_text(encoding="utf-8")),filename=path.name,source_type="demo"))
@app.get("/api/telemetry")
def telemetry(page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=500)):
    with SessionLocal() as db:
        rows=db.scalars(select(TelemetryEvent).order_by(TelemetryEvent.timestamp).offset((page-1)*page_size).limit(page_size)).all();return {"page":page,"page_size":page_size,"events":[{"event_id":x.event_id,"timestamp":x.timestamp,"event_type":x.event_type,"host":x.host,"source_host":x.source_host,"destination_host":x.destination_host,"action":x.action,"severity":x.severity,"raw_data":x.raw_data} for x in rows]}
@app.post("/api/analysis/run")
def run_analysis(payload:AnalysisRequest):
    with SessionLocal() as db:
        batch=db.get(TelemetryBatch,payload.batch_id)
        if not batch: raise HTTPException(404,"Telemetry batch not found")
        events=list(batch.events);hosts={e.host for e in events if e.host}|{e.source_host for e in events if e.source_host}|{e.destination_host for e in events if e.destination_host};root=next((e.host for e in sorted(events,key=lambda x:x.timestamp) if e.event_type in {"dns","process"}),None);incident=Incident(title="Phase 1 correlated telemetry analysis",severity="high" if len(events)>3 else "medium",status="analysis_started",confidence=min(0.95,0.5+len(events)*0.03),root_cause_host=root,batch_id=batch.id);db.add(incident);db.commit();return {"incident_id":incident.id,"events_processed":len(events),"hosts_detected":len(hosts),"status":"analysis_started"}
def host_payload(h): return {"id":h.id,"hostname":h.hostname,"ip_address":h.ip_address,"asset_type":h.asset_type,"criticality":h.criticality,"status":h.status,"risk_score":h.risk_score}
@app.get("/api/hosts")
def hosts():
    with SessionLocal() as db:return {"hosts":[host_payload(h) for h in db.scalars(select(Host)).all()]}
@app.get("/api/hosts/{host_id}")
def host(host_id:int):
    with SessionLocal() as db:
        h=db.get(Host,host_id)
        if not h: raise HTTPException(404,"Host not found")
        return host_payload(h)
def incident_payload(i): return {"id":i.id,"title":i.title,"severity":i.severity,"status":i.status,"confidence":i.confidence,"root_cause_host":i.root_cause_host,"batch_id":i.batch_id}
@app.get("/api/incidents")
def incidents():
    with SessionLocal() as db:return {"incidents":[incident_payload(i) for i in db.scalars(select(Incident).order_by(Incident.id.desc())).all()]}
@app.get("/api/incidents/{incident_id}")
def incident(incident_id:int):
    with SessionLocal() as db:
        i=db.get(Incident,incident_id)
        if not i: raise HTTPException(404,"Incident not found")
        return incident_payload(i)
@app.get("/api/mitre/techniques")
def mitre(): return {"techniques":[{"technique_id":k,**v} for k,v in TECHNIQUES.items()]}
def not_ready(feature): raise HTTPException(501,f"{feature} is reserved for Phase 2; no fake data is returned.")
@app.get("/api/incidents/{incident_id}/graph")
def graph(incident_id:int): return not_ready("Incident graph analysis")
@app.get("/api/incidents/{incident_id}/timeline")
def timeline(incident_id:int): return not_ready("Incident timeline analysis")
@app.get("/api/incidents/{incident_id}/predictions")
def predictions(incident_id:int): return not_ready("Next-target prediction")
