"""Capture screenshots of the live ClaimIQ app at http://13.206.252.215:8501"""

import time, pathlib
from playwright.sync_api import sync_playwright

BASE_URL = "http://13.206.252.215:8501"
OUT_DIR  = pathlib.Path(__file__).parent.parent / "data" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORT = {"width": 1280, "height": 800}

def wait_streamlit(page, secs=3):
    time.sleep(secs)

def save(page, name, scroll_y=0):
    if scroll_y:
        page.evaluate(f"window.scrollTo(0, {scroll_y})")
        time.sleep(0.8)
    path = str(OUT_DIR / f"{name}.png")
    page.screenshot(path=path, full_page=False)
    size = pathlib.Path(path).stat().st_size // 1024
    print(f"  OK {name}.png  ({size} KB)")
    return path

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport=VIEWPORT)
    page = ctx.new_page()

    # ── 1. Home page ─────────────────────────────────────────────────────
    print("1. Home page (Process New Claim tab)...")
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    wait_streamlit(page, 5)
    save(page, "01_home")

    # ── 2. Fill reviewer name ─────────────────────────────────────────────
    print("2. Entering reviewer name...")
    try:
        reviewer_input = page.locator("input[placeholder='Dr. Reviewer']").first
        reviewer_input.click()
        reviewer_input.fill("Dr. Smith")
        wait_streamlit(page, 1)
    except Exception as e:
        print(f"   reviewer input: {e}")

    # ── 3. Select a sample claim ──────────────────────────────────────────
    print("3. Selecting sample claim 1 (Complete Valid)...")
    try:
        selectbox = page.locator("div[data-testid='stSelectbox']").first
        selectbox.click()
        wait_streamlit(page, 1)
        # Pick first real option (not "-- select a sample --")
        options = page.locator("li[role='option']")
        count = options.count()
        print(f"   Found {count} options")
        if count > 1:
            options.nth(1).click()
        elif count == 1:
            options.first.click()
        wait_streamlit(page, 1)
    except Exception as e:
        print(f"   selectbox: {e}")

    save(page, "02_sample_selected")

    # ── 4. Click Process Claim ────────────────────────────────────────────
    print("4. Clicking Process Claim...")
    try:
        btn = page.locator("button:has-text('Process Claim')").first
        btn.scroll_into_view_if_needed()
        btn.click()
        print("   Waiting for AI pipeline (~15s)...")
        wait_streamlit(page, 18)
    except Exception as e:
        print(f"   process button: {e}")
        wait_streamlit(page, 5)

    save(page, "03_pipeline_complete", scroll_y=0)

    # ── 5. Extracted fields ───────────────────────────────────────────────
    print("5. Extracted fields section...")
    save(page, "04_extracted_fields", scroll_y=350)

    # ── 6. Validation results ─────────────────────────────────────────────
    print("6. Validation results...")
    save(page, "05_validation_results", scroll_y=700)

    # ── 7. AI Recommendation ──────────────────────────────────────────────
    print("7. AI recommendation card...")
    save(page, "06_ai_recommendation", scroll_y=1100)

    # ── 8. Human Approval ─────────────────────────────────────────────────
    print("8. Human approval form...")
    save(page, "07_human_approval", scroll_y=1600)

    # ── 9. Claims History tab ─────────────────────────────────────────────
    print("9. Claims History tab...")
    try:
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(0.5)
        history_tab = page.locator("button[data-baseweb='tab']", has_text="Claims History").first
        history_tab.click()
        wait_streamlit(page, 3)
    except Exception as e:
        print(f"   claims history tab: {e}")
    save(page, "08_claims_history")

    # ── 10. About tab ─────────────────────────────────────────────────────
    print("10. About tab...")
    try:
        about_tab = page.locator("button[data-baseweb='tab']", has_text="About").first
        about_tab.click()
        wait_streamlit(page, 2)
    except Exception as e:
        print(f"   about tab: {e}")
    save(page, "09_about")

    browser.close()

print(f"\nOK All screenshots saved to: {OUT_DIR}")
for s in sorted(OUT_DIR.glob("*.png")):
    print(f"  {s.name}  ({s.stat().st_size // 1024} KB)")
