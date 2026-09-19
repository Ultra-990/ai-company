"""Short read-only UI smoke test using a private headless Chrome profile.

No owner/client token, mutating API request, GPU, model or tenant process is used.
Only the Chrome process created here is terminated on exit.
"""
import argparse
import asyncio
import base64
import json
from pathlib import Path
import subprocess
import tempfile

import websockets


async def check(output: Path):
    with tempfile.TemporaryDirectory(prefix="ai-company-chrome-") as profile:
        process = subprocess.Popen([
            "/usr/bin/google-chrome", "--headless", "--disable-gpu", "--disable-extensions",
            "--disable-background-networking", "--no-first-run", "--no-default-browser-check",
            "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            port_file = Path(profile) / "DevToolsActivePort"
            for _ in range(100):
                if port_file.exists(): break
                await asyncio.sleep(.1)
            port, path = port_file.read_text().splitlines()[:2]
            async with websockets.connect(f"ws://127.0.0.1:{port}{path}", max_size=8*1024*1024) as ws:
                serial = 0
                async def call(method, params=None, session=None):
                    nonlocal serial
                    serial += 1; message = {"id": serial, "method":method, "params":params or {}}
                    if session: message["sessionId"] = session
                    await ws.send(json.dumps(message))
                    while True:
                        reply = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                        if reply.get("id") == serial:
                            if "error" in reply: raise RuntimeError(reply["error"])
                            return reply.get("result", {})
                target = await call("Target.createTarget", {"url":"about:blank"})
                session = (await call("Target.attachToTarget", {"targetId":target["targetId"], "flatten":True}))["sessionId"]
                async def evaluate(expression):
                    result = await call("Runtime.evaluate", {"expression":expression, "returnByValue":True, "awaitPromise":True}, session)
                    if "exceptionDetails" in result: raise RuntimeError(result["exceptionDetails"])
                    return result["result"].get("value")
                async def wait_for(expression):
                    for _ in range(50):
                        if await evaluate(expression): return
                        await asyncio.sleep(.1)
                    raise AssertionError(expression)
                async def screenshot(name):
                    result = await call("Page.captureScreenshot", {"format":"png"}, session)
                    (output/name).write_bytes(base64.b64decode(result["data"]))
                await call("Emulation.setDeviceMetricsOverride", {"width":1440,"height":1100,"deviceScaleFactor":1,"mobile":False}, session)
                await call("Page.navigate", {"url":"http://127.0.0.1:8000/os/legacy"}, session)
                await wait_for("document.querySelectorAll('.os-window').length === 12")
                await evaluate("if(document.documentElement.dataset.theme!=='dark') document.querySelector('[data-theme-toggle]').click()")
                await screenshot("os-dark.png")
                count = await evaluate("document.querySelectorAll('#network-lines line').length")
                assert 13 <= count <= 30, count
                await evaluate("window.testWindow=document.querySelector('.os-window'); window.testLine=document.querySelector('#network-lines line'); document.dispatchEvent(new Event('organization-data-changed'))")
                await asyncio.sleep(.3)
                assert await evaluate("window.testWindow===document.querySelector('.os-window') && window.testLine===document.querySelector('#network-lines line')")
                point = await evaluate("(()=>{const r=document.querySelector('.window-bar').getBoundingClientRect();return {x:r.x+25,y:r.y+20}})()")
                await call("Input.dispatchMouseEvent", {"type":"mousePressed", "x":point["x"],"y":point["y"],"button":"left","clickCount":1}, session)
                scheduled = await evaluate("""(()=>{
                  window.originalRAF=window.requestAnimationFrame; let count=0;
                  window.requestAnimationFrame=(fn)=>{count++;return originalRAF(fn)};
                  const bar=document.querySelector('.window-bar');
                  for(let i=0;i<20;i++) bar.dispatchEvent(new PointerEvent('pointermove', {pointerId:1,clientX:180+i,clientY:460+i,bubbles:true}));
                  window.requestAnimationFrame=window.originalRAF; return count;
                })()""")
                assert scheduled <= 1, scheduled
                await call("Input.dispatchMouseEvent", {"type":"mouseReleased", "x":200,"y":480,"button":"left","clickCount":1}, session)
                await asyncio.sleep(.1)
                assert await evaluate("document.querySelector('.os-window').style.left.endsWith('px')")
                assert await evaluate("window.testLine===document.querySelector('#network-lines line')")
                await evaluate("window.savedHome=document.querySelector('.os-window').style.left; document.querySelector('.window-open').click()")
                assert await evaluate("document.querySelector('.os-window').classList.contains('is-open')")
                await screenshot("os-active-window.png")
                await evaluate("document.querySelectorAll('.window-open')[1].click()")
                assert await evaluate("!document.querySelector('.os-window').classList.contains('is-open') && document.querySelector('.os-window').style.left===window.savedHome")
                await evaluate("document.querySelector('#owner-orb').click()")
                assert await evaluate("document.querySelector('#owner-menu').open")
                assert await evaluate("(()=>{const el=document.querySelector('#owner-menu-title'),r=el.getBoundingClientRect();return !!document.elementFromPoint(r.x+10,r.y+10).closest('#owner-menu')})()")
                await screenshot("os-owner-menu.png")
                await evaluate("document.querySelector('#open-delivery-center').click()")
                assert await evaluate("document.querySelector('#delivery-center').open && !document.querySelector('#owner-menu').open")
                await evaluate("document.querySelector('#delivery-center').close(); if(document.documentElement.dataset.theme!=='light') document.querySelector('[data-theme-toggle]').click()")
                await evaluate("document.querySelector('#owner-orb').click(); document.querySelector('#open-client-publishing').click()")
                assert await evaluate("document.querySelector('#client-publishing').open && !document.querySelector('#owner-menu').open")
                await evaluate("document.querySelector('#publishing-token').value='smoke-test-not-a-real-token'; document.querySelector('#client-publishing').close()")
                await wait_for("document.querySelector('#publishing-token').value===''")
                await evaluate("document.querySelector('#restore-layout').click()")
                await screenshot("os-light.png")
                await evaluate("document.querySelector('[data-theme-toggle]').click()")
                assert await evaluate("document.documentElement.dataset.theme==='dark'")
                await call("Emulation.setDeviceMetricsOverride", {"width":390,"height":844,"deviceScaleFactor":1,"mobile":True}, session)
                await asyncio.sleep(.1)
                assert await evaluate("document.documentElement.scrollWidth <= 390")
                await screenshot("os-mobile.png")
                await call("Page.navigate", {"url":"http://127.0.0.1:8000/client"}, session)
                await wait_for("!!document.querySelector('#client-login')")
                assert await evaluate("document.querySelector('#client-project').hidden")
                await screenshot("client-mobile.png")
                # Mock only the client read endpoint IN THIS isolated browser target;
                # no access token is created and no production record is changed.
                await evaluate("""window.fetch=async()=>new Response(JSON.stringify({
                  project:{title:'Projekt demonstracyjny — test UI', summary:'Przykładowy widok, nie dane klienta.',progress:40,status:'in_progress',next_step:'Odbiór makiety',milestones:[{title:'<script>window.testXSS=true</script>',status:'completed'}]},
                  updated_at:new Date().toISOString(),expires_at:new Date(Date.now()+86400000).toISOString()
                }),{status:200,headers:{'Content-Type':'application/json'}})""")
                await evaluate("document.querySelector('#client-token').value='test-only'; document.querySelector('#client-login').requestSubmit()")
                await wait_for("!document.querySelector('#client-project').hidden")
                assert await evaluate("!window.testXSS && document.querySelector('#client-milestones').textContent.includes('<script>')")
                assert await evaluate("document.documentElement.scrollWidth <= 390")
                await screenshot("client-demo-mobile.png")
                await evaluate("document.querySelector('#client-logout').click()")
                assert await evaluate("document.querySelector('#client-project').hidden && document.querySelector('#client-title').textContent===''")
                print(json.dumps({"windows":12, "unique_connections":count, "persistent_DOM":True,
                                  "owner_menu_above_brain":True,"delivery_dialog":True,
                                  "coalesced_drag_frames":scheduled,"publishing_dialog":True,"inactive_position_restored":True,
                                  "mobile_no_overflow":True,"client_shell":True,"client_snapshot_mock":True,
                                  "screenshots":str(output)}))
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    asyncio.run(check(args.output))
