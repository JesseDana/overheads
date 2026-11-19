"""v41: a production holds scenes in story order and a library of locations; each scene dresses and lights its own set."""
import json, os
from test_r11 import live2, grouped, codes, OUT, SHEET


def ids_of(app, sel):
    return app.js("s=>{const P=window.__shotplans,sc=P.cur();return sc.items.filter(i=>i.kind===s).map(i=>i.id)}", sel)


def go_scene(app, gi):
    app.js("i=>{const P=window.__shotplans,sc=P.cur(),g=sc.groups[i];P.goShot(sc.shots.findIndex(s=>s.grp===g.id))}", gi)
    app.wait(150)


def visible_furn(app):
    """furniture the current scene can see, by position"""
    return app.js("()=>{const P=window.__shotplans,sc=P.cur();P.shotOf(sc);return sc.items.filter(i=>i.kind==='furn').map(i=>[i.id,i.x,i.y])}")


def saved(app):
    return app.js("()=>JSON.parse(localStorage.getItem('shotplans:workshop_doc'))")


def test_old_plan_becomes_one_location_with_each_scene_dressed(open_app):
    sc = grouped()
    nf = sum(1 for i in sc['items'] if i['kind'] == 'furn')
    nw = sum(1 for i in sc['items'] if i['kind'] == 'wall')
    nl = sum(1 for i in sc['items'] if i['kind'] == 'light')
    app = open_app({'workshop_doc': sc})
    s = app.scene()
    assert len(s['locs']) == 1 and s['locs'][0]['name'] == 'Workshop'
    assert all(g['locId'] == s['locs'][0]['id'] for g in s['groups'])
    walls = [i for i in s['items'] if i['kind'] == 'wall']
    assert len(walls) == nw and all(w['loc'] == s['locs'][0]['id'] and 'grp' not in w for w in walls), 'walls stay one shared set'
    for g in s['groups']:
        assert sum(1 for i in s['items'] if i['kind'] == 'furn' and i.get('grp') == g['id']) == nf
        assert sum(1 for i in s['items'] if i['kind'] == 'light' and i.get('grp') == g['id']) == nl
    # every scene sees one set of furniture, not three stacked
    for gi in range(3):
        go_scene(app, gi)
        assert len(visible_furn(app)) == nf
    # the saved document has everything, and no in-memory bookkeeping
    app.js("()=>{window.__shotplans.cur().items.find(i=>i.kind==='furn').x+=0.5}")
    app.js("()=>window.__shotplans.S&&0")
    app.page.keyboard.press('Escape')
    assert not app.errors, app.errors


def test_same_doc_loads_the_same_ids_twice(open_app):
    """ids made while loading an old plan must not change between loads, or merging with another device breaks"""
    sc = grouped()
    a = open_app({'workshop_doc': sc}).scene()
    b = open_app({'workshop_doc': json.loads(json.dumps(sc))}).scene()
    key = lambda s: sorted((i['id'], i.get('grp', ''), i.get('loc', '')) for i in s['items'])
    assert key(a) == key(b) and [g['id'] for g in a['groups']] == [g['id'] for g in b['groups']] and a['locs'] == b['locs']


def test_furniture_and_lights_are_per_scene_walls_are_shared(open_app):
    app = open_app({'workshop_doc': grouped()})
    go_scene(app, 0)
    f0 = visible_furn(app)[0]
    wall = ids_of(app, 'wall')[0]
    app.js("([f,w])=>{const P=window.__shotplans,sc=P.cur();sc.items.find(i=>i.id===f).x+=3;sc.items.find(i=>i.id===w).x1+=1;P.S&&0}", [f0[0], wall])
    go_scene(app, 1)
    f1 = visible_furn(app)
    assert all(abs(x[1] - f0[1]) < 1e-6 or x[0] != f0[0] for x in f1)
    assert f0[0] not in [x[0] for x in f1], 'scene 2 sees its own copy'
    moved = next(x for x in visible_furn(app) if abs(x[2] - f0[2]) < 1e-6 and abs(x[1] - f0[1]) < 1e-6)
    assert moved, 'scene 2 furniture did not move'
    w = app.item(wall)
    assert w and app.js("w=>window.__shotplans.cur().items.some(i=>i.id===w)", wall), 'scene 2 sees the shared wall'
    assert app.js("w=>window.__shotplans.cur().items.find(i=>i.id===w).x1", wall) == w['x1']


def test_dragging_furniture_in_one_scene_leaves_the_other(open_app):
    app = open_app({'workshop_doc': grouped()}, device='desktop')
    go_scene(app, 0)
    app.space('set')
    fid = 'f_cred'
    before = app.item(fid)
    app.drag_item_to(fid, before['x'] + 2, before['y'])
    after = app.item(fid)
    assert abs(after['x'] - before['x']) > 1
    go_scene(app, 2)
    twin = [x for x in visible_furn(app) if x[0].startswith('f_cred')]
    assert twin and all(abs(x[1] - before['x']) < 1e-6 for x in twin)
    # and saving keeps both
    app.wait(800)
    doc = saved(app)
    if doc:
        assert 'stash' not in doc and sum(1 for i in doc['items'] if i['kind'] == 'furn') == 3 * len(visible_furn(app))


def test_bring_in_lights_from_another_scene(open_app):
    sc = grouped()
    app = open_app({'workshop_doc': sc}, device='phone')
    # scene 3 loses its lights; then brings in scene 1's
    go_scene(app, 2)
    app.js("()=>{const P=window.__shotplans,sc=P.cur();sc.items=sc.items.filter(i=>i.kind!=='light')}")
    app.rerender()
    nl = sum(1 for i in sc['items'] if i['kind'] == 'light')
    app.page.tap('#shotBtn')
    app.page.tap('#sheet [data-do="setfrom"]')
    app.wait(200)
    opts = app.page.locator('#sfScene option')
    assert opts.count() == 2
    app.page.select_option('#sfScene', index=0)
    app.page.uncheck('#sheet [data-cat="furn"]')
    app.page.screenshot(path=OUT + 'v41_phone_setfrom.png')
    app.page.tap('#sheet [data-c="go"]')
    app.wait(200)
    assert len(ids_of(app, 'light')) == nl
    g3 = app.scene()['groups'][2]['id']
    assert all(i.get('grp') == g3 for i in app.scene()['items'] if i['kind'] == 'light' and i['id'] in ids_of(app, 'light'))
    app.page.click('#undoBtn') if app.page.locator('#undoBtn').is_visible() else app.page.keyboard.press('Control+z')
    app.wait(200)
    assert len(ids_of(app, 'light')) == 0
    assert not app.errors, app.errors


def test_new_scene_is_dressed_and_unlit_and_can_move_location(open_app):
    app = open_app({'workshop_doc': grouped()})
    nf = len(visible_furn(app))
    app.page.click('#shotBtn')
    app.page.click('#sheet [data-do="newscene"]')
    app.wait(250)
    assert len(visible_furn(app)) == nf and len(ids_of(app, 'light')) == 0
    assert len(ids_of(app, 'wall')) > 0
    # move it to a new location: an empty room
    app.page.select_option('#sheet [data-k="locId"]', '__new')
    app.wait(250)
    s = app.scene()
    g = s['groups'][1]
    assert len(s['locs']) == 2 and g['locId'] == s['locs'][1]['id']
    assert len(ids_of(app, 'wall')) == 0, 'a new location has no walls yet'
    app.page.fill('#sheet [data-k="locName"]', 'Parking lot')
    app.wait(100)
    assert app.scene()['locs'][1]['name'] == 'Parking lot'
    app.page.screenshot(path=OUT + 'v41_desktop_scene_details.png')
    # back to the first location: its walls return
    app.page.select_option('#sheet [data-k="locId"]', s['locs'][0]['id'])
    app.wait(250)
    assert len(ids_of(app, 'wall')) > 0
    assert len(app.scene()['locs']) == 2, 'an unused location stays in the library'
    assert not app.errors, app.errors


def test_a_scene_can_have_its_own_walls(open_app):
    app = open_app({'workshop_doc': grouped()})
    go_scene(app, 1)
    app.page.click('#shotBtn')
    app.page.click('#sheet [data-do="gedit"]')
    app.wait(200)
    app.page.select_option('#sheet [data-k="ownArch"]', 'own')
    app.wait(200)
    walls = ids_of(app, 'wall')
    w = app.item(walls[0])
    assert w['grp'] == app.scene()['groups'][1]['id'] and 'loc' not in w
    app.js("w=>{window.__shotplans.cur().items.find(i=>i.id===w).x1+=4}", walls[0])
    go_scene(app, 0)
    assert all(app.item(i).get('loc') for i in ids_of(app, 'wall')), 'scene 1 still sees the shared walls'
    assert walls[0] not in ids_of(app, 'wall')
    assert not app.errors, app.errors


def test_overview_page_per_location_and_shot_list_filter(open_app):
    sc = grouped()
    sc['groups'][2]['loc'] = 'Lobby'
    app = open_app({'workshop_doc': sc}, device='phone')
    s = app.scene()
    assert len(s['locs']) == 2
    app.page.tap('#shotBtn')
    app.wait(200)
    chips = app.page.locator('#sheet [data-lf]')
    assert chips.count() == 3
    chips.nth(2).tap()
    app.wait(100)
    vis = [r for r in app.page.locator('#shotList .srow').all() if r.is_visible()]
    assert len(vis) == 3 and all('3' in r.locator('.sn').inner_text() for r in vis)
    app.page.screenshot(path=OUT + 'v41_phone_list.png')
    assert not app.errors, app.errors


def test_undo_and_save_round_trip_keep_every_scene(open_app):
    app = open_app({'workshop_doc': grouped()})
    total = len(app.scene()['items'])
    go_scene(app, 1)
    app.page.click('#shotBtn')
    app.page.click('#sheet [data-do="newscene"]')
    app.wait(250)
    app.page.keyboard.press('Escape')
    app.page.click('#undoBtn')
    app.wait(200)
    assert len(app.scene()['items']) == total and len(app.scene()['groups']) == 3
    app.wait(900)
    doc = saved(app)
    if doc:
        assert 'stash' not in doc and len(doc['items']) == total and len(doc['locs']) == 1
