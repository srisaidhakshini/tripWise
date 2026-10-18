import time
from playwright.sync_api import sync_playwright
U="http://localhost:8000"; S="shots/"
def wait_results(p, t=60):
    p.wait_for_function("document.querySelector('#status-line').textContent.includes('found') || document.querySelector('#destination-grid .empty-state')", timeout=t*1000)
    time.sleep(4)
def eager(p):
    p.evaluate("document.querySelectorAll('img').forEach(i=>i.loading='eager')"); time.sleep(3)
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width":1440,"height":900}); p = ctx.new_page()
    p.goto(U); p.click("[data-view=trip]"); time.sleep(1.5); p.screenshot(path=S+"01_trip_empty.png")
    p.click("[data-view=explore]"); wait_results(p); eager(p); p.evaluate("scrollTo(0,0)"); p.screenshot(path=S+"02_explore_home.png")
    p.evaluate("document.querySelector('#results-title').scrollIntoView()"); eager(p); p.screenshot(path=S+"03_explore_results.png")
    p.select_option("#sort-filter","name"); wait_results(p); eager(p); p.evaluate("document.querySelector('#results-title').scrollIntoView()"); p.screenshot(path=S+"04_filter_sort_az.png")
    p.select_option("#sort-filter","distance")
    wait_results(p)
    p.fill("#search-input","Paris"); p.click("#search-button"); time.sleep(3); wait_results(p); eager(p)
    p.select_option("#radius-filter","15000"); wait_results(p); eager(p)
    p.evaluate("document.querySelector('#results-title').scrollIntoView()"); p.screenshot(path=S+"05_search_paris_15km.png")
    # photo card details
    p.evaluate("document.querySelector('.card-art.has-photo').closest('.destination-card').querySelector('[data-details]').click()")
    time.sleep(6); p.screenshot(path=S+"06_destination_details.png")
    p.click("#detail-add"); time.sleep(1.5); p.screenshot(path=S+"07_details_saved.png"); p.click("#dialog-close")
    # save 3 more with photos
    p.evaluate("document.querySelectorAll('.destination-card:has(.has-photo) [data-save]').forEach((b,i)=>{if(i>0&&i<4)b.click()})"); time.sleep(3)
    p.click("[data-view=trip]"); time.sleep(2); eager(p); p.screenshot(path=S+"08_trip_populated.png")
    # no results empty state
    p.click("[data-view=explore]"); p.fill("#search-input","zzqxjv"); p.click("#search-button"); time.sleep(12); p.evaluate("document.querySelector('#results-title').scrollIntoView()"); p.screenshot(path=S+"09_empty_state.png")
    # mobile
    m = b.new_context(viewport={"width":390,"height":844}, device_scale_factor=2, is_mobile=True, has_touch=True, storage_state=ctx.storage_state()); q = m.new_page()
    q.goto(U); wait_results(q); eager(q); q.screenshot(path=S+"10_mobile_explore.png")
    q.evaluate("document.querySelector('#results-title').scrollIntoView()"); eager(q); q.screenshot(path=S+"11_mobile_results.png")
    q.evaluate("document.querySelector('.card-art.has-photo').closest('.destination-card').querySelector('[data-details]').click()"); time.sleep(6); q.screenshot(path=S+"12_mobile_details.png"); q.click("#dialog-close")
    q.evaluate("document.querySelector('.mobile-nav [data-view=trip]').click()"); time.sleep(2); eager(q); q.screenshot(path=S+"13_mobile_trip.png")
    b.close()
print("done")
