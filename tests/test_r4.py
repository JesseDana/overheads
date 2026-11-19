"""Round 4 (code reviewer): confirmed bugs in v16. Every test here fails on v16 and documents one finding in
reports/r4/code.md. Save tests wrap the app's db handle at runtime so writes can fail or be held in flight."""
import copy, re, subprocess, time
import pytest
import sp

# Wrap the app's db handle at runtime so scene writes can fail or be delayed (the stock DBMOCK can't fail).
WRAP = """()=>{const S=window.__shotplans.S,real=S.db;window.__fail=false;window.__setDelay=0;window.__sets=0;
 S.db={collection:n=>{const c=real.collection(n);if(n!=='scenes')return c;
  return {onSnapshot:c.onSnapshot,doc:id=>{const d=c.doc(id);return {get:d.get,delete:d.delete,set:async o=>{window.__sets++;
    if(window.__setDelay)await new Promise(r=>setTimeout(r,window.__setDelay));
    if(window.__fail){const e=new Error('offline');e.code='unavailable';throw e}return d.set(o)}}}}}}}"""


def wrap(app):
    app.js(WRAP)


def scene_ids(app):
    return app.js("()=>[...window.__shotplans.S.scenes.keys()]")


FURN = [i['id'] for i in sp.WS['items'] if i['kind'] == 'furn' and i.get('shape') != 'rug']
X, Z = FURN[0], FURN[2]


def x_of(app, id, where='app'):
    if where == 'app':
        return app.js("id=>Math.round(window.__shotplans.cur().items.find(i=>i.id===id).x*100)/100", id)
    return app.js("id=>Math.round(window.__db.read('workshop').items.find(i=>i.id===id).x*100)/100", id)


# ---------------------------------------------------------------- save bookkeeping
def test_new_scene_survives_failed_first_save(open_app):
    app = open_app(db=True)
    wrap(app)
    app.js('window.__fail=true')
    app.page.click('#sceneBtn')
    app.page.click('#sheet [data-do="dupscene"]')
    app.wait(600)
    nid = app.S('curId')
    assert nid != 'workshop'
    app.js('window.__fail=false')  # signal comes back before the first retry (2 s)
    app.wait(3500)
    assert nid in scene_ids(app), 'new plan dropped after a failed first save; toast: %r' % app.toast()
    assert app.db(nid) is not None, 'new plan never reached the db'


def test_remote_change_during_inflight_save_is_kept(open_app):
    app = open_app(db=True)
    wrap(app)
    x0, z0 = x_of(app, X, 'db'), x_of(app, Z, 'db')
    app.js('window.__setDelay=400')
    app.js("id=>{const S=window.__shotplans.S;S.sel=id;S.multi=[]}", X)
    app.page.keyboard.press('ArrowRight')
    for _ in range(300):  # wait until our write is in flight (held 400 ms by the wrapper)
        if app.js('window.__sets') == 1:
            break
        app.wait(10)
    app.wait(100)
    app.js("([id])=>{const d=window.__db.read('workshop');d.items.find(i=>i.id===id).x+=3;window.__db.remote('workshop',d)}", [Z])
    app.js('window.__setDelay=0')
    app.wait(2500)
    got = dict(app_x=x_of(app, X), app_z=x_of(app, Z), db_x=x_of(app, X, 'db'), db_z=x_of(app, Z, 'db'))
    assert got == dict(app_x=x0 + .25, app_z=z0 + 3, db_x=x0 + .25, db_z=z0 + 3), got






# ---------------------------------------------------------------- escaping / hostile documents
def lit_scene(bob='Bob'):
    sc = sp.room_scene()
    sc['items'] = [i for i in sc['items'] if i['kind'] != 'light']
    sc['items'].append({'id': 'keyAnn', 'kind': 'light', 'type': 'point', 'x': 4, 'y': 8, 'r': -34, 'level': 100, 'spread': 20})
    for i in sc['items']:
        if i['id'] == 'camA':
            i['k'] = [{'x': 11, 'y': 11, 'r': 0, 'f': 85, 'h': 5}] * 2
    sc['cast'][1]['name'] = bob
    return sc


def test_pdf_unlit_note_is_plain_text(open_app):
    app = open_app({'room': lit_scene("Bob O'Brien & Co")})
    app.go(shot='s1')
    note = app.js("()=>{const P=window.__shotplans,sc=P.cur();return P.frameInfo(sc,sc.items.find(i=>i.id==='camA'),0,320).litNote}")
    assert 'No light reaches' in note, note
    app.open_more('pdf')
    for _ in range(60):
        app.wait(250)
        if app.js('window.__saved.length'):
            break
    f = app.saved_files()[-1]
    txt = subprocess.run(['pdftotext', f, '-'], capture_output=True, text=True).stdout
    assert 'No light reaches' in txt
    assert '&#39;' not in txt and '&amp;' not in txt, re.findall(r'No light reaches[^\n]*', txt)


def test_non_string_cast_and_scene_names(open_app):
    sc = sp.room_scene()
    sc['cast'][0]['name'] = 42
    sc['name'] = 7
    app = open_app({'room': sc})
    app.go(shot='s1')
    app.select('camA')
    app.wait(200)
    assert not app.errors, app.errors
    assert app.js("()=>typeof window.__shotplans.cur().cast[0].name") == 'string'


def test_prototype_keys_in_enums(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'sofa1':
            i['shape'] = 'constructor'
        if i['id'] == 'key':
            i['type'] = 'toString'
        if i['id'] == 'ann':
            i['k'][0]['ps'] = 'constructor'
    sc['sensor'] = 'constructor'
    sc['items'].append({'id': 'fr1', 'kind': 'frame', 'type': 'valueOf', 'x': 8, 'y': 8, 'r': 0, 'size': 4})
    app = open_app({'room': sc})
    app.go(shot='s1')
    app.select('camA')
    s = app.scene()
    shape = [i for i in s['items'] if i['id'] == 'sofa1'][0]['shape']
    ps = [i for i in s['items'] if i['id'] == 'ann'][0]['k'][0].get('ps')
    body = app.js("()=>document.body.innerText")
    assert not app.errors and s['sensor'] == 'ff' and shape != 'constructor' and ps != 'constructor' and 'native code' not in body, \
        (app.errors[:2], s['sensor'], shape, ps, 'native code' in body)


# ---------------------------------------------------------------- labels
def test_text_item_size_is_honoured(open_app):
    sc = sp.room_scene()
    sc['items'].append({'id': 'tx', 'kind': 'text', 'text': 'STAGE', 'x': 8, 'y': 8, 'size': 2})
    app = open_app({'room': sc})
    app.go(shot='s1')
    px = app.js("()=>{const S=window.__shotplans.S,t=[...document.querySelectorAll('#worldG text')].find(t=>t.textContent==='STAGE');return [parseFloat(t.getAttribute('font-size'))*S.view.s,t.getAttribute('visibility')]}")
    s = app.S('view')['s']
    assert px[0] > 1.5 * s * .9, 'Text item set to 2 ft renders at %.1f px (2 ft = %.0f px)' % (px[0], 2 * s)


def test_user_text_not_hidden_by_collision(open_app):
    sc = sp.room_scene()
    sc['items'].append({'id': 'tx', 'kind': 'text', 'text': 'MARK', 'x': 6, 'y': 6.4, 'size': .55})
    app = open_app({'room': sc})
    app.go(shot='s1')
    vis = app.js("()=>[...document.querySelectorAll('#worldG text')].find(t=>t.textContent==='MARK').getAttribute('visibility')")
    assert vis != 'hidden'


# ---------------------------------------------------------------- export lock
def test_add_camera_during_export_lands_in_current_shot(open_app):
    app = open_app({'room': sp.room_scene()})
    app.go(shot='s1')
    app.open_more('pdf')
    ok = False
    for _ in range(400):
        if app.js("()=>{const S=window.__shotplans.S;if(S.busy&&S.shotId==='s2'){document.querySelector('#tools [data-menu=\"rig\"]').click();return true}return false}"):
            ok = True
            break
        app.wait(5)
    assert ok, 'export never reached shot 2'
    for _ in range(60):
        app.wait(250)
        if app.js('window.__saved.length'):
            break
    app.wait(300)
    app.page.click('[data-newcam]')
    app.wait(150)
    s = app.scene()
    new = [i for i in s['items'] if i['kind'] == 'cam' and i['id'] not in ('camA', 'camB', 'camC')]
    assert new and new[0]['shot'] == 's1', 'camera added during export went to %s' % (new and new[0]['shot'])




# ---------------------------------------------------------------- size limits
def test_beat_count_is_capped(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'ann':
            i['k'] = [{}] * 20000
    t = time.time()
    app = open_app({'room': sc}, wait=200)
    app.wait(100)
    n = app.js("()=>document.querySelectorAll('#beats button').length")
    dt = time.time() - t
    assert n < 1000, '%d beat chips rendered from one 20,000-pose list (%.1f s to load)' % (n, dt)


# ---------------------------------------------------------------- hostile document, every string field
P = '<img src=x onerror="window.__x%d=1">'


def hostile():
    sc = sp.room_scene()
    n = iter(range(1, 99))
    sc['name'] = P % next(n); sc['notes'] = P % next(n)
    sc['shots'][0]['name'] = P % next(n); sc['shots'][0]['beats'][0]['name'] = P % next(n)
    sc['cast'][0]['name'] = P % next(n); sc['cast'][1]['color'] = '#fff" onload="x'
    for i in sc['items']:
        if i['kind'] == 'wall': i['name'] = P % next(n)
        if i['kind'] == 'furn': i['label'] = P % next(n)
        if i['kind'] == 'light': i['name'] = P % next(n)
        if i['kind'] == 'cam': i['name'] = P % next(n); i['k'][0]['aim'] = 'x" onmouseover="y'
    sc['items'] += [
        {'id': 'img1', 'kind': 'img', 'src': 'https://example.invalid/a.png', 'x': 8, 'y': 7, 'w': 4, 'h': 3, 'opacity': '1"/><img src=x onerror="window.__x90=1">'},
        {'id': 'fr1', 'kind': 'frame', 'type': 'neg', 'x': 8, 'y': 8, 'r': 0, 'size': 4, 'name': P % 91},
        {'id': 'tx1', 'kind': 'text', 'text': P % 92, 'x': 2, 'y': 2},
        {'id': 'q"><img src=x onerror="window.__x93=1">', 'kind': 'furn', 'shape': 'chair', 'x': 5, 'y': 5, 'color': '"><img src=x onerror="window.__x94=1">'}]
    return sc


def fired(app):
    return app.js("()=>Object.keys(window).filter(k=>/^__x\\d+$/.test(k))")


def test_hostile_document_runs_no_script(open_app):
    app = open_app({'room': hostile()})
    app.go(shot='s1')
    for sel in ('img1', 'camA', 'fr1', 'key'):
        app.select(sel)
    app.open_more('list'); app.wait(200); app.page.keyboard.press('Escape')
    app.page.click('#sceneBtn'); app.wait(200); app.page.keyboard.press('Escape')
    app.wait(300)
    assert fired(app) == [], fired(app)


def test_hostile_db_doc_id_runs_no_script(open_app):
    sc = sp.room_scene()
    app = open_app({'room': sc, 'z"><img src=x onerror="window.__x95=1">': sp.room_scene('Other')}, db=True)
    app.page.click('#sceneBtn'); app.wait(300)
    assert fired(app) == [], fired(app)
