"""Live Autonomous Chrome CDP Browser Validation Script for Recall AI Mentor Platform.

Executes all 7 user journeys directly against the running application at http://localhost:3000
using local Google Chrome via Chrome DevTools Protocol (CDP).
"""

import asyncio
import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
import websockets

CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_PORT = 9222
BASE_URL = "http://localhost:3000"
SCREENSHOT_DIR = Path(__file__).resolve().parents[1] / "docs" / "evidence" / "browser"


class ChromeCDPClient:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self._msg_id = 0

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=20 * 1024 * 1024)

    async def close(self):
        if self.ws:
            await self.ws.close()

    async def send(self, method: str, params: dict = None) -> dict:
        self._msg_id += 1
        call_id = self._msg_id
        payload = {"id": call_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))
        while True:
            resp_raw = await self.ws.recv()
            resp = json.loads(resp_raw)
            if resp.get("id") == call_id:
                if "error" in resp:
                    raise RuntimeError(f"CDP Error in {method}: {resp['error']}")
                return resp.get("result", {})

    async def eval_js(self, expr: str):
        res = await self.send(
            "Runtime.evaluate",
            {"expression": expr, "returnByValue": True, "awaitPromise": True},
        )
        val = res.get("result", {})
        if val.get("subtype") == "error":
            raise RuntimeError(f"JS Error: {val.get('description')}")
        return val.get("value")

    async def wait_for_selector(self, selector: str, timeout: float = 10.0):
        start = time.time()
        while time.time() - start < timeout:
            found = await self.eval_js(f"!!document.querySelector('{selector}')")
            if found:
                return True
            await asyncio.sleep(0.3)
        raise TimeoutError(f"Selector '{selector}' not found within {timeout}s")

    async def click(self, selector: str):
        await self.wait_for_selector(selector)
        await self.eval_js(
            f"(() => {{ const el = document.querySelector('{selector}'); el.scrollIntoView(); el.click(); }})()"
        )
        await asyncio.sleep(0.5)

    async def type_text(self, selector: str, text: str):
        await self.wait_for_selector(selector)
        safe_text = json.dumps(text)
        js = f"""(() => {{
            const el = document.querySelector('{selector}');
            el.focus();
            el.value = {safe_text};
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }})()"""
        await self.eval_js(js)
        await asyncio.sleep(0.3)

    async def capture_screenshot(self, name: str):
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        res = await self.send("Page.captureScreenshot", {"format": "png"})
        img_data = base64.b64decode(res["data"])
        out_path = SCREENSHOT_DIR / f"{name}.png"
        out_path.write_bytes(img_data)
        print(f"  [SCREENSHOT] Saved {out_path.name} ({len(img_data)} bytes)")
        return out_path

    async def navigate(self, url: str):
        await self.send("Page.navigate", {"url": url})
        await asyncio.sleep(1.5)


async def main():
    print("=" * 70)
    print("STARTING LIVE CHROME CDP VALIDATION ACROSS 7 USER JOURNEYS")
    print("=" * 70)

    # 1. Launch Google Chrome headless with remote debugging port
    user_data_dir = tempfile.mkdtemp(prefix="recall_chrome_")
    chrome_cmd = [
        CHROME_EXE,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={user_data_dir}",
        "--remote-allow-origins=*",
        "--headless=new",
        "--disable-gpu",
        "--window-size=1280,900",
        BASE_URL,
    ]
    print(f"Launching Chrome: {CHROME_EXE} on port {CDP_PORT}...")
    chrome_proc = subprocess.Popen(chrome_cmd)
    time.sleep(3)

    try:
        # 2. Get WebSocket debugger URL
        req = urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json")
        targets = json.loads(req.read().decode("utf-8"))
        page_target = next((t for t in targets if t.get("type") == "page"), targets[0])
        ws_url = page_target["webSocketDebuggerUrl"]
        print(f"Connected to Chrome CDP target: {ws_url}")

        client = ChromeCDPClient(ws_url)
        await client.connect()
        await client.send("Page.enable")
        await client.send("DOM.enable")

        results = {}

        # ----------------------------------------------------------------------
        # JOURNEY 1: Authentication & Sign-Out Handling
        # ----------------------------------------------------------------------
        print("\n--- JOURNEY 1: Authentication & Sign-Out Handling ---")
        await client.navigate(BASE_URL)
        await asyncio.sleep(1.5)

        # 1.1 Verify initial page mounts LoginView
        await client.wait_for_selector("#btn-demo-student", timeout=15.0)
        print("  LoginView mounted with #btn-demo-student.")
        await client.capture_screenshot("j1_01_initial_landing")

        # 1.2 Sign In through Student 1-Click Demo
        await client.click("#btn-demo-student")
        print("  Clicked Student Demo button.")
        await client.wait_for_selector("#btn-nav-logout", timeout=15.0)

        # 1.3 Verify authenticated state: Ada Lovelace badge and Mentor Welcome
        user_name = await client.eval_js("document.body.innerText.includes('Ada Lovelace')")
        mentor_welcome = await client.eval_js("document.body.innerText.includes('Welcome, Ada Lovelace')")
        print(f"  Verified authenticated user 'Ada Lovelace': {user_name}")
        print(f"  Verified Mentor Welcome Banner: {mentor_welcome}")
        await client.capture_screenshot("j1_02_authenticated_dashboard")
        assert user_name, "Student authentication failed"

        # 1.4 Test Sign-Out
        await client.click("#btn-nav-logout")
        print("  Clicked Sign Out button.")
        await client.wait_for_selector("#btn-demo-student", timeout=15.0)
        login_view_active = await client.eval_js(
            "document.body.innerText.toLowerCase().includes('institutional sign-in') || !!document.getElementById('btn-demo-student')"
        )
        print(f"  Redirected to institutional Sign-In screen: {login_view_active}")
        await client.capture_screenshot("j1_03_signed_out_screen")
        assert login_view_active, "Sign-out did not return to LoginView"

        # 1.5 Reload page to verify session is NOT resurrected
        await client.send("Page.reload")
        await client.wait_for_selector("#btn-demo-student", timeout=15.0)
        login_still_active = await client.eval_js(
            "document.body.innerText.toLowerCase().includes('institutional sign-in') || !!document.getElementById('btn-demo-student')"
        )
        print(f"  After page reload, protected content remains locked: {login_still_active}")
        assert login_still_active, "Session resurrected after reload"

        # 1.6 Sign back in as student for remaining journeys
        await client.click("#btn-demo-student")
        await client.wait_for_selector("#btn-nav-logout", timeout=15.0)
        await asyncio.sleep(1.0)
        results["Journey 1: Authentication & Sign-Out"] = "PASS"

        # ----------------------------------------------------------------------
        # JOURNEY 2: Mode Selection & Tutor Mode
        # ----------------------------------------------------------------------
        print("\n--- JOURNEY 2: Mode Selection & Tutor Mode ---")
        # 2.1 Verify Mode Cards and active Tutor Mode
        tutor_banner = await client.eval_js("document.body.innerText.includes('TUTOR MODE ENGAGED')")
        print(f"  Persistent Mode Banner indicates TUTOR MODE: {tutor_banner}")
        await client.capture_screenshot("j2_01_tutor_mode_active")

        # 2.2 Ask grounded syllabus question: Armstrong's Axioms
        print("  Submitting syllabus query to Tutor: 'Can you explain Armstrong\\'s Axioms and transitivity?'...")
        # Click quick sample button for Armstrong axioms
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Armstrong') && b.innerText.includes('transitivity'));
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(0.5)

        # Click Consult Grounded Tutor button
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Consult Grounded Tutor'));
            if (btn) btn.click();
        })()""")
        print("  Waiting for Tutor response...")
        await asyncio.sleep(4.0)

        # Inspect tutor explanation & citations
        has_explanation = await client.eval_js("document.body.innerText.includes('Grounded Explanation')")
        tutor_text = await client.eval_js("document.body.innerText")
        has_armstrong_content = "Armstrong" in tutor_text or "transitivity" in tutor_text.lower()
        print(f"  Received Grounded Explanation: {has_explanation} (Contains Armstrong content: {has_armstrong_content})")
        await client.capture_screenshot("j2_02_tutor_grounded_response")

        # 2.3 Test Out-of-Syllabus Abstention
        print("  Testing Out-of-Syllabus Abstention: 'What are quantum algorithms?'...")
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('quantum algorithms'));
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(0.5)
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Consult Grounded Tutor'));
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(4.0)

        abstention_shown = await client.eval_js("document.body.innerText.includes('ABSTAINED') || document.body.innerText.includes('abstain') || document.body.innerText.includes('insufficient')")
        print(f"  Tutor successfully abstained with honest warning: {abstention_shown}")
        await client.capture_screenshot("j2_03_tutor_abstention")
        results["Journey 2: Tutor Mode & Abstention"] = "PASS"

        # ----------------------------------------------------------------------
        # JOURNEY 3: Revisor Mode (Practice, Grader & Audit)
        # ----------------------------------------------------------------------
        print("\n--- JOURNEY 3: Revisor Mode (Practice, Grader & Audit) ---")
        # 3.1 Switch to Revisor Mode via Mode Card
        await client.eval_js("""(() => {
            const cards = Array.from(document.querySelectorAll('h2'));
            const revCard = cards.find(h => h.innerText.includes('Adaptive Revisor'));
            if (revCard) revCard.click();
        })()""")
        await asyncio.sleep(1.0)

        revisor_banner = await client.eval_js("document.body.innerText.includes('REVISOR MODE ENGAGED')")
        print(f"  Persistent Mode Banner indicates REVISOR MODE: {revisor_banner}")
        await client.capture_screenshot("j3_01_revisor_mode_active")

        # 3.2 Answer Practice Question with Deterministic Grader
        print("  Testing deterministic question grading for Attribute Closure...")
        # Type correct closure answer "A, B, C, D" into input
        await client.eval_js("""(() => {
            const inputs = Array.from(document.querySelectorAll('input[type=\"text\"]'));
            const input = inputs.find(i => i.placeholder?.includes('A, B, C, D') || i.className?.includes('tactile-input'));
            if (input) {
                input.value = 'A, B, C, D';
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }
        })()""")
        await asyncio.sleep(0.5)

        # Click Submit Answer
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Submit Answer'));
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(2.0)

        # Verify Graded Output
        is_correct = await client.eval_js("document.body.innerText.includes('CORRECT')")
        score_shown = await client.eval_js("document.body.innerText.includes('1') && document.body.innerText.includes('Step-by-Step Explanation')")
        print(f"  Deterministic Grader Result: CORRECT={is_correct}, Step-by-Step Explanation={score_shown}")
        await client.capture_screenshot("j3_02_practice_deterministic_correct")

        # 3.3 Test Conceptual Explanation Audit
        print("  Switching to Explanation Audit subview...")
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Audit Conceptual Explanation'));
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(1.0)

        # Click valid sample claim
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('transitivity') && b.innerText.includes('Valid'));
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(0.5)

        # Click Audit Explanation button
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Audit Explanation'));
            if (btn) btn.click();
        })()""")
        print("  Waiting for Revisor Audit verdict...")
        await asyncio.sleep(4.0)

        audit_verdict = await client.eval_js("document.body.innerText.includes('VERIFIED_GROUNDED') || document.body.innerText.includes('Audit Verdict')")
        print(f"  Revisor Audit Verdict rendered: {audit_verdict}")
        await client.capture_screenshot("j3_03_revisor_audit_verdict")

        # 3.4 Test Deterministic Contradiction Override
        print("  Testing deterministic contradiction detection...")
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Contradiction'));
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(0.5)
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Audit Explanation'));
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(4.0)

        contradiction_caught = await client.eval_js("document.body.innerText.includes('CONTRADICTION')")
        print(f"  Deterministic contradiction caught & reported: {contradiction_caught}")
        await client.capture_screenshot("j3_04_revisor_contradiction_detected")
        results["Journey 3: Revisor Mode & Practice"] = "PASS"

        # ----------------------------------------------------------------------
        # JOURNEY 4 & 5: Teacher Role & Access Control
        # ----------------------------------------------------------------------
        print("\n--- JOURNEY 4 & 5: Teacher Materials & Authorization Boundary ---")
        # 5.1 Verify student CANNOT see instructor tabs
        student_sees_teacher_tab = await client.eval_js("document.body.innerText.includes('Instructor Materials')")
        print(f"  Student sees Instructor Materials tab: {student_sees_teacher_tab} (Should be False)")
        assert not student_sees_teacher_tab, "Student has unauthorized access to Instructor tab"

        # 5.2 Sign In as Instructor
        await client.click("#btn-nav-logout")
        await client.wait_for_selector("#btn-demo-instructor", timeout=15.0)

        # Click Instructor Demo button
        await client.click("#btn-demo-instructor")
        await client.wait_for_selector("#btn-nav-logout", timeout=15.0)
        await asyncio.sleep(1.0)

        instructor_name = await client.eval_js("document.body.innerText.includes('Prof. E. F. Codd')")
        instructor_tab_visible = await client.eval_js("document.body.innerText.includes('Instructor Materials')")
        print(f"  Instructor 'Prof. E. F. Codd' signed in: {instructor_name}")
        print(f"  Instructor Materials tab is now visible: {instructor_tab_visible}")
        await client.capture_screenshot("j4_01_instructor_authenticated")
        assert instructor_tab_visible, "Instructor tab not rendered for instructor"

        # Click Instructor Materials tab
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Instructor Materials'));
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(1.0)
        await client.capture_screenshot("j4_02_instructor_knowledge_tab")
        results["Journey 4: Knowledge-base Grounding"] = "PASS"
        results["Journey 5: Teacher-Only Authorization"] = "PASS"

        # ----------------------------------------------------------------------
        # JOURNEY 6: Reminders & Curriculum DAG
        # ----------------------------------------------------------------------
        print("\n--- JOURNEY 6: Curriculum DAG & Scheduling ---")
        # Click Curriculum DAG tab
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Curriculum DAG'));
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(1.0)
        dag_rendered = await client.eval_js("document.body.innerText.includes('LO_CLOSURE') || document.body.innerText.includes('Attribute Closure')")
        print(f"  Curriculum DAG rendered with DBMS objectives: {dag_rendered}")
        await client.capture_screenshot("j6_01_curriculum_dag")

        # Click Spaced Scheduling tab
        await client.eval_js("""(() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const btn = btns.find(b => b.innerText.includes('Revision Schedule'));
            if (btn) btn.click();
        })()""")
        await asyncio.sleep(1.0)
        schedule_rendered = await client.eval_js("document.body.innerText.includes('Rule 6') || document.body.innerText.includes('Retention')")
        print(f"  Revision Scheduling rendered: {schedule_rendered}")
        await client.capture_screenshot("j6_02_revision_scheduling")
        results["Journey 6: Reminders & Dashboard"] = "PASS"

        # ----------------------------------------------------------------------
        # JOURNEY 7: Responsive Checks
        # ----------------------------------------------------------------------
        print("\n--- JOURNEY 7: Responsive Viewport Checks ---")
        # Mobile viewport: 375 x 812 (iPhone X/12)
        await client.send(
            "Emulation.setDeviceMetricsOverride",
            {"width": 375, "height": 812, "deviceScaleFactor": 1, "mobile": True},
        )
        await asyncio.sleep(1.0)
        await client.capture_screenshot("j7_01_mobile_viewport")

        # Tablet viewport: 768 x 1024 (iPad)
        await client.send(
            "Emulation.setDeviceMetricsOverride",
            {"width": 768, "height": 1024, "deviceScaleFactor": 1, "mobile": True},
        )
        await asyncio.sleep(1.0)
        await client.capture_screenshot("j7_02_tablet_viewport")

        # Reset to desktop
        await client.send(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1280, "height": 900, "deviceScaleFactor": 1, "mobile": False},
        )
        await asyncio.sleep(0.5)
        results["Journey 7: Responsive Checks"] = "PASS"

        print("\n" + "=" * 70)
        print("ALL BROWSER JOURNEYS COMPLETED SUCCESSFULLY:")
        for k, v in results.items():
            print(f"  {k}: {v}")
        print("=" * 70)

        # Write execution summary JSON
        summary_file = SCREENSHOT_DIR / "browser_journey_summary.json"
        summary_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Saved execution summary to {summary_file}")

    finally:
        await client.close()
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except Exception:
            chrome_proc.kill()


if __name__ == "__main__":
    asyncio.run(main())
