"""The page on its own, as GitHub Pages serves it: no host runtime, browser storage, ordinary downloads."""
import json
import sp


def open_plain(browser, scenes=None):
    ctx = browser.new_context(**sp.DEVICES['desktop'], accept_downloads=True)
    ctx.route('**/jspdf.umd.min.js', lambda r: r.fulfill(path=sp.JSPDF, content_type='application/javascript'))
    ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
    if scenes:
        ctx.add_init_script(sp.seed_js(scenes, False, {'shotplans:last': next(iter(scenes))}))
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('file://' + sp.APP)
    page.wait_for_timeout(900)
    return ctx, page, errors


def test_runs_without_the_host(browser):
    ctx, page, errors = open_plain(browser)
    assert page.evaluate('typeof window.claude') == 'undefined'
    assert page.title() == 'Overheads'
    assert page.locator('#sceneBtn').is_visible()
    assert not errors, errors
    ctx.close()


def test_saves_in_the_browser_and_survives_a_reload(browser):
    ctx, page, errors = open_plain(browser, {'workshop_doc': json.loads(json.dumps(sp.WS))})
    page.evaluate("()=>{const P=window.__shotplans,sc=P.cur();sc.name='Renamed here';P.save(0)}")
    page.wait_for_function("()=>(localStorage.getItem('shotplans:workshop_doc')||'').includes('Renamed here')", timeout=5000)
    page.wait_for_timeout(1500)  # Chromium commits localStorage to disk in batches; a reload straight after a write can read the old value
    page.reload()
    page.wait_for_timeout(900)
    assert page.evaluate("()=>window.__shotplans.cur().name") == 'Renamed here'
    assert page.locator('#saveNote').inner_text() == 'This browser only'
    assert not errors, errors
    ctx.close()


def test_pdf_and_csv_download_as_ordinary_files(browser):
    ctx, page, errors = open_plain(browser, {'workshop_doc': json.loads(json.dumps(sp.WS))})
    with page.expect_download() as d:
        page.evaluate("()=>{const P=window.__shotplans;P.exportListCSV(P.cur())}")
    assert open(d.value.path(), encoding='utf-8-sig').read().startswith('Scene,Shot')
    with page.expect_download(timeout=60000) as d:
        page.evaluate("()=>window.__shotplans.exportPDF()")
    assert open(d.value.path(), 'rb').read(5) == b'%PDF-'
    assert not errors, errors
    ctx.close()
