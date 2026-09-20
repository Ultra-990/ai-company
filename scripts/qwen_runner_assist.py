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
elif sys.argv[1:]==['--studio-interaction-review']:
    from scripts.compare_local_models import check_idle
    check_idle()
    prompt='''Review an interaction fix for a synthetic web studio. Reply JSON with
risks and test_cases, at most 4 concise strings each. Advisory only: do not execute
anything, claim tests passed or request tools. Existing scene uses native page
scroll for CSS3D spring motion; chapter buttons and blank scene background undo
chapter history. Section links keep separate scroll history. A modal preview
animates from the card and supports wheel zoom. Problem: separate histories and
click handlers can disagree; wheel during opening/switching is currently discarded.
Proposed: one navigation coordinator, section/chapter transitions in one ordered
history; local scene fallback Back for wheel-only movement; same Back button and
blank-click policy. Guard selection/drag and controls. Modal closes before scene
navigation and restores original opener/scroll; wheel during animation queues
zoom until open, no page scroll leak. All native page wheel and browser pinch
remain intact; explicit pause is retained; reduced motion and mobile have readable
fallback. Suggest concrete combined flow regressions and ordering risks, not a
new framework. No actual video element or player exists in this prototype.'''
elif sys.argv[1:]==['--studio-bundle-review']:
    from scripts.compare_local_models import check_idle
    check_idle()
    prompt='''Review this bounded packaging plan. Return JSON with risks and tests,
at most four short strings each. Advisory only; no execution or claims of tests.
Synthetic FORMA has a verified Python stdlib backend, HTML/CSS/JS and three local
PNG images. Today gallery/tools are injected only in preview, missing from ZIP.
Assemble a new immutable candidate ZIP with complete HTML, original business logic,
trusted static-route server, all interaction scripts, PNG files and checksums.
Never overwrite baseline or mark accepted/deployed. No client data or credentials.
Read bounded allowlisted archive entries in memory, no arbitrary ZIP extraction.
Run exact archive bytes only inside existing nonroot network-none readonly Docker
profile, same CPU/RAM/PID limits. Check all public assets against byte hashes,
private source routes denied, independent business assertions unchanged. Browser
gets HTML and scripts from this archive, images as data URLs in opaque CSP frame;
backend requests execute exact bundle sources in the restricted runner. Check
archive corruption, missing assets, stale reports, and focus regression. No new
model training, dependencies, GPU image generation or desktop automation.'''
elif sys.argv[1:]==['--media-delivery-review']:
    from scripts.compare_local_models import check_idle
    check_idle()
    prompt='''Review a bounded source+PNG delivery integration. Return JSON with
risks and tests, at most four short strings each. Advisory only: no code or claims
of execution. A separate immutable schema stores Python stdlib multifile sources
and 1-12 PNG (4MB each, 12MB total, dimensions <=4096), canonical base64 transport,
decoded-byte hashes. Old text schema and limits unchanged. Duplicate import same
task+content returns same package. Owner-only import UI reads a local selected JSON;
logout must cancel pending read before network send. No ZIP extraction on server.
Trusted pinned harness in readonly nonroot network-none Docker verifies isolation,
package unittest, hashes and MIME of all public assets, and denial of private paths.
Package tests are not independent business acceptance. Synthetic pilot adds
unchanged independent assertions. Opaque CSP iframe gets verified PNG as data URLs.
Passed test permits candidate ZIP; final ZIP requires explicit owner review bound
to source+PNG checksum, latest test, task scope and runner config. Tampered evidence,
new test or revoked review blocks old release. New image means new version/review.
No task completion, client send, deployment, auto repair, remote images or OS focus
control. Which concrete integration gaps deserve tests? Keep under 220 words.'''
options=configuration()|{'format':'json'}
if sys.argv[1:] in (['--studio-interaction-review'], ['--studio-bundle-review'], ['--media-delivery-review']):
    options=options|{'num_predict':800,'num_thread':4,'timeout_seconds':90}
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
