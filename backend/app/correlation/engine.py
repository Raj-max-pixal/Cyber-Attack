from ..schemas.telemetry import NormalizedEvent
def relationships(events:list[NormalizedEvent]):
    return [{"source_type":"host","source_id":e.source_host,"target_type":"host","target_id":e.destination_host,"relationship_type":"remote_authentication" if e.event_type=="authentication" else "network_connection","timestamp":e.timestamp,"confidence":0.82} for e in events if e.source_host and e.destination_host]
