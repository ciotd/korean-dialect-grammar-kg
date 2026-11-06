"""Loopback-only viewer. No model calls, shell commands or arbitrary file serving."""
import json
import secrets
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from .core import Registry, read, STAGES
from .work import WorkStore

DOCUMENTS = {'implementation':'docs/research/PIPELINE_IMPLEMENTATION.md',
             'search_execution':'docs/research/SEARCH_EXECUTION_20261025.md',
             'runtime':'docs/research/RUNTIME_REDESIGN_20261024.md',
             'results':'docs/research/PIPELINE_FIRST50_RESULTS_20261023.md',
             'management':'docs/research/RESEARCH_MANAGEMENT.md',
             'workflow':'docs/workflows/RESEARCH_MANAGEMENT.md',
             'decisions':'docs/research/DECISIONS.md',
             'status':'docs/research/RESEARCH_STATUS.md'}

def make_server(project, port=8766):
    registry=Registry(project);registry.sync();token=secrets.token_urlsafe(32)
    assets=Path(__file__).parent/'web'
    work=WorkStore(project)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # No sentence text or query values in HTTP logs.

        def send(self, value, status=200, mime='application/json; charset=utf-8'):
            body=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode('utf-8')
            self.send_response(status);self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(body)

        def host_ok(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')

        def do_GET(self):
            if not self.host_ok():return self.send({'error':'invalid_host'},403)
            request=urlparse(self.path);query=parse_qs(request.query)
            arg=lambda key:query.get(key,[''])[0]
            try:
                if request.path=='/api/work':return self.send(work.state())
                if request.path=='/api/work/review':return self.send(work.review())
                if request.path.startswith('/reports/integrated-grammar-20261106/'):
                    name=request.path.removeprefix('/reports/integrated-grammar-20261106/')
                    files={'report.html':'text/html','report.css':'text/css','report.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/integrated_grammar_20261106/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path in ('/work','/work.js','/work.css'):
                    name={'/work':'work.html','/work.js':'work.js','/work.css':'work.css'}[request.path]
                    mime={'work.html':'text/html','work.js':'text/javascript','work.css':'text/css'}[name]
                    return self.send((assets/name).read_bytes(),mime=mime+'; charset=utf-8')
                if request.path.startswith('/reports/overnight-20261105/'):
                    name=request.path.removeprefix('/reports/overnight-20261105/')
                    files={'report.html':'text/html','report.css':'text/css','report.js':'text/javascript','paper_handoff.md':'text/plain','codex_review.md':'text/plain','claude_review.md':'text/plain','guide.html':'text/html','guide.css':'text/css','guide.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/overnight_20261105/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/qwen-rerun-20261030/'):
                    name=request.path.removeprefix('/reports/qwen-rerun-20261030/')
                    files={'report.html':'text/html','report.css':'text/css'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/qwen_rerun_20261030/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/claude-comparison-20261030/'):
                    name=request.path.removeprefix('/reports/claude-comparison-20261030/')
                    files={'report.html':'text/html','report.css':'text/css'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/claude_comparison_20261030/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/card-delivery-20261030/'):
                    name=request.path.removeprefix('/reports/card-delivery-20261030/')
                    files={'report.html':'text/html','report.css':'text/css'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/card_delivery_20261030/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/card-revision-20261030/'):
                    name=request.path.removeprefix('/reports/card-revision-20261030/')
                    files={'report.html':'text/html','report.css':'text/css'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/card_revision_20261030/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/card-content-experiment-20261030/'):
                    name=request.path.removeprefix('/reports/card-content-experiment-20261030/')
                    files={'report.html':'text/html','report.css':'text/css','report.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/card_content_experiment_20261030/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/selection-probe-20261102/'):
                    name=request.path.removeprefix('/reports/selection-probe-20261102/')
                    files={'report.html':'text/html','report.css':'text/css','report.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/selection_probe_20261102/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/effect-ledger-20261031/'):
                    name=request.path.removeprefix('/reports/effect-ledger-20261031/')
                    files={'report.html':'text/html','report.css':'text/css','report.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/effect_ledger_20261031/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/controlled-delivery-20261031/'):
                    name=request.path.removeprefix('/reports/controlled-delivery-20261031/')
                    files={'report.html':'text/html','report.css':'text/css','report.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/controlled_delivery_20261031/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/register-connective-20261030/'):
                    name=request.path.removeprefix('/reports/register-connective-20261030/')
                    files={'report.html':'text/html','report.css':'text/css','report.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/register_connective_20261030/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/contract-alignment-20261030/'):
                    name=request.path.removeprefix('/reports/contract-alignment-20261030/')
                    files={'report.html':'text/html','report.css':'text/css','report.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/contract_alignment_20261030/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/bottleneck-audit-20261030/'):
                    name=request.path.removeprefix('/reports/bottleneck-audit-20261030/')
                    files={'report.html':'text/html','report.css':'text/css','report.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/bottleneck_audit_20261030/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/scoped-repair-20261030/'):
                    name=request.path.removeprefix('/reports/scoped-repair-20261030/')
                    files={'report.html':'text/html','report.css':'text/css','report.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/scoped_repair_20261030/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/grammar-cards/'):
                    name=request.path.removeprefix('/reports/grammar-cards/')
                    files={'report.html':'text/html','report.js':'text/javascript','report.css':'text/css',
                           'data.json':'application/json','blind_review.json':'application/json',
                           'review.html':'text/html','review.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/grammar_cards_20261028/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path=='/api/grammar-ratings':
                    from .evaluation import load_ratings
                    return self.send(load_ratings(registry.project))
                if request.path.startswith('/reports/search-execution/'):
                    name=request.path.removeprefix('/reports/search-execution/')
                    files={'report.html':'text/html','report.js':'text/javascript','report.css':'text/css',
                           'data.json':'application/json','blind_review.json':'application/json',
                           'review.html':'text/html','review.js':'text/javascript'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/search_execution_20261025/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path.startswith('/reports/runtime/'):
                    name=request.path.removeprefix('/reports/runtime/')
                    files={'report.html':'text/html','report.js':'text/javascript','report.css':'text/css','comparison.json':'application/json'}
                    if name not in files:return self.send({'error':'not_found'},404)
                    path=registry.project/'experiments/analyses/redesign_20261024/private'/name
                    if not path.is_file():return self.send({'error':'report_not_ready'},404)
                    return self.send(path.read_bytes(),mime=files[name]+'; charset=utf-8')
                if request.path in ('/','/app.js','/style.css'):
                    name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[request.path]
                    mime={'index.html':'text/html','app.js':'text/javascript','style.css':'text/css'}[name]
                    return self.send((assets/name).read_bytes(),mime=mime+'; charset=utf-8')
                if request.path=='/api/info':
                    return self.send({'csrf':token,'stages':STAGES,'documents':DOCUMENTS,'reports':read(registry.project/'experiments/management/report_navigation.json',[])})
                if request.path=='/api/runs':return self.send(registry.runs())
                if request.path=='/api/records':return self.send(registry.records(arg('run')))
                if request.path=='/api/summary':
                    registry.get(arg('run'))
                    return self.send(read(registry.root/'summaries'/f'{arg("run")}.json',{'note':'No completed summary yet.'}))
                if request.path=='/api/trace':return self.send(registry.trace(arg('run'),arg('input'),arg('stage')))
                if request.path=='/api/compare':return self.send(registry.compare(arg('left'),arg('right')))
                if request.path=='/api/document':
                    if arg('name') not in DOCUMENTS:raise KeyError('unknown_document')
                    path=registry.project/DOCUMENTS[arg('name')]
                    return self.send({'title':arg('name'),'path':DOCUMENTS[arg('name')],'text':path.read_text(encoding='utf-8')})
                return self.send({'error':'not_found'},404)
            except (ValueError,KeyError) as exc:
                return self.send({'error':str(exc)},400)
            except Exception as exc:
                return self.send({'error':type(exc).__name__},500)

        def do_POST(self):
            if not self.host_ok() or self.headers.get('X-Research-Token')!=token:
                return self.send({'error':'local_token_required'},403)
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
                return self.send({'error':'invalid_origin'},403)
            if self.path=='/api/work/decisions':
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=200000:return self.send({'error':'payload_size'},400)
                    payload=json.loads(self.rfile.read(length))
                    if not isinstance(payload,dict):raise ValueError('object_required')
                    return self.send(work.decide(payload))
                except (ValueError,KeyError,TypeError) as exc:return self.send({'error':str(exc)},400)
            if self.path=='/api/grammar-ratings':
                try:
                    from .evaluation import save_ratings
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=1000000:return self.send({'error':'payload_size'},400)
                    payload=json.loads(self.rfile.read(length))
                    return self.send(save_ratings(registry.project,payload))
                except (ValueError,KeyError,TypeError) as exc:return self.send({'error':str(exc)},400)
            if self.path!='/api/sync':return self.send({'error':'not_found'},404)
            try:return self.send(registry.sync())
            except Exception as exc:return self.send({'error':type(exc).__name__},500)
    class LocalServer(ThreadingHTTPServer):
        def server_bind(self):
            if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):
                self.allow_reuse_address=False
                self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            super().server_bind()
    return LocalServer(('127.0.0.1',port),Handler)

def serve(project,port=8766):
    server=make_server(project,port)
    print(f'Research dashboard: http://127.0.0.1:{server.server_port}/',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
