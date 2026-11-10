"""Record only connection status/model IDs; never include credentials or response bodies."""
import datetime as dt,json,sys,urllib.error
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[2];sys.path[:0]=[str(R/'local/python'),str(R/'src')]
from kg_pipeline.io import Qwen
item={'at':dt.datetime.now(dt.timezone.utc).isoformat(),'endpoint':'configured models listing','generation_calls':0}
try:
 c=Qwen(R/'test.py');item.update(ok=True,model=c.model)
except urllib.error.HTTPError as e:item.update(ok=False,http_status=e.code,error_type=type(e).__name__)
except Exception as e:item.update(ok=False,error_type=type(e).__name__)
with (B/'private/preflight_history.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(item,ensure_ascii=False)+'\n')
print(json.dumps(item,ensure_ascii=False));sys.exit(0 if item['ok'] else 2)
