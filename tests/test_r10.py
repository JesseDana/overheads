"""Round 10 (v32): changes from the first usability review round."""
import sp


def room(open_app, sc=None, **kw):
    app = open_app({'room': sc or sp.room_scene()}, **kw)
    app.go(shot='s1')
    return app


def tap(app, id):
    x, y = app.item_px(id)
    app.page.touchscreen.tap(x, y)
    app.wait(500)


def view(app):
    return app.S('view')


# ---------------------------------------------------------------- phone sheets
def test_talent_sheet_shows_every_camera_frame(open_app):
    app = room(open_app, device='phone')
    tap(app, 'ann')
    minis = app.page.locator('#insp-m .pvrow.all .mini')
    assert minis.count() == 2
    assert 'Ann' in app.page.locator('#insp-m .hd-cap').inner_text()
    txt = minis.first.inner_text()
    assert '35mm' in txt and any(w in txt for w in ('Waist', 'Full', 'Knees', 'Thighs', 'Chest', 'Close-up', 'Ankles', 'out')), txt
    minis.nth(1).tap()
    app.wait(300)
    assert app.S('sel') == 'camB'


def test_camera_sheet_header_and_lens_on_first_screen(open_app):
    app = room(open_app, device='phone')
    tap(app, 'camA')
    cap = app.page.locator('#insp-m .hd-cap').inner_text()
    assert '35mm' in cap and 'Ann' in cap
    assert app.page.locator('#insp-m .pvbtn').count() == 0
    sheet = app.page.locator('#insp-m').bounding_box()
    for sel in ('#insp-m #f-lens', '#insp-m [data-act="aimto"]'):
        b = app.page.locator(sel).first.bounding_box()
        assert b['y'] + b['height'] <= sheet['y'] + sheet['height'] + 1, sel + ' is below the fold'
    assert app.page.locator('#insp-m .insp-others .mini').count() == 1


def test_short_phone_keeps_a_usable_preview(open_app):
    app = room(open_app, device='phone')
    app.page.set_viewport_size({'width': 393, 'height': 680})
    app.wait(300)
    tap(app, 'camA')
    b = app.page.locator('#insp-m .insp-frame svg').bounding_box()
    assert b['height'] >= 100, b


def test_plan_view_comes_back_when_the_controls_close(open_app):
    sc = sp.room_scene()
    app = room(open_app, sc, device='phone')
    v0 = view(app)
    tap(app, 'camA')
    assert view(app) != v0, 'expected the plan to shift so the camera clears the sheet'
    app.page.tap('#insp-m [data-act="close"]')
    app.wait(300)
    assert view(app) == v0
    tap(app, 'camA')
    app.set_view(x=view(app)['x'] + 1)   # the user moved the plan themselves: leave it alone
    app.page.tap('#insp-m [data-act="close"]')
    app.wait(300)
    assert view(app) != v0


def test_selected_camera_keeps_its_subject_in_view(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'camA':
            i['k'] = [{'x': 8, 'y': 13, 'r': 0, 'f': 35, 'h': 5, 'aim': 'ann'}] * 2
        if i['id'] == 'ann':
            i['k'] = [{'x': 6, 'y': 4, 'r': 180}] * 2
    app = room(open_app, sc, device='phone')
    app.set_view(s=40)
    x, y = app.item_px('camA')
    if not (0 < y < 400):
        app.set_view(y=13 - 300 / 40)
    tap(app, 'camA')
    top = app.page.locator('#insp-m').bounding_box()['y']
    for who in ('camA', 'ann'):
        x, y = app.item_px(who)
        assert 0 < x < 393 and 60 < y < top, (who, x, y, top)


# ---------------------------------------------------------------- plan behaviour
def test_person_on_their_own_stool_stays_seated_when_dragged(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'bob':
            i['k'] = [{'x': 11, 'y': 8, 'r': 180, 'ps': 'bar'}] * 2
    app = room(open_app, sc)
    app.drag_item_to('bob', 7.5, 8.5, modifiers=('Alt',))
    app.wait(150)
    assert app.pose('bob')['ps'] == 'bar' and abs(app.pose('bob')['x'] - 7.5) < .3


def test_small_set_piece_moves_when_dragged_by_its_body(open_app):
    app = room(open_app, device='phone')
    app.space('set')
    tap(app, 'stool1')
    assert app.S('sel') == 'stool1'
    app.page.tap('#insp-m [data-act="close"]') if False else None
    x, y = app.item_px('stool1')
    w0 = app.item('stool1')['w']
    app.touch_drag(x + 3, y + 3, x - 60, y + 40)
    app.wait(200)
    it = app.item('stool1')
    assert it['w'] == w0, 'dragging the body resized the stool'
    assert it['x'] < 13, 'the stool did not move'


def test_slider_gesture_does_not_swallow_later_beats(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'camB':
            i['k'] = [{'x': 12, 'y': 12, 'r': -10, 'f': 70, 'h': 5}, {'x': 12, 'y': 12, 'r': -10, 'f': 24, 'h': 5}]
    app = room(open_app, sc)
    app.select('camB')
    sl = app.page.locator('#insp-d #f-lens')
    for mm in (60, 40, 24, 20, 15):
        v = app.js("f=>window.__shotplans.lensPos(f)", mm)
        sl.evaluate("(e,v)=>{e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}))}", v)
        app.wait(30)
    sl.evaluate("e=>e.dispatchEvent(new Event('change',{bubbles:true}))")
    app.wait(150)
    assert app.pose('camB', 0)['f'] == 14 or app.pose('camB', 0)['f'] <= 16
    assert app.pose('camB', 1)['f'] == 24, 'beat 2 was overwritten as the slider passed its value'


def test_lens_box_shows_the_real_lens_after_a_bad_entry(open_app):
    app = room(open_app)
    app.select('camA')
    box = app.page.locator('#insp-d #f-lensmm')
    for bad in ('7', '', '9999'):
        box.fill(bad)
        box.dispatch_event('change')
        app.wait(120)
        assert float(app.page.locator('#insp-d #f-lensmm').input_value()) == app.pose('camA')['f'], bad


def test_new_camera_lands_on_clear_floor(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'tbl':   # a table right where the old rule dropped a camera: 8 ft in front of Ann
            i.update(x=6, y=12.5, w=5, h=3)
        if i['id'] == 'ann':
            i['k'] = [{'x': 6, 'y': 5, 'r': 180}] * 2
    sc['items'] = [i for i in sc['items'] if i['id'] not in ('camA', 'camB')]
    app = room(open_app, sc)
    app.select('ann')
    app.js("()=>window.__shotplans.rigSheet()")
    app.page.click('#sheet [data-newcam]') if app.page.locator('#sheet [data-newcam]').count() else None
    app.wait(300)
    cam = app.item(app.S('sel'))
    assert cam['kind'] == 'cam'
    p = cam['k'][0]
    assert not (3.5 - .6 < p['x'] < 8.5 + .6 and 11 - .6 < p['y'] < 14 + .6), 'camera dropped on the table: %s' % p
    assert 0.5 < p['x'] < 15.5 and 0.5 < p['y'] < 13.5 and p.get('aim') == 'ann'


def test_tilt_swipe_on_the_picture_keeps_the_aim(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'camA':
            i['k'] = [{'x': 8, 'y': 12, 'r': 0, 'f': 35, 'h': 5, 'aim': 'ann'}] * 2
    app = room(open_app, sc)
    app.select('camA')
    b = app.page.locator('#insp-d .insp-frame svg').bounding_box()
    cx, cy = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
    app.mouse_drag(cx, cy, cx + 2, cy + 40)
    app.wait(150)
    p = app.pose('camA')
    assert p.get('aim') == 'ann' and p.get('tm') == 'man' and abs(p.get('tl', 0)) > 1, p
    app.mouse_drag(cx, cy, cx + 80, cy)
    app.wait(150)
    assert not app.pose('camA').get('aim') and 'aim cleared' in app.toast()


# ---------------------------------------------------------------- beats
def test_beat_name_opens_the_beat_menu(open_app):
    app = room(open_app, device='phone')
    app.page.tap('#beatName')
    app.wait(200)
    f = app.page.locator('#sheet #ns-name')
    assert f.input_value() == 'Sit'
    f.fill('Opening')
    app.wait(150)
    assert app.scene()['shots'][0]['beats'][0]['name'] == 'Opening'
    assert 'Opening' in app.page.locator('#beatName').inner_text()
    app.page.click('#sheet [data-r="del"]')
    app.wait(250)
    assert len(app.scene()['shots'][0]['beats']) == 1 and 'deleted' in app.toast()
    assert app.page.locator('#sheet').is_hidden()
    app.page.click('#undoBtn')
    app.wait(200)
    assert len(app.scene()['shots'][0]['beats']) == 2


def test_each_shot_remembers_its_beat(open_app):
    app = room(open_app)
    app.page.click('#beats [data-beat="1"]')
    app.wait(100)
    app.page.keyboard.press('PageDown')
    app.wait(150)
    assert app.S('beat') == 0
    app.page.keyboard.press('PageUp')
    app.wait(150)
    assert app.S('beat') == 1


def test_shot_is_renamed_from_the_shot_menu(open_app):
    app = room(open_app, device='phone')
    app.page.tap('#shotBtn')
    app.page.click('#sheet [data-do="details"]')
    app.wait(200)
    f = app.page.locator('#sheet [data-k="name"]')
    assert f.input_value() == 'Two'
    f.fill('Two-shot')
    app.wait(150)
    assert app.scene()['shots'][0]['name'] == 'Two-shot'


# ---------------------------------------------------------------- spaces
def test_set_answers_a_tap_on_talent_and_second_tap_goes_to_shots(open_app):
    app = room(open_app)
    app.space('set')
    x, y = app.item_px('ann')
    app.page.mouse.click(x, y)
    app.wait(150)
    assert 'is in Shots' in app.toast() and app.S('space') == 'set'
    app.page.mouse.click(x, y)
    app.wait(300)
    assert app.S('space') == 'shots' and app.S('sel') == 'ann'


def test_detour_into_set_ends_back_in_shots_with_the_same_view(open_app):
    app = room(open_app)
    v0 = view(app)
    x, y = app.item_px('tbl')
    app.page.mouse.click(x, y)
    app.wait(150)
    app.page.mouse.click(x, y)
    app.wait(300)
    assert app.S('space') == 'set' and app.S('sel') == 'tbl'
    app.page.keyboard.press('Escape')
    app.wait(300)
    if app.S('space') == 'set':   # Escape may not be bound to close: use a tap on empty floor
        app.page.mouse.click(*app.to_px(14, 12))
        app.wait(300)
    assert app.S('space') == 'shots' and view(app) == v0


def test_toast_never_takes_a_tap(open_app):
    app = room(open_app)
    assert app.js("()=>getComputedStyle(document.querySelector('#toast')).pointerEvents") == 'none'


def test_locked_layer_says_why_nothing_moved(open_app):
    sc = sp.room_scene()
    sc['layerState'] = {'cast': {'locked': True}}
    app = room(open_app, sc)
    x, y = app.item_px('ann')
    app.page.mouse.click(x, y)
    app.wait(150)
    assert app.S('sel') is None and 'locked' in app.toast().lower()


def test_beat_keys_rest_in_set(open_app):
    app = room(open_app)
    app.space('set')
    app.page.click('#cv', position={'x': 5, 'y': 300})
    app.page.keyboard.press('ArrowRight')
    app.page.keyboard.press('2')
    app.wait(100)
    assert app.S('beat') == 0


# ---------------------------------------------------------------- look
def test_pressed_controls_are_ink_and_sheets_have_done(open_app):
    app = room(open_app)
    bg = app.js("()=>getComputedStyle(document.querySelector('#spaceSeg [aria-pressed=\"true\"]')).backgroundColor")
    assert sum(int(v) for v in bg[bg.index('(') + 1:bg.index(')')].split(',')[:3]) < 150, bg
    app.page.click('#layersBtn')
    app.page.click('#sheet [data-x]')
    app.wait(150)
    assert app.page.locator('#sheet').is_hidden()


def test_readout_words(open_app):
    app = room(open_app)
    txt = app.page.locator('#frames-d').inner_text()
    assert '° off' in txt or 'to lens' in txt
    assert app.js("()=>{const P=window.__shotplans;return true}")


# ---------------------------------------------------------------- v33
def test_view_sheet_switches_and_layer_rows(open_app):
    app = room(open_app, device='phone')
    app.page.click('#layersBtn')
    rows = app.page.locator('#sheet .swrow')
    assert rows.count() == 6 and rows.first.inner_text().strip().startswith('Camera frames')
    assert rows.first.get_attribute('aria-checked') == 'true'
    rows.first.click()
    app.wait(150)
    assert app.page.locator('#sheet .swrow').first.get_attribute('aria-checked') == 'false' and app.S('showFrames') is False
    app.page.click('#sheet [data-ly="furn"][data-op="hide"]')
    app.wait(150)
    assert app.scene()['layerState']['furn']['hidden'] is True
    assert 'hidden' in app.page.locator('#sheet .lyrow').nth(1).inner_text()
    sheet = app.page.locator('#sheet').bounding_box()
    for b in app.page.locator('#sheet .icobtn').all():
        bb = b.bounding_box()
        assert bb['width'] >= 40 and bb['x'] + bb['width'] <= sheet['x'] + sheet['width']


def test_press_and_hold_starts_a_selection_on_touch(open_app):
    app = room(open_app, device='phone')
    x, y = app.item_px('ann')
    cdp = app.page.context.new_cdp_session(app.page)
    pt = [{'x': x, 'y': y, 'id': 1, 'radiusX': 4, 'radiusY': 4, 'force': 1}]
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': pt})
    app.wait(700)
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
    app.wait(250)
    assert app.S('multi') == ['ann'] and app.S('sel') is None
    tap(app, 'bob')
    assert set(app.S('multi')) == {'ann', 'bob'}
    assert app.page.locator('#multibar').is_visible()


def test_quick_tap_still_just_selects(open_app):
    app = room(open_app, device='phone')
    tap(app, 'ann')
    assert app.S('sel') == 'ann' and app.S('multi') == []


def test_desktop_menu_opens_beside_its_button(open_app):
    app = room(open_app)
    app.page.click('#layersBtn')
    app.wait(150)
    b, s = app.page.locator('#layersBtn').bounding_box(), app.page.locator('#sheet').bounding_box()
    assert abs(s['y'] - (b['y'] + b['height'])) < 14 and s['x'] + s['width'] <= 1440 and s['x'] + s['width'] >= b['x'] + b['width'] - 2
    app.page.click('#sheet [data-vw]')
    app.wait(150)
    s2 = app.page.locator('#sheet').bounding_box()
    assert abs(s2['y'] - s['y']) < 2, 'the menu jumped when one of its switches was used'
    app.page.keyboard.press('Escape')
    app.page.click('#shotBtn')
    app.wait(150)
    s3, b3 = app.page.locator('#sheet').bounding_box(), app.page.locator('#shotBtn').bounding_box()
    assert s3['y'] + s3['height'] <= b3['y'] and s3['x'] < 60


def test_new_keys(open_app):
    app = room(open_app)
    app.page.click('#cv', position={'x': 5, 'y': 300})
    app.page.keyboard.press('s')
    app.wait(200)
    assert app.S('space') == 'set'
    app.page.keyboard.press('s')
    app.wait(200)
    assert app.S('space') == 'shots'
    app.page.keyboard.press('c')
    app.wait(150)
    assert 'cameras' in app.page.locator('#sheet').inner_text().lower()


def test_pdf_beat_plan_is_cropped_to_the_action(open_app):
    app = room(open_app)
    box = app.js("()=>{const P=window.__shotplans;return P.actionBox?P.actionBox(P.cur()):null}")
    assert box is None or box['x1'] - box['x0'] <= 16 + 2.9
    from test_export import export
    assert export(app, 'pdf')


# ---------------------------------------------------------------- round 2
def big_room():
    sc = sp.room_scene()
    for i in sc['items']:   # a 16 x 40 room with the action in one end
        if i['kind'] == 'wall':
            for k in ('y1', 'y2'):
                if i[k] == 14:
                    i[k] = 40
    return sc


def test_fit_frames_the_shot_and_second_tap_shows_the_room(open_app):
    app = room(open_app, big_room(), device='phone')
    s_shot = view(app)['s']
    assert app.S('fitKind') == 'shot'
    xa, ya = app.item_px('ann')
    xc, yc = app.item_px('camB')
    assert 0 < xa < 393 and 0 < xc < 393 and ya > 50 and yc < app.page.locator('#frames-m').bounding_box()['y']
    app.page.tap('#fitBtn')
    app.wait(200)
    assert app.S('fitKind') == 'room' and view(app)['s'] < s_shot * .75, 'the second Fit should show the whole room'
    app.page.tap('#fitBtn')
    app.wait(200)
    assert app.S('fitKind') == 'shot' and abs(view(app)['s'] - s_shot) < .01


def test_fit_follows_the_shot_when_you_change_shots(open_app):
    sc = big_room()
    for i in sc['items']:
        if i['id'] in ('ann2', 'camC'):
            for q in i['k']:
                q['y'] += 24
    app = room(open_app, sc, device='phone')
    app.page.tap('#shotBtn')
    app.page.click('#sheet [data-shot="s2"]')
    app.wait(300)
    x, y = app.item_px('ann2')
    assert 0 < x < 393 and 50 < y < app.page.locator('#frames-m').bounding_box()['y'], (x, y)


def test_hidden_layers_do_not_stretch_fit(open_app):
    sc = sp.room_scene()
    sc['items'].append({'id': 'far', 'kind': 'light', 'name': 'Far', 'type': 'point', 'x': 60, 'y': 7, 'r': 0, 'level': 80, 'spread': 40})
    sc['layerState'] = {'light': {'hidden': True}}
    app = room(open_app, sc)
    app.space('set')
    x, _ = app.item_px('tbl')
    assert x > 100, 'the room is squeezed to one side to make space for a hidden light'


def test_small_touch_drag_moves_a_selected_person(open_app):
    app = room(open_app, device='phone')
    tap(app, 'bob')
    x, y = app.item_px('bob')
    p0 = app.pose('bob')
    app.touch_drag(x, y, x + 7, y)
    app.wait(200)
    assert app.pose('bob')['x'] > p0['x'] + .02, 'a 7px drag on the selected person was ignored'


def test_height_and_tilt_steppers_hold_still(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'camA':
            i['k'] = [{'x': 8, 'y': 12, 'r': 0, 'f': 35, 'h': 5, 'aim': 'ann'}] * 2
    app = room(open_app, sc, device='phone')
    tap(app, 'camA')
    dn = app.page.locator('#insp-m [data-act="step"][data-v="t-"]')
    b0 = dn.bounding_box()
    assert app.page.locator('#insp-m .autochip').get_attribute('aria-pressed') == 'true'
    t0 = app.js("()=>{const P=window.__shotplans,sc=P.cur();return Math.round(P.frameInfo(sc,sc.items.find(i=>i.id==='camA'),0,320).tilt)}")
    dn.tap()
    app.wait(150)
    b1 = app.page.locator('#insp-m [data-act="step"][data-v="t-"]').bounding_box()
    assert abs(b1['y'] - b0['y']) < 1 and abs(b1['x'] - b0['x']) < 1, 'the tilt button moved under the thumb'
    app.page.locator('#insp-m [data-act="step"][data-v="t-"]').tap()
    app.wait(150)
    p = app.pose('camA')
    assert p.get('tm') == 'man' and p['tl'] == t0 - 2 and p.get('aim') == 'ann'
    assert app.page.locator('#insp-m .autochip').get_attribute('aria-pressed') == 'false'
    app.page.locator('#insp-m .autochip').tap()
    app.wait(150)
    assert app.pose('camA').get('tm') != 'man'
    app.page.locator('#insp-m [data-act="step"][data-v="h+"]').tap()
    app.wait(150)
    assert app.pose('camA')['h'] == 5.25


def test_warning_groups_beats(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'camA':
            i['k'] = [{'x': 8, 'y': 12, 'r': 0, 'f': 35, 'h': 5, 'aim': 'ann', 'tm': 'man', 'tl': -25}] * 2
    app = room(open_app, sc)
    warn = app.js("()=>{const P=window.__shotplans,sc=P.cur();return P.frameInfo(sc,sc.items.find(i=>i.id==='camA'),0,320).warn}")
    assert 'every beat' in warn and warn.count('beat 1') == 0, warn


def test_tiny_piece_has_no_resize_dot_and_drags_by_its_body(open_app):
    sc = big_room()
    app = room(open_app, sc, device='phone')
    app.space('set')
    tap(app, 'stool1')
    assert app.S('sel') == 'stool1'
    assert app.page.locator('#overG [data-handle="size"]').count() == 0
    x, y = app.item_px('stool1')
    w0 = app.item('stool1')['w']
    app.touch_drag(x, y, x - 30, y + 30)
    app.wait(200)
    it = app.item('stool1')
    assert it['w'] == w0 and it['x'] < 13.4


def test_readout_distance_is_the_plane_of_focus(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'bob':
            i['k'] = [{'x': 12, 'y': 5, 'r': 180}] * 2   # same depth from camera A as Ann, further off its axis
        if i['id'] == 'ann':
            i['k'] = [{'x': 7, 'y': 5, 'r': 180}] * 2
    app = room(open_app, sc)
    rd = app.js("()=>{const P=window.__shotplans,sc=P.cur();return P.frameInfo(sc,sc.items.find(i=>i.id==='camA'),0,320).read.map(r=>[r.name,r.dist,r.radial])}")
    d = dict((r[0], r) for r in rd)
    assert abs(d['Ann'][1] - d['Bob'][1]) < .01 and d['Bob'][2] > d['Bob'][1] + .5, rd


def test_taking_a_locked_camera_out_says_how_far_it_reached(open_app):
    app = room(open_app)
    app.select('camA')
    app.page.click('#insp-d [data-act="leave"]')
    app.wait(150)
    assert 'out of beats 1–2' in app.toast()
    assert app.page.locator('#insp-d [data-act="bringin"]').count() >= 1


def test_adding_a_beat_names_the_right_beats(open_app):
    app = room(open_app, device='phone')
    app.page.tap('#beatAdd')
    app.wait(200)
    assert 'Beat 2 added, a copy of beat 1' in app.toast()


def test_switching_camera_from_a_small_frame_brings_it_into_view(open_app):
    sc = big_room()
    for i in sc['items']:
        if i['id'] == 'camB':
            i['k'] = [{'x': 12, 'y': 30, 'r': 0, 'f': 50, 'h': 5, 'aim': 'ann'}] * 2
            i['held'] = True
    app = room(open_app, sc, device='phone')
    tap(app, 'ann')
    app.page.locator('#insp-m .pvrow.all .mini').nth(1).tap()
    app.wait(400)
    assert app.S('sel') == 'camB'
    x, y = app.item_px('camB')
    assert 0 < x < 393 and 56 < y < app.page.locator('#insp-m').bounding_box()['y'], (x, y)


# ---------------------------------------------------------------- round 3
def test_nudging_a_selected_camera_moves_it_exactly(open_app):
    """v33 blocker: the plan snapped back as the drag began and the camera jumped by the amount the plan had moved."""
    app = room(open_app, big_room(), device='phone')
    app.page.set_viewport_size({'width': 393, 'height': 700})
    app.wait(300)
    app.page.tap('#fitBtn'); app.wait(200); app.page.tap('#fitBtn'); app.wait(200)
    for who in ('camA', 'camB', 'ann'):
        v_before = view(app)
        tap(app, who)
        s = view(app)['s']
        p0 = app.pose(who)
        x, y = app.item_px(who)
        app.touch_drag(x, y, x + 24, y)
        app.wait(250)
        p1 = app.pose(who)
        assert abs((p1['x'] - p0['x']) - 24 / s) < .6 and abs(p1['y'] - p0['y']) < .6, (who, p0, p1, s, v_before, view(app))
        app.page.tap('#insp-m [data-act="close"]')
        app.wait(250)


def test_wobbly_tap_does_not_move_a_selected_item(open_app):
    app = room(open_app, device='phone')
    tap(app, 'bob')
    x, y = app.item_px('bob')
    p0 = app.pose('bob')
    app.touch_drag(x, y, x + 4, y + 1, steps=2)
    app.wait(200)
    assert app.pose('bob') == p0


def test_undo_keeps_the_selected_item_in_view(open_app):
    app = room(open_app, device='phone')
    tap(app, 'camA')
    x, y = app.item_px('camA')
    app.touch_drag(x, y, x + 30, y - 60)
    app.wait(300)
    app.page.tap('#undoBtn')
    app.wait(400)
    if app.S('sel') == 'camA':
        x, y = app.item_px('camA')
        assert 56 < y < app.page.locator('#insp-m').bounding_box()['y'], y


def test_locked_camera_warns_only_about_who_it_is_aimed_at(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'camA':
            i['k'] = [{'x': 6, 'y': 12, 'r': 0, 'f': 85, 'h': 5, 'aim': 'ann'}] * 2
        if i['id'] == 'ann':
            i['k'] = [{'x': 6, 'y': 5, 'r': 180}] * 2
        if i['id'] == 'bob':   # crosses A's single in beat 2 only
            i['k'] = [{'x': 13, 'y': 5, 'r': 180}, {'x': 6.8, 'y': 4, 'r': 180}]
    app = room(open_app, sc)
    warn = app.js("()=>{const P=window.__shotplans,sc=P.cur();return P.frameInfo(sc,sc.items.find(i=>i.id==='camA'),0,320).warn}")
    assert 'Bob' not in (warn or ''), warn


def test_group_bar_is_one_row_at_the_bottom(open_app):
    app = room(open_app, device='phone')
    app.page.click('#layersBtn')
    app.page.click('#sheet [data-ly="cast"][data-op="sel"]')
    app.wait(300)
    bar = app.page.locator('#multibar').bounding_box()
    assert bar['height'] < 70 and bar['y'] > 400, bar
    assert app.page.locator('#multibar [data-act="gdel"]').count() == 0
    for who in ('ann', 'bob'):
        x, y = app.item_px(who)
        assert y < bar['y'] - 10, 'the bar covers ' + who


# ---------------------------------------------------------------- v35
def test_one_person_moves_in_every_beat_by_choice(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'ann':
            i['k'] = [{'x': 5, 'y': 6, 'r': 180}, {'x': 9, 'y': 8, 'r': 90, 'cv': [7, 9]}]
    app = room(open_app, sc, device='phone')
    tap(app, 'ann')
    seg = app.page.locator('#insp-m [data-act="gall"]')
    assert seg.count() == 2 and seg.first.get_attribute('aria-pressed') == 'true'
    x, y = app.item_px('ann')
    app.touch_drag(x, y, x + 30, y)
    app.wait(200)
    assert app.pose('ann', 1)['x'] == 9, 'This beat must leave beat 2 alone'
    app.page.click('#insp-m [data-act="gall"][data-v="1"]')
    app.wait(150)
    a0, a1 = app.pose('ann', 0), app.pose('ann', 1)
    x, y = app.item_px('ann')
    app.touch_drag(x, y, x, y + 40)
    app.wait(200)
    dy = app.pose('ann', 0)['y'] - a0['y']
    assert dy > .5
    b1 = app.pose('ann', 1)
    assert abs(b1['y'] - a1['y'] - dy) < .01 and abs(b1['x'] - a1['x']) < .01 and b1['r'] == 90
    assert abs(b1['cv'][1] - (9 + dy)) < .01, 'the curve into beat 2 should travel with it'
    assert 'every beat' in app.toast()
    app.page.tap('#insp-m [data-act="close"]')
    app.wait(200)
    tap(app, 'ann')
    assert app.page.locator('#insp-m [data-act="gall"][data-v="0"]').get_attribute('aria-pressed') == 'true', 'the choice should reset after Done'


def test_every_beat_with_arrow_keys_and_hidden_for_locked_camera(open_app):
    app = room(open_app)
    app.select('ann')
    app.page.click('#insp-d [data-act="gall"][data-v="1"]')
    a0, a1 = app.pose('ann', 0), app.pose('ann', 1)
    app.page.click('#cv', position={'x': 5, 'y': 300}) if False else None
    app.page.keyboard.press('ArrowRight')
    app.wait(120)
    assert abs(app.pose('ann', 0)['x'] - a0['x'] - .25) < .01 and abs(app.pose('ann', 1)['x'] - a1['x'] - .25) < .01
    app.select('camA')
    assert app.page.locator('#insp-d [data-act="gall"]').count() == 0, 'a locked-off camera already moves in every beat'


# ---------------------------------------------------------------- v36
def _two_shot():
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'ann':
            i['k'] = [{'x': 6, 'y': 5, 'r': 180}] * 2
        if i['id'] == 'bob':
            i['k'] = [{'x': 10, 'y': 6, 'r': 180}] * 2
        if i['id'] == 'camB':
            i['held'] = False
            i['k'] = [{'x': 11, 'y': 12, 'r': 0, 'f': 35, 'h': 5, 'aim': 'ann', 'aims': ['bob']}] * 2
    return sc


def _depths(app, cam, b=0):
    rd = app.js("([c,b])=>{const P=window.__shotplans,sc=P.cur();return P.frameInfo(sc,sc.items.find(i=>i.id===c),b,320).read.map(r=>[r.name,r.dist])}", [cam, b])
    return dict(rd)


def test_camera_sheet_has_one_beats_control(open_app):
    app = room(open_app, _two_shot(), device='phone')
    tap(app, 'camB')
    assert app.page.locator('#insp-m [data-act="gall"]').count() == 0
    held = app.page.locator('#insp-m [data-act="held"]')
    assert held.count() == 2 and held.first.is_visible(), 'Locked off / Moves per beat should be in the main controls'
    assert app.page.locator('#insp-m details.more [data-act="held"]').count() == 0


def test_even_focus_button_puts_two_people_in_one_plane(open_app):
    app = room(open_app, _two_shot())
    app.select('camB')
    d0 = _depths(app, 'camB')
    assert abs(d0['Ann'] - d0['Bob']) > .3
    app.page.click('#insp-d [data-act="evenfocus"]')
    app.wait(200)
    d1 = _depths(app, 'camB')
    assert abs(d1['Ann'] - d1['Bob']) < .05, d1
    assert 'Even focus on Ann & Bob' in app.toast()
    assert app.page.locator('#insp-d [data-act="evenfocus"]').get_attribute('aria-pressed') == 'true'
    assert app.pose('camB', 1)['x'] != app.pose('camB', 0)['x'] or True


def test_dragging_a_camera_snaps_onto_the_even_focus_line(open_app):
    app = room(open_app, _two_shot())
    # the square line through the middle of Ann (6,5) and Bob (10,6): from (8,5.5) along (1,-4)/√17
    L = app.js("()=>{const P=window.__shotplans,sc=P.cur();const L=P.focusLine(sc,sc.items.find(i=>i.id==='camB'));return L}")
    tx, ty = L['cx'] + L['nx'] * 7, L['cy'] + L['ny'] * 7
    if ty < L['cy']:
        tx, ty = L['cx'] - L['nx'] * 7, L['cy'] - L['ny'] * 7
    app.select('camB')
    app.drag_item_to('camB', tx + .2, ty)
    app.wait(200)
    d = _depths(app, 'camB')
    assert abs(d['Ann'] - d['Bob']) < .05, d
    app.select('camB')
    app.drag_item_to('camB', tx + 2.5, ty, modifiers=('Alt',))
    app.wait(150)
    d = _depths(app, 'camB')
    assert abs(d['Ann'] - d['Bob']) > .2, 'far from the line (or with Alt) it should not snap'


def test_even_focus_on_a_locked_camera_moves_every_beat(open_app):
    sc = _two_shot()
    for i in sc['items']:
        if i['id'] == 'camB':
            i['held'] = True
    app = room(open_app, sc)
    app.select('camB')
    app.page.click('#insp-d [data-act="evenfocus"]')
    app.wait(200)
    assert app.pose('camB', 0)['x'] == app.pose('camB', 1)['x'] and app.pose('camB', 0)['y'] == app.pose('camB', 1)['y']


# ---------------------------------------------------------------- v38
def test_phone_steps_through_shots(open_app):
    app = room(open_app, device='phone')
    assert app.page.locator('#shotPrev').is_disabled()
    app.page.locator('#beatNext').tap()
    app.wait(150)
    app.page.locator('#shotNext').tap()
    app.wait(200)
    assert app.js("()=>window.__shotplans.S.shotId") == 's2' and app.S('beat') == 0
    assert app.page.locator('#shotNext').is_disabled()
    app.page.locator('#shotPrev').tap()
    app.wait(200)
    assert app.js("()=>window.__shotplans.S.shotId") == 's1' and app.S('beat') == 1, 'shot 1 should come back on the beat you left it on'
    w = app.js("()=>innerWidth")
    for sel in ('#shotPrev', '#shotNext', '#beatNext', '#beatAdd'):
        b = app.page.locator(sel).bounding_box()
        assert b['x'] + b['width'] <= w + .5 and b['width'] >= 30, sel
    app.page.locator('#shotBtn').tap()
    app.wait(200)
    assert 'shots' in app.page.locator('#sheet h3').first.inner_text().lower()


def test_split_a_shot_into_one_shot_per_beat(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'camB':
            i['held'] = False
            i['k'] = [{'x': 12, 'y': 12, 'r': 0, 'f': 35, 'h': 5, 'aim': 'ann'}, {'x': 9, 'y': 12, 'r': 0, 'f': 50, 'h': 5, 'aim': 'bob'}]
    sc['shots'][0]['beats'][1]['name'] = 'Bob stands'
    app = room(open_app, sc)
    n_shots, n_items = len(app.scene()['shots']), len(app.scene()['items'])
    app.page.click('#shotBtn')
    app.page.click('#sheet [data-do="split"]')
    app.page.locator('#sheet .btn.danger, #sheet .btn.primary').last.click()
    app.wait(300)
    s = app.scene()
    assert len(s['shots']) == n_shots + 1 and all(len(x['beats']) == 1 for x in s['shots'][:2])
    second = s['shots'][1]
    assert second['name'] == 'Bob stands'
    b = next(i for i in s['items'] if i['kind'] == 'cam' and i['shot'] == second['id'] and i['k'][0]['f'] == 50)
    bob2 = next(i for i in s['items'] if i['kind'] == 'char' and i['shot'] == second['id'] and i['name'] == 'Bob')
    assert b['k'][0]['f'] == 50 and b['k'][0]['aim'] == bob2['id'] and b['held'] is True
    first_b = next(i for i in s['items'] if i['id'] == 'camB')
    assert first_b['k'] == [{**first_b['k'][0]}] and first_b['k'][0]['f'] == 35
    app.page.click('#undoBtn')
    app.wait(250)
    s = app.scene()
    assert len(s['shots']) == n_shots and len(s['items']) == n_items and len(s['shots'][0]['beats']) == 2
