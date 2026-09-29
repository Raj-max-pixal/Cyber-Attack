from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field
EventType=Literal["authentication","dns","process","network"]
class NormalizedEvent(BaseModel):
    timestamp:datetime; event_id:str; event_type:EventType; host:str|None=None; source_host:str|None=None; destination_host:str|None=None; username:str|None=None; source_ip:str|None=None; destination_ip:str|None=None; action:str|None=None; severity:str="low"; raw_data:dict[str,Any]=Field(default_factory=dict)
class TelemetryUpload(BaseModel):
    events:list[dict[str,Any]]; filename:str="telemetry.json"; source_type:str="json"
class AnalysisRequest(BaseModel): batch_id:int
