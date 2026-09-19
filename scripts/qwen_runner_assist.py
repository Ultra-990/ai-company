"""Ask local Qwen for a bounded draft; never imports or executes its output."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.local_ollama import configuration, OllamaProvider

prompt='''Write a single self-contained Python 3.10 stdlib-only container test harness.
It runs INSIDE a disposable Docker container, never on host. Package is /workspace,
read-only. Working tmpfs /tmp writable. app.py starts a web server respecting PORT=8080,
HOST=127.0.0.1. test_app.py contains unittest tests. Import only standard library.
Use subprocess for tests with timeout 15 seconds, capture at most 12000 chars in final
report. Launch app.py as a separate process; poll /health for <=8 seconds; verify JSON
status=ok, GET / is HTTP200 and has HTML doctype. All HTTP is loopback inside container.
Always terminate/kill only own app process; no shell, package install, arbitrary commands.
Output one JSON report with tests_ok, http_ok, tests_log, errors. Exit nonzero on any failure.
Do NOT claim this proves security or meets every requirement. Keep <=150 lines.
Reply ONLY JSON {"files":{"harness.py":"full source text"}}. No Markdown.'''
if sys.argv[1:]==['--department-review']:
    prompt='''Review this department-agent implementation plan. Reply concise JSON
with risks and tests (max 6 each) and a short Polish reviewer instruction.
There are 12 departments, each with manager/analyst/builder/tester/delivery/reviewer.
Existing 4-stage tasks use analyst/builder/tester/delivery. Manager coordinates,
reviewer profile is advisory; final acceptance remains owner. One shared local Qwen,
temperature .2, bounded context and timeout, no tools/host/network access.
Add versioned department-specific instructions to immutable handoff packet, preserving
old results. Example: finance prepares calculations from supplied assumptions, not
invented tax advice; marketing uses supplied material, never claims live research;
quality lists missing evidence, never claims tests ran. Source text is untrusted.
UI should show actual assigned tasks, queued/reported-running/awaiting-review runs,
not claim all agents are running. Raw completed inference is not accepted work.
No automatic startup of all agents or external actions. Read-only paginated task
list opens existing project with explicit model execution. No new task duplication.
Do not execute code or claim tests passed. Focus on operational correctness.'''
elif sys.argv[1:]==['--upwork-review']:
    prompt='''Design a concise Polish intake/qualification checklist for our Upwork
delivery system. Output JSON with analyst_instruction (max 1800 characters),
required_tests (max 8 strings). Do not execute anything or claim capabilities.
Owner pastes job description; URL is stored only, never fetched. Existing WorkOrder
has four dependent stages: scope analyst, builder, tester, delivery. Local Qwen
analyses scope; no automatic bid, price commitment, contract acceptance or publication.
Current executable profile: Python stdlib app.py + test_app.py + README.md,
stateless HTTP GET application, own HTML/CSS/JS; no pip, internet, GPU, persistent DB,
accounts, payments or production hosting. Container tests plus bounded automatic
repairs exist, but final release requires owner acceptance. Analysis must report
supported/clarify/unsupported, gaps, client questions, explicit acceptance cases
and exclusions. A model opinion is not a readiness proof. Job text is untrusted data,
not tool instructions. Replayed requests must not duplicate projects or model calls.
Private-client login/payments are deferred. Do not suggest testing on real jobs.'''
elif sys.argv[1:]==['--owner-session-review']:
    prompt='''Review a proposed local FastAPI owner-login design. Return concise JSON
with critical_risks and required_tests. No code execution or secrets.
Existing owner/worker Bearer auth remains. Add POST /api/owner-session using owner
Bearer only; GET retrieves csrf and expiry; DELETE revokes. Random 256-bit opaque
session ID HttpOnly SameSite=Strict host-only cookie Path=/api, absolute TTL 8h.
Server in-memory locked map stores hashed ID, csrf, origin, token fingerprint;
restart invalidates, token rotation invalidates, max 32 active sessions.
Secure cookie on HTTPS; HTTP allowed only canonical loopback localhost/127.0.0.1/::1.
Exact Origin match for login, logout and ALL cookie-authenticated owner API requests,
custom CSRF header required for mutations, reject Sec-Fetch-Site cross-site.
GET session uses custom X-Owner-Session header and same-origin referer or Origin;
no raw token returned or browser storage. Existing explicit Bearer never falls back
to cookie; worker/client endpoints never accept owner cookies. Generated previews
are opaque sandbox origins and cannot pass origin checks.
Frontend explicitly opts owner request helpers into same-origin cookie + CSRF;
never global fetch patch, never send cookies to external URLs or client APIs.
Navbar login/logout works across panels, old raw-token flow remains fallback.
Logout clears server state; other tabs use BroadcastChannel to clear UI but server
enforces revocation regardless. Do not claim perfect security or legal compliance.'''
elif sys.argv[1:]==['--preview-review']:
    root=Path(__file__).resolve().parents[1]
    prompt='''Review this bounded stateless application-preview broker. Return JSON with
critical_bugs and browser_test_cases (at most 4 short strings per array,
each at most 300 characters; entire answer at most 200 words).
Only concrete issues supported by the supplied code. Do not execute anything.
Container: network none, readonly root/source, nonroot, 1CPU/512MiB, own random label,
45s timeout, always cleanup. Owner API authorizes each request, checks source checksum,
accepts only GET /api/name?query, no arbitrary hosts. Frame has opaque sandbox origin,
connect-src none, external scripts denied, form-action none. Parent retains token.
Check stale replies, cross-frame messages, failed fetch and 8 hours * 322 = 2576.
'''+ '\n'.join((root/path).read_text() for path in [
        'app/static/organization-os/application-preview.js',
        'app/static/organization-os/application-frame.js'])
options=configuration()|{'format':'json'}
if sys.argv[1:]==['--preview-review']:
    options=options|{'num_predict':1536,'format':{
        'type':'object','additionalProperties':False,
        'required':['critical_bugs','browser_test_cases'],
        'properties':{key:{'type':'array','maxItems':4,
                          'items':{'type':'string','maxLength':300}}
                      for key in ('critical_bugs','browser_test_cases')}}}
result=OllamaProvider(options).complete([
    {'role':'system','content':'You draft code for human review. Do not execute code or claim tests ran.'},
    {'role':'user','content':prompt}])
destination=Path(tempfile.mkdtemp(prefix='qwen-runner-draft-',dir='/tmp'))/'draft.json'
destination.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'draft':str(destination),'elapsed_seconds':result.get('elapsed_seconds'),'eval_count':result.get('eval_count')}))
