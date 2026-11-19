"""Round 9 (v30): Set and Shots spaces, the beat stepper, the lens slider, the View and Share sheets, the readout."""
import sp


def room(open_app, **kw):
    app = open_app({'room': sp.room_scene()}, **kw)
    app.go(shot='s1')
    return app


def space(app):
    return app.S('space')


# ---------------------------------------------------------------- spaces
def test_plan_with_talent_opens_in_shots_and_bare_room_in_set(open_app):
    assert space(room(open_app)) == 'shots'
    sc = sp.room_scene()
    sc['items'] = [i for i in sc['items'] if i['kind'] not in ('char', 'cam')]
    app = open_app({'bare': sc})
    assert space(app) == 'set'
    assert app.page.locator('#tools [data-menu="furn"]').is_visible()
    assert not app.page.locator('#tools [data-menu="cast"]').is_visible()


def test_set_is_fixed_in_shots_and_second_tap_opens_it_in_set(open_app):
    app = room(open_app)
    x, y = app.item_px('tbl')
    s = app.S('view')['s']
    app.mouse_drag(x, y, x + 2 * s, y)
    assert app.item('tbl')['x'] == 3, 'furniture moved in Shots'
    app.go(shot='s1')
    x, y = app.item_px('tbl')
    app.page.mouse.click(x, y)
    app.wait(120)
    assert app.S('sel') is None and 'is in Set' in app.toast()
    app.page.mouse.click(x, y)
    app.wait(250)
    assert space(app) == 'set' and app.S('sel') == 'tbl'
    x, y = app.item_px('tbl')
    s = app.S('view')['s']
    app.mouse_drag(x, y, x + 2 * s, y)
    assert app.item('tbl')['x'] > 4.5, 'furniture did not move in Set'


def test_talent_and_cameras_wait_in_set(open_app):
    app = room(open_app)
    app.space('set')
    for who in ('ann', 'camA'):
        x, y = app.item_px(who)
        app.page.mouse.click(x, y)
        app.wait(120)
        assert app.S('sel') is None, '%s was selectable in Set' % who
    p0 = app.pose('ann')
    x, y = app.item_px('ann')
    app.mouse_drag(x, y, x + 60, y)
    assert app.pose('ann') == p0
    assert app.js("()=>!!document.querySelector('#worldG g.nohit[opacity]')"), 'talent and cameras are not dimmed in Set'


def test_switching_space_drops_a_selection_that_does_not_belong(open_app):
    app = room(open_app)
    app.select('camA')
    app.space('set')
    assert app.S('sel') is None
    app.select('tbl')
    app.space('shots')
    assert app.S('sel') is None


def test_lights_adjust_in_both_spaces(open_app):
    app = room(open_app)
    for sp_ in ('shots', 'set'):
        app.space(sp_)
        app.go(shot='s1')
        x, y = app.item_px('key')
        app.page.mouse.click(x, y)
        app.wait(120)
        assert app.S('sel') == 'key', sp_


def test_adding_switches_to_the_right_space(open_app):
    app = room(open_app)
    app.space('set')
    app.page.click('#tools [data-menu="furn"]')
    app.page.locator('#sheet [data-add], #sheet [data-shape], #sheet button').first.click()
    app.wait(200)
    assert space(app) == 'set'
    app.js("()=>window.__shotplans.rigSheet()")
    app.page.click('#sheet [data-newcam]')
    app.wait(250)
    assert space(app) == 'shots'
    assert app.item(app.S('sel'))['kind'] == 'cam'


def test_layer_select_goes_to_the_layer_s_space(open_app):
    app = room(open_app)
    app.page.click('#layersBtn')
    app.page.click('#sheet [data-ly="furn"][data-op="sel"]')
    app.wait(200)
    assert space(app) == 'set' and 'tbl' in app.S('multi')


def test_set_space_scene_panel_is_about_the_set(open_app):
    app = room(open_app)
    app.space('set')
    txt = app.page.locator('#insp-d').inner_text()
    assert 'Bring in furniture or lights' in txt and 'Beat 1 name' not in txt
    app.space('shots')
    assert 'Beat 1 name' in app.page.locator('#insp-d').inner_text()


def test_exports_are_not_dimmed_in_set(open_app):
    app = room(open_app)
    app.space('set')
    from test_export import export
    assert export(app, 'pdf')
    assert space(app) == 'set'


# ---------------------------------------------------------------- top bar and canvas
def test_top_bar_fits_a_phone(open_app):
    app = room(open_app, device='phone')
    w = app.js("()=>innerWidth")
    for sel in ('#sceneBtn', '#spaceSeg', '#layersBtn', '#moreBtn', '#undoBtn', '#fitBtn'):
        b = app.page.locator(sel).bounding_box()
        assert b and b['x'] >= 0 and b['x'] + b['width'] <= w + .5, sel
    for b in app.page.locator('#spaceSeg button').all():
        assert b.evaluate("e=>e.scrollWidth<=e.clientWidth"), 'Set/Shots label is clipped'
    assert app.page.locator('#toolsHost #tools [data-menu="cast"]').is_visible()
    assert app.page.locator('#toolsHost #tools [data-menu="rig"]').is_visible()
    assert not app.page.locator('#zinBtn').is_visible() or app.js("()=>!matchMedia('(pointer:coarse)').matches")


def test_view_dot_and_frames_toggle(open_app):
    app = room(open_app, device='phone')
    dot = lambda: app.js("()=>document.querySelector('#layersBtn').classList.contains('dot')")
    assert not dot()
    assert app.page.locator('#frames-m').is_visible()
    app.page.click('#layersBtn')
    app.page.click('#sheet [data-vw="frames0"]')
    app.page.keyboard.press('Escape')
    app.wait(150)
    assert not app.page.locator('#frames-m').is_visible() and dot()
    app.page.click('#layersBtn')
    app.page.click('#sheet [data-vw="frames1"]')
    app.page.click('#sheet [data-ly="light"][data-op="hide"]')
    app.page.keyboard.press('Escape')
    app.wait(150)
    assert app.page.locator('#frames-m').is_visible() and dot()


def test_share_sheet_has_exports_only(open_app):
    app = room(open_app)
    app.page.click('#moreBtn')
    txt = app.page.locator('#sheet').inner_text()
    assert 'PDF' in txt and 'Shot list' in txt and 'Plan file' in txt
    assert 'Import' not in txt.replace('import one from the scene menu', '')
    app.page.keyboard.press('Escape')
    app.page.click('#sceneBtn')
    assert 'Import plan file' in app.page.locator('#sheet').inner_text()


# ---------------------------------------------------------------- beats
def test_phone_beat_stepper(open_app):
    app = room(open_app, device='phone')
    assert app.page.locator('#beatName').is_visible()
    assert not app.page.locator('#beats [data-beat]').first.is_visible()
    assert app.page.locator('#beatPrev').is_disabled()
    assert 'Beat 1 of 2' in app.page.locator('#beatName').inner_text().replace('BEAT', 'Beat').replace('OF', 'of')
    app.page.click('#beatNext')
    app.wait(150)
    assert app.S('beat') == 1 and app.page.locator('#beatNext').is_disabled(), 'next should stop at the last beat'
    app.page.locator('#beatNext').click(force=True)
    app.wait(150)
    assert len(app.scene()['shots'][0]['beats']) == 2, 'a tap past the last beat must not add one'
    app.page.click('#beatAdd')
    app.wait(200)
    assert app.S('beat') == 2 and len(app.scene()['shots'][0]['beats']) == 3
    assert app.pose('ann', 2)['x'] == app.pose('ann', 1)['x']
    app.page.click('#beatPrev')
    app.wait(150)
    assert app.S('beat') == 1
    assert len(app.scene()['shots'][1]['beats']) == 2, 'adding a beat reached into another shot'


def test_desktop_keeps_beat_chips(open_app):
    app = room(open_app)
    assert app.page.locator('#beats [data-beat="1"]').is_visible()
    assert not app.page.locator('#beatName').is_visible()


# ---------------------------------------------------------------- lens
def test_lens_slider_settles_on_common_lenses_and_box_takes_any(open_app):
    app = room(open_app)
    app.select('camA')
    assert app.page.locator('#insp-d [data-act="lens"], #insp-d [data-lens]').count() == 0, 'lens preset buttons are back'
    sl = app.page.locator('#insp-d #f-lens')
    for near, want in ((48, 50), (83, 85), (36, 35), (27, 28)):
        v = app.js("f=>window.__shotplans.lensPos(f)", near)
        sl.evaluate("(e,v)=>{e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))}", v)
        app.wait(120)
        assert app.pose('camA')['f'] == want, (near, app.pose('camA')['f'])
    v = app.js("f=>window.__shotplans.lensPos(f)", 60)
    sl.evaluate("(e,v)=>{e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))}", v)
    app.wait(120)
    assert 57 <= app.pose('camA')['f'] <= 63 and app.pose('camA')['f'] not in (50, 65), 'between stops the slider should stay free'
    box = app.page.locator('#insp-d #f-lensmm')
    box.fill('47')
    box.dispatch_event('change')
    app.wait(150)
    assert app.pose('camA')['f'] == 47
    assert abs(float(app.page.locator('#insp-d #f-lens').input_value()) - app.js("f=>window.__shotplans.lensPos(f)", 47)) < 2


# ---------------------------------------------------------------- controls
def test_camera_controls_order_and_setup_section(open_app):
    app = room(open_app, device='phone')
    app.select('camA')
    ys = [app.page.locator(sel).first.bounding_box()['y'] for sel in ('#insp-m #f-lens', '#insp-m .htrow', '#insp-m [data-act="aimto"]')]
    assert ys == sorted(ys), 'expected Lens, then height and tilt, then Aim at: %s' % ys
    assert app.page.locator('#insp-m #f-camh, #insp-m #f-tilt').count() == 0, 'height and tilt are steppers now, not sliders'
    more = app.page.locator('#insp-m details.more')
    assert more.count() == 1 and not more.evaluate('e=>e.open'), 'setup section should start closed on a phone'
    assert not app.page.locator('#insp-m [data-f="name"]').is_visible()
    app.page.click('#insp-m details.more summary')
    app.wait(150)
    assert app.page.locator('#insp-m [data-f="name"]').is_visible()


def test_setup_section_is_open_on_desktop(open_app):
    app = room(open_app)
    app.select('camA')
    assert app.page.locator('#insp-d details.more').evaluate('e=>e.open')
    assert app.page.locator('#insp-d [data-f="name"]').is_visible()


def test_cameras_are_ink_not_coloured(open_app):
    app = room(open_app)
    app.select('ann')
    chip = app.page.locator('#insp-d [data-act="look"][data-v="camA"] .dot')
    assert 'sq' in chip.get_attribute('class')
    app.js("()=>window.__shotplans.rigSheet()")
    assert app.page.locator('#sheet .cbadge').count() == 3
    assert 'colour' not in app.page.locator('#sheet').inner_text()


# ---------------------------------------------------------------- readout
def test_phone_readout_rows(open_app):
    app = room(open_app, device='phone')
    fr = app.page.locator('#frames-m .fr[data-cam="camA"]')
    txt = fr.inner_text()
    assert '35mm' in txt and fr.locator('.hd').count() == 2, 'two-up phone rows are led by each person\'s head; the name is in the picture'
    assert 'In frame' not in app.page.locator('#frames-m').inner_text()
    assert fr.locator('.prow').count() == 2
    info = app.page.locator('#frames-m [data-info]').bounding_box()
    assert info['x'] + info['width'] <= app.js('()=>innerWidth')
    both = [app.page.locator('#frames-m .fr[data-cam="%s"]' % c).bounding_box() for c in ('camA', 'camB')]
    assert both[0]['x'] + both[0]['width'] <= both[1]['x'] + 1 and both[1]['x'] + both[1]['width'] <= app.js('()=>innerWidth'), 'both frames should sit side by side on the phone'


def test_cameras_follow_the_theme_ink(open_app):
    app = room(open_app)
    fill = lambda: app.js("()=>getComputedStyle(document.querySelector('#worldG rect[fill=\"var(--ink)\"][rx=\".1\"]')).fill")
    lum = lambda c: sum(int(v) for v in c[c.index('(') + 1:c.index(')')].split(',')[:3])
    assert lum(fill()) < 150
    app.page.emulate_media(color_scheme='dark')
    app.rerender()
    assert lum(fill()) > 500, 'camera is dark on the dark plan: %s' % fill()


# ---------------------------------------------------------------- v31
def _select_people_layer(app):
    app.page.click('#layersBtn')
    app.page.click('#sheet [data-ly="cast"][data-op="sel"]')
    app.wait(200)


def test_group_moves_in_this_beat_or_every_beat_by_choice(open_app):
    app = room(open_app, device='phone')
    _select_people_layer(app)
    assert {'ann', 'bob', 'camA', 'camB'} <= set(app.S('multi'))
    a0, a1 = app.pose('ann', 0), app.pose('ann', 1)
    x, y = app.item_px('bob')
    app.mouse_drag(x, y, x + 40, y)
    app.wait(150)
    d = app.pose('ann', 0)['x'] - a0['x']
    assert d > .5 and app.pose('ann', 1)['x'] == a1['x'], 'by default a group moves in this beat only'
    app.page.click('#multibar [data-act="gall"][data-v="1"]')
    app.wait(100)
    b0, b1, c1 = app.pose('ann', 0), app.pose('ann', 1), app.pose('camB', 1)
    x, y = app.item_px('bob')
    app.mouse_drag(x, y, x, y + 40)
    app.wait(150)
    dy = app.pose('ann', 0)['y'] - b0['y']
    assert dy > .5
    assert abs(app.pose('ann', 1)['y'] - b1['y'] - dy) < .01, 'Every beat did not carry the other beat along'
    assert abs(app.pose('camB', 1)['y'] - c1['y'] - dy) < .01
    assert abs(app.pose('ann', 1)['x'] - b1['x']) < .01
    n = app.hist_len()
    app.page.click('#undoBtn')
    app.wait(150)
    assert abs(app.pose('ann', 1)['y'] - b1['y']) < .01, 'one undo should take the whole group move back'


def test_group_toggle_only_where_it_means_something(open_app):
    app = room(open_app)
    _select_people_layer(app)
    assert app.page.locator('#insp-d [data-act="gall"]').count() == 2
    app.page.keyboard.press('Escape')
    app.space('set')
    app.page.click('#layersBtn')
    app.page.click('#sheet [data-ly="furn"][data-op="sel"]')
    app.wait(200)
    assert app.page.locator('#insp-d [data-act="gall"]').count() == 0


def test_desktop_bottom_row_starts_at_the_left(open_app):
    app = room(open_app)
    first = lambda: app.page.locator('#beats .sstep > button:visible').first.bounding_box()['x']
    x1 = first()
    assert x1 < 40
    app.go(shot='s2')
    assert first() == x1, 'the row should not shift when the shot changes'
    app.space('set')
    assert app.page.locator('#tools [data-menu="furn"]').bounding_box()['x'] < 200


def test_other_beat_ghost_is_not_hidden_behind_nearer_furniture(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'ann':   # beat 1 by the camera, beat 2 at the back
            i['k'] = [{'x': 8, 'y': 9, 'r': 180}, {'x': 8, 'y': 4, 'r': 180}]
        if i['id'] == 'tbl':   # a TV on a stand between the two spots, tall enough to be in frame
            i.update(shape='tv', label='TV', x=8, y=6.5, w=4, h=1)
        if i['id'] == 'camA':
            i['k'] = [{'x': 8, 'y': 13, 'r': 0, 'f': 24, 'h': 4}] * 2
    app = open_app({'room': sc})
    app.go(shot='s1', beat=1)   # ann at the back; her beat-1 ghost is nearer than the table
    svg = app.js("()=>{const P=window.__shotplans,sc=P.cur();return P.frameInfo(sc,sc.items.find(i=>i.id==='camA'),1,400).svg}")
    assert svg.count('class="ffurn"') >= 3, 'the TV is not in frame; the test proves nothing'
    g, t = svg.index('<g opacity=".16">'), svg.rindex('class="ffurn"')   # the TV is the nearest furniture, so the last drawn
    assert t < g, 'the nearer ghost was drawn before (behind) the TV'
    app.go(shot='s1', beat=0)   # now the ghost is at the back and belongs behind the table
    svg = app.js("()=>{const P=window.__shotplans,sc=P.cur();return P.frameInfo(sc,sc.items.find(i=>i.id==='camA'),0,400).svg}")
    assert svg.index('<g opacity=".16">') < svg.rindex('class="ffurn"'), 'the far ghost should sit behind the TV'
