"""Installed and offline: the page declares itself an app, and opens with no connection after one visit."""
import json, os, socket, subprocess, sys, time
import pytest
import sp

ROOT = os.path.dirname(sp.APP)


@pytest.fixture(scope='module')
def server():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    p = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1', '--directory', ROOT],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.8)
    yield f'http://127.0.0.1:{port}/'
    p.terminate()


def test_manifest_and_icons(server):
    m = json.load(open(os.path.join(ROOT, 'manifest.webmanifest')))
    assert m['display'] == 'standalone' and m['start_url'] == './'
    for ic in m['icons']:
        assert os.path.exists(os.path.join(ROOT, ic['src'])), ic['src']
    html = open(sp.APP).read()
    assert '<link rel="manifest" href="manifest.webmanifest">' in html and 'apple-mobile-web-app-capable' in html


def test_opens_offline_after_one_visit(browser, server):
    ctx = browser.new_context(**sp.DEVICES['phone'])
    ctx.route('**/jspdf.umd.min.js', lambda r: r.fulfill(path=sp.JSPDF, content_type='application/javascript'))
    ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
    ctx.add_init_script(sp.seed_js({'workshop_doc': json.loads(json.dumps(sp.WS))}, False, {'shotplans:last': 'workshop_doc'}))
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(server)
    page.evaluate("navigator.serviceWorker.ready")
    page.reload()                      # now controlled by the worker
    page.wait_for_timeout(800)
    assert page.evaluate("!!navigator.serviceWorker.controller")
    page.evaluate("()=>{const P=window.__shotplans,sc=P.cur();sc.name='Made online';P.save(0)}")
    page.wait_for_timeout(1500)
    ctx.set_offline(True)
    page.reload()
    page.wait_for_timeout(1200)
    assert page.locator('#sceneBtn').is_visible(), 'the app did not open offline'
    assert page.evaluate("()=>window.__shotplans.cur()&&window.__shotplans.cur().name") == 'Made online'
    assert not errors, errors
    ctx.close()
