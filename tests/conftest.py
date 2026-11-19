import os
import pytest
from playwright.sync_api import sync_playwright

import sp


@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as p:
        exe = os.environ.get('OVERHEADS_CHROME', '/usr/bin/google-chrome')
        b = p.chromium.launch(executable_path=exe if os.path.exists(exe) else None, args=['--no-sandbox'])
        yield b
        b.close()


@pytest.fixture
def open_app(browser, tmp_path):
    """open_app(scenes={'id': doc} | 'workshop', device='desktop'|'phone'|'tablet', db=False, current='id', extra_local={})
    Each call gets its own browser context (fresh storage). Returns sp.App."""
    ctxs = []
    html = tmp_path / '_app.html'
    html.write_text(sp.page_html())

    def _open(scenes='workshop', device='desktop', db=False, current=None, extra_local=None, wait=900):
        if scenes == 'workshop':
            scenes = {'workshop': sp.workshop()}
        ctx = browser.new_context(**sp.DEVICES[device])
        ctxs.append(ctx)
        ctx.route('**/jspdf.umd.min.js', lambda r: r.fulfill(path=sp.JSPDF, content_type='application/javascript'))
        ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
        cur = current or next(iter(scenes))
        ctx.add_init_script(sp.STUB + (sp.DBMOCK if db else '') + sp.seed_js(scenes, db, {'shotplans:last': cur, **(extra_local or {})}))
        page = ctx.new_page()
        app = sp.App(page, str(tmp_path))
        page.goto('file://' + str(html))
        page.wait_for_timeout(wait)
        return app

    yield _open
    for c in ctxs:
        c.close()
