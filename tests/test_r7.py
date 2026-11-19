"""Round 7: distances (focus plane, camera-to-subject), applying a move to other shots, curved paths, the 180° line, the phone sheet."""
import sp


def scene(**ann):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'ann2':
            i['k'] = [{'x': 6, 'y': 5, 'r': 180}, {'x': 6, 'y': 5, 'r': 180}]
    return sc


def depth(app, cam, who, beat=0):
    return app.js("([c,w,b])=>{const P=window.__shotplans,sc=P.cur(),cp=P.poseT(sc,sc.items.find(i=>i.id===c),b),q=P.poseT(sc,sc.items.find(i=>i.id===w),b);return P.depthOf(cp,q)}", [cam, who, beat])


def dist(app, a, b, beat=0):
    pa, pb = app.pose(a, beat), app.pose(b, beat)
    return ((pa['x'] - pb['x']) ** 2 + (pa['y'] - pb['y']) ** 2) ** .5


def test_drag_snaps_to_shared_focus_plane(open_app):
    app = open_app({'room': scene()})
    app.go(shot='s1')
    app.drag_item_to('bob', 11, 5.2)
    app.wait(150)
    assert abs(depth(app, 'camA', 'bob') - depth(app, 'camA', 'ann')) < .01


def test_alt_drag_skips_focus_snap(open_app):
    app = open_app({'room': scene()})
    app.go(shot='s1')
    app.drag_item_to('bob', 11, 5.25, modifiers=('Alt',))
    app.wait(150)
    assert abs(depth(app, 'camA', 'bob') - depth(app, 'camA', 'ann')) > .1


def test_same_focus_button_and_distance_field(open_app):
    sc = scene()
    for i in sc['items']:
        if i['id'] == 'bob':
            i['k'] = [{'x': 11, 'y': 7, 'r': 180}] * 2
    app = open_app({'room': sc})
    app.go(shot='s1')
    app.select('bob')
    app.page.click('#insp-d [data-act="distcam"][data-v="camA"]')
    app.page.click('#insp-d [data-act="dfocus"][data-v="ann"]')
    app.wait(150)
    assert abs(depth(app, 'camA', 'bob') - depth(app, 'camA', 'ann')) < .01
    f = app.page.locator('#insp-d [data-f="dist"]')
    f.fill('6')
    f.dispatch_event('change')
    app.wait(150)
    assert abs(dist(app, 'bob', 'camA') - 6) < .02


def test_camera_matches_other_camera_distance_and_lens(open_app):
    sc = scene()
    for i in sc['items']:
        if i['id'] == 'camA':
            i['k'] = [{**q, 'aim': 'ann'} for q in i['k']]
        if i['id'] == 'camB':
            i['held'] = True
            i['k'] = [{'x': 13, 'y': 12, 'r': 0, 'f': 50, 'h': 5, 'aim': 'bob'}] * 2
    app = open_app({'room': sc})
    app.go(shot='s1')
    app.select('camB')
    app.page.click('#insp-d [data-act="cmatch"][data-v="camA"]')
    app.wait(150)
    assert abs(dist(app, 'camB', 'bob') - dist(app, 'camA', 'ann')) < .02
    assert app.pose('camB', 0)['f'] == app.pose('camA', 0)['f']


def test_apply_move_to_other_shot_at_same_spot(open_app):
    app = open_app({'room': scene()})
    app.go(shot='s1')
    app.drag_item_to('ann', 6, 3.5, modifiers=('Alt',))
    app.wait(150)
    to = app.pose('ann', 0)
    app.select('ann')
    app.page.click('#insp-d [data-act="applyshots"]')
    app.wait(150)
    assert app.page.locator('#sheet input[data-shot="s2"]').is_checked()
    app.page.click('#sheet [data-apply]')
    app.wait(150)
    for b in (0, 1):
        q = app.pose('ann2', b)
        assert abs(q['x'] - to['x']) < .01 and abs(q['y'] - to['y']) < .01


def test_curved_path_bends_the_move(open_app):
    app = open_app({'room': scene()})
    app.go(shot='s1', beat=1)
    app.js("()=>{const sc=window.__shotplans.cur();const b=sc.items.find(i=>i.id==='camB');b.k[1]={...b.k[1],cv:[16,9]}}")
    mid = app.js("()=>{const P=window.__shotplans,sc=P.cur();return P.poseT(sc,sc.items.find(i=>i.id==='camB'),0.5)}")
    # quadratic: .25*(12,12) + .5*(16,9) + .25*(12,10)
    assert abs(mid['x'] - 14) < .01 and abs(mid['y'] - 10) < .01
    app.open_more('list')
    app.wait(200)
    txt = app.js("()=>document.querySelector('#sheet').textContent")
    assert 'CURVED PUSH IN' in txt or 'CURVED TRACK' in txt, txt[:400]


def test_curve_handle_drag(open_app):
    app = open_app({'room': scene()})
    app.go(shot='s1', beat=1)
    app.select('camB')
    app.wait(150)
    h = app.page.locator('#overG rect[data-handle="cv"]').bounding_box()
    x0, y0 = h['x'] + h['width'] / 2, h['y'] + h['height'] / 2
    app.mouse_drag(x0, y0, x0 + 60, y0)
    app.wait(150)
    assert app.item('camB')['k'][1].get('cv'), 'dragging the handle should curve the move'


def facing_scene(across=False, direct=False):
    sc = scene()
    for i in sc['items']:
        if i['id'] == 'ann':
            i['k'] = [{'x': 6, 'y': 5, 'r': 180 if direct else 90}] * 2
        if i['id'] == 'bob':
            i['k'] = [{'x': 11, 'y': 5, 'r': 180 if direct else 270}] * 2
        if i['id'] == 'camB':
            i['held'] = True
            i['k'] = [{'x': 12, 'y': 2 if across else 12, 'r': 180 if across else 0, 'f': 50, 'h': 5}] * 2
    sc['axisOn'] = True
    return sc


def test_axis_auto_picks_people_facing_each_other(open_app):
    app = open_app({'room': facing_scene()})
    app.go(shot='s1')
    pr = app.js("()=>{const P=window.__shotplans,sc=P.cur(),p=P.axisPair(sc,P.shotOf(sc),0);return p&&p.map(x=>x.id)}")
    assert sorted(pr) == ['ann', 'bob']
    assert app.js("()=>!!document.querySelector('#worldG').innerHTML.match(/180°/)")


def test_axis_none_for_direct_address(open_app):
    app = open_app({'room': facing_scene(direct=True)})
    app.go(shot='s1')
    assert app.js("()=>{const P=window.__shotplans,sc=P.cur();return P.axisPair(sc,P.shotOf(sc),0)}") is None


def test_axis_warns_camera_across_line(open_app):
    app = open_app({'room': facing_scene(across=True)})
    app.go(shot='s1')
    note = app.js("()=>{const P=window.__shotplans,sc=P.cur();return P.axisNote(sc,sc.items.find(i=>i.id==='camB'),0)}")
    assert 'Across the 180° line from A' in note


def test_phone_preview_stays_small_after_scrolling_back(open_app):
    app = open_app('workshop', device='phone')
    cam = app.js("()=>window.__shotplans.inShot(window.__shotplans.cur()).find(i=>i.kind==='cam').id")
    app.select(cam)
    app.wait(300)
    sc = app.page.locator('#insp-m .insp-scroll')
    h = lambda: app.page.locator('#insp-m .insp-frame svg').bounding_box()['height']
    big = h()
    sc.evaluate('el=>el.scrollTop=300')
    app.wait(350)
    small = h()
    sc.evaluate('el=>el.scrollTop=20')
    app.wait(350)
    assert small < big - 30 and abs(h() - small) < 2, (big, small, h())
    b = app.page.locator('#insp-m .insp-frame svg').bounding_box()   # a tap on the picture brings it back to full size
    app.page.mouse.click(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2)
    app.wait(350)
    assert h() > small + 30


def test_phone_long_warning_leaves_controls_reachable(open_app):
    sc = scene()
    for i in sc['items']:
        if i['id'] == 'camA':
            i['k'] = [{**q, 'f': 135, 'aim': 'ann'} for q in i['k']]
            i['k'][1] = {**i['k'][1]}
    app = open_app({'room': sc}, device='phone')
    app.go(shot='s1')
    app.select('camA')
    app.wait(300)
    b = app.page.locator('#insp-m .insp-scroll').bounding_box()
    assert b['height'] >= 120 and b['y'] + 120 <= 852, b


def test_pictogram_is_the_only_figure_style(open_app):
    """the rounded style is gone: every plan draws pictograms, whatever it stored"""
    sc = facing_scene()
    sc['fig'] = 'round'
    app = open_app({'s': sc})
    assert app.scene()['fig'] == 'picto'
    app.page.click('#layersBtn')
    app.wait(150)
    assert app.page.locator('[data-fig]').count() == 0
    assert not app.errors, app.errors


def test_pdf_with_axis_curve_and_pictograms(open_app):
    from test_export import export, pdf_text
    sc = facing_scene(across=True)
    sc['fig'] = 'picto'
    for i in sc['items']:
        if i['id'] == 'camB':
            i['held'] = False
            i['k'][1] = {**i['k'][1], 'x': 9, 'y': 2, 'cv': [14, 1]}
    app = open_app({'room': sc})
    app.go(shot='s1')
    f = export(app, 'pdf')
    txt = pdf_text(f)
    assert '180°' in txt or 'Across the 180' in txt
