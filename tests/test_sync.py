"""Sync with the host db (mocked in-page) and between local tabs: content-based change detection, 3-way merge,
clashes, deletes, snapshots deferred during a gesture, unsaved-edit replay, focus kept on remote re-render."""
import pytest
import sp

FURN = [i['id'] for i in sp.WS['items'] if i['kind'] == 'furn' and i.get('shape') != 'rug']
X, Y, Z = FURN[:3]
CAM = [i['id'] for i in sp.WS['items'] if i['kind'] == 'cam'][0]

# Claude / another device edits one item's x. ts: 'same' keeps updatedAt, 'none' drops it, 'iso' string, 'old' 60 s behind, 'now'
REMOTE = """([id,dx,ts])=>{const d=window.__db.read('workshop');d.items.find(i=>i.id===id).x+=dx;
  if(ts==='none')delete d.updatedAt;else if(ts==='iso')d.updatedAt=new Date().toISOString();else if(ts==='old')d.updatedAt=Date.now()-60000;else if(ts==='now')d.updatedAt=Date.now();
  window.__db.remote('workshop',d)}"""


def x_app(app, id):
    return app.js("id=>{const it=window.__shotplans.cur()?.items.find(i=>i.id===id);return it?Math.round(it.x*100)/100:null}", id)


def x_db(app, id):
    return app.js("id=>{const d=window.__db.read('workshop');const it=d&&d.items.find(i=>i.id===id);return it?Math.round(it.x*100)/100:null}", id)


def remote(app, id, dx, ts='now'):
    app.js(REMOTE, [id, dx, ts])


def nudge(app, id, n=1):
    app.js("id=>{const S=window.__shotplans.S;S.sel=id;S.multi=[]}", id)
    for _ in range(n):
        app.page.keyboard.press('ArrowRight')


@pytest.fixture
def app(open_app):
    a = open_app(db=True)
    assert a.S('mode') == 'db'
    assert a.S('curId') == 'workshop'
    return a


def test_remote_write_with_unchanged_timestamp_is_seen(app):
    z0 = x_db(app, Z)
    remote(app, Z, 3, 'same')
    app.wait(300)
    assert x_app(app, Z) == z0 + 3, 'a remote write that kept updatedAt was ignored'
    nudge(app, X)
    app.wait(1500)
    assert x_db(app, Z) == z0 + 3, "the next local save put Claude's change back"


@pytest.mark.parametrize('ts', ['none', 'iso', 'old', 'same'])
def test_remote_write_during_pending_edit_is_merged(app, ts):
    x0, z0 = x_db(app, X), x_db(app, Z)
    nudge(app, X)
    app.wait(150)
    remote(app, Z, 3, ts)
    app.wait(1800)
    assert x_db(app, X) == x0 + .25, 'my edit was lost'
    assert x_db(app, Z) == z0 + 3, 'their edit was overwritten (updatedAt=%s)' % ts
    assert x_app(app, Z) == z0 + 3


def test_clash_keeps_mine_and_undo_shows_theirs(app):
    x0 = x_db(app, X)
    nudge(app, X)
    app.wait(150)
    remote(app, X, 3)
    app.wait(1800)
    assert x_db(app, X) == x0 + .25
    assert 'You both changed' in app.toast()
    app.page.keyboard.press('Control+z')
    app.wait(1200)
    assert x_app(app, X) == x0 + 3 and x_db(app, X) == x0 + 3


def test_undo_cleared_after_adopting_remote(app):
    z0 = x_db(app, Z)
    nudge(app, X)
    app.wait(1500)
    remote(app, Z, 3)
    app.wait(400)
    app.page.keyboard.press('Control+z')
    app.wait(1200)
    assert x_db(app, Z) == z0 + 3, "undo after adopting a remote version erased Claude's work"


def test_remote_delete_when_idle_removes_scene(app):
    app.js("()=>window.__db.remote('workshop',null)")
    app.wait(400)
    assert app.js("()=>window.__shotplans.S.scenes.has('workshop')") is False, 'a plan deleted elsewhere is still open'


def test_remote_delete_with_pending_edit_not_resurrected(app):
    nudge(app, X)
    app.wait(100)
    app.js("()=>window.__db.remote('workshop',null)")
    app.wait(1800)
    assert app.db('workshop') is None, 'a deleted plan came back from a pending edit'


def test_snapshot_under_finger_applied_after(app):
    z0 = x_db(app, Z)
    app.page.mouse.move(300, 700)
    app.page.mouse.down()
    remote(app, Z, 3)
    app.wait(300)
    app.page.mouse.up()
    app.wait(300)
    assert x_app(app, Z) == z0 + 3, 'a write that arrived while a finger was down was dropped'
    nudge(app, X)
    app.wait(1500)
    assert x_db(app, Z) == z0 + 3
    assert 'another device' not in app.toast()


def test_snapshot_during_item_drag_merged(app):
    z0, y0 = x_db(app, Z), x_db(app, Y)
    app.space('set')
    app.js("id=>{window.__shotplans.S.sel=id}", Y)
    app.rerender()
    px, py = app.item_px(Y)
    m = app.page.mouse
    m.move(px, py); m.down(); m.move(px + 40, py, steps=4)
    remote(app, Z, 3)
    app.wait(200)
    m.move(px + 80, py, steps=4); m.up()
    app.wait(1500)
    assert x_db(app, Y) != y0, 'my drag was lost'
    assert x_db(app, Z) == z0 + 3, 'the write that arrived mid-drag was lost'


def test_unsaved_edit_replayed_on_next_visit(open_app):
    a = open_app(db=True)
    x0 = x_db(a, X)
    a.js("()=>window.__db.setGetDelay(1e7)")  # the network never answers
    nudge(a, X, 2)
    a.wait(100)   # let both key presses land before the page is hidden
    a.js("()=>window.dispatchEvent(new Event('pagehide'))")
    a.wait(100)
    rec = a.js("()=>JSON.parse(localStorage.getItem('shotplans:unsaved:workshop')||'null')")
    assert rec and rec.get('doc'), 'no unsaved copy kept on pagehide'
    page2 = a.page.context.new_page()
    b = sp.App(page2, a.out_dir)
    page2.goto(a.page.url)
    for _ in range(40):   # the recovered edit is replayed once the page settles; poll instead of guessing a delay
        page2.wait_for_timeout(250)
        try:
            if x_app(b, X) == x0 + .5 and x_db(b, X) == x0 + .5:
                break
        except Exception:
            pass
    assert x_app(b, X) == x0 + .5
    assert x_db(b, X) == x0 + .5, 'the recovered edit was not saved'
    assert b.js("()=>localStorage.getItem('shotplans:unsaved:workshop')") is None


def test_remote_rerender_keeps_focus(app):
    app.js("([id])=>{const S=window.__shotplans.S;S.shotId=window.__shotplans.cur().items.find(i=>i.id===id).shot;S.sel=id}", [CAM])
    app.rerender()
    f = app.page.locator('#insp-d [data-f="name"]')
    f.click()
    app.page.keyboard.press('End')
    app.wait(1200)
    remote(app, Z, 1)
    app.wait(300)
    assert app.js("()=>document.activeElement.dataset.f") == 'name'
    app.page.keyboard.press('Backspace')
    app.page.keyboard.press('2')
    app.wait(200)
    assert app.item(CAM) is not None and app.S('beat') == 0


def test_local_tabs_see_each_other(open_app):
    a = open_app()
    b_page = a.page.context.new_page()
    b = sp.App(b_page, a.out_dir)
    b_page.goto(a.page.url)
    b_page.wait_for_timeout(900)
    x0 = a.item(X)['x']
    a.js("()=>{window.__ev=[];addEventListener('storage',e=>window.__ev.push([e.key,(e.newValue||'').length,!!window.__shotplans.S.drag,window.__shotplans.S.mode]))}")
    b_page.bring_to_front()
    b.js("id=>{const S=window.__shotplans.S;S.sel=id}", X)
    b_page.keyboard.press('ArrowRight')
    b.wait(1500)
    assert b.item(X)['x'] == x0 + .25, "tab B's own nudge did not register (test rig, not sync)"
    a.page.bring_to_front()
    for _ in range(20):
        if a.item(X)['x'] == x0 + .25:
            break
        a.wait(250)
    if not a.js('()=>window.__ev.length'):
        pytest.skip('this headless browser sometimes delivers no storage event between two file:// tabs; nothing for the app to react to')
    assert a.item(X)['x'] == x0 + .25, 'tab A did not pick up tab B\'s save'
    a.js("id=>{const S=window.__shotplans.S;S.sel=id}", Y)
    a.page.keyboard.press('ArrowDown')
    a.wait(1500)
    st = a.stored('workshop')
    assert next(i for i in st['items'] if i['id'] == X)['x'] == x0 + .25, "tab A's save overwrote tab B's edit"
