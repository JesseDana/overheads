"""Plan interactions: centre-grab drag, Fit vs phone panels, snap to the neighbouring beat, seats, box select,
hidden-layer chip and adding into a hidden layer."""
import pytest
import sp


def room(open_app, device='desktop', mutate=None):
    sc = sp.room_scene()
    if mutate:
        mutate(sc)
    app = open_app({'room': sc}, device=device)
    app.go(shot='s1')
    return app


# ---------------------------------------------------------------- centre grab
def test_centre_grab_drags_person_not_plan(open_app):
    app = room(open_app)
    app.select('bob')  # selection draws overlay lines/labels over the figure
    x, y = app.item_px('bob')
    top = app.js("([x,y])=>{const e=document.elementFromPoint(x,y);return !!(e&&e.closest('#worldG [data-id],[data-handle]'))}", [x, y])
    assert top, 'the centre of a selected figure is covered by something that is not the figure'
    v0 = app.S('view')
    tx, ty = app.to_px(13, 7)
    app.mouse_drag(x, y, tx, ty)
    p = app.pose('bob')
    assert (round(p['x'], 2), round(p['y'], 2)) == (13, 7), 'centre grab did not move the person: %s' % p
    assert app.S('view') == v0, 'centre grab panned the plan'


@pytest.mark.parametrize('kind_id', ['camA', 'key', 'tbl'])
def test_centre_grab_other_items(open_app, kind_id):
    app = room(open_app)
    if kind_id == 'tbl':
        app.space('set')
    app.select(kind_id)
    x, y = app.item_px(kind_id)
    v0 = app.S('view')
    s = v0['s']
    app.mouse_drag(x, y, x + 2 * s, y)
    assert app.S('view') == v0, 'dragging the selected %s panned the plan' % kind_id
    it = app.item(kind_id)
    nx = it['k'][0]['x'] if 'k' in it else it['x']
    assert nx > (8 if kind_id == 'camA' else 3) + 1.5, '%s did not move' % kind_id


# ---------------------------------------------------------------- Fit
def _items_bottom_px(app):
    return app.js("""()=>{const P=window.__shotplans,sc=P.cur(),S=P.S,r=document.querySelector('#cv').getBoundingClientRect();let y=-1e9;
      for(const it of P.inShot(sc)){let ys=[];if(it.kind==='wall')ys=[it.y1,it.y2];else if(it.k)ys=it.k.map(q=>q.y);else if(it.y!=null)ys=[it.y];
        for(const v of ys)y=Math.max(y,r.top+(v-S.view.y)*S.view.s)}return y}""")


def test_fit_clears_phone_frames_strip(open_app):
    app = room(open_app, 'phone')
    app.page.click('#fitBtn')
    app.wait(150)
    top = app.js("()=>{const e=document.querySelector('#frames-m');return e&&!e.hidden&&e.offsetParent?e.getBoundingClientRect().top:null}")
    assert top is not None, 'frames strip not shown on phone'
    assert _items_bottom_px(app) <= top + 1, 'Fit puts part of the plan under the frames strip'


def test_fit_clears_phone_edit_sheet(open_app):
    app = room(open_app, 'phone')
    x, y = app.item_px('bob')
    app.page.touchscreen.tap(x, y)
    app.wait(400)
    app.page.click('#fitBtn')
    app.wait(150)
    top = app.js("()=>{const e=document.querySelector('#insp-m');return !e.hidden?e.getBoundingClientRect().top:null}")
    assert top is not None
    assert _items_bottom_px(app) <= top + 1, 'Fit puts part of the plan under the edit sheet'


# ---------------------------------------------------------------- snap to neighbouring beat
def test_drag_near_other_beat_snaps_to_it(open_app):
    app = room(open_app)
    app.go(shot='s1', beat=1)
    app.drag_item_to('ann', 6.3, 5.2)  # Ann is at (6,5) in beat 1, (9,5) in beat 2
    p = app.item('ann')['k'][1]
    assert (p['x'], p['y']) == (6, 5), 'a drag ending 4 in from beat 1 left a tiny track: %s' % p


def test_alt_drag_skips_beat_snap(open_app):
    app = room(open_app)
    app.go(shot='s1', beat=1)
    app.drag_item_to('ann', 6.3, 5.2, modifiers=('Alt',))
    p = app.item('ann')['k'][1]
    assert (p['x'], p['y']) != (6, 5)


def test_moving_camera_snaps_but_locked_camera_moves_everywhere(open_app):
    app = room(open_app)
    app.go(shot='s1', beat=1)
    app.drag_item_to('camB', 12.2, 11.8)  # beat 1 spot is (12,12)
    k = app.item('camB')['k']
    assert (k[1]['x'], k[1]['y']) == (12, 12)
    app.drag_item_to('camA', 6, 12)
    k = app.item('camA')['k']
    assert all((q['x'], q['y']) == (6, 12) for q in k), 'locked-off camera moved in one beat only: %s' % k


# ---------------------------------------------------------------- seats
def test_drop_on_bar_stool_sits_on_bar(open_app):
    app = room(open_app)
    app.drag_item_to('bob', 13.5, 3)
    p = app.item('bob')['k'][0]
    assert p.get('ps') == 'bar', p
    assert (p['x'], p['y']) == (13.5, 3)
    assert 'bar stool' in app.toast().lower()


def test_drop_on_sofa_keeps_spot_along_it(open_app):
    app = room(open_app)
    app.drag_item_to('bob', 6, 2)  # sofa centred at x=4, 7 ft wide
    p = app.item('bob')['k'][0]
    assert p.get('ps') == 'chair', p
    assert abs(p['x'] - 6) < .3, 'person snapped to the sofa centre instead of keeping their spot: %s' % p


def test_lift_off_seat_stands(open_app):
    app = room(open_app)
    app.drag_item_to('bob', 13.5, 3)
    app.drag_item_to('bob', 11, 8)
    assert (app.item('bob')['k'][0].get('ps') or 'stand') == 'stand'


def test_seat_posture_reused_from_other_beat(open_app):
    def m(sc):
        bob = next(i for i in sc['items'] if i['id'] == 'bob')
        bob['k'] = [{'x': 13.5, 'y': 3, 'r': 180, 'ps': 'chair'}, {'x': 11, 'y': 5, 'r': 180}]  # sat "chair" on the bar stool
    app = room(open_app, mutate=m)
    app.go(shot='s1', beat=1)
    app.drag_item_to('bob', 13.5, 3)
    assert app.item('bob')['k'][1].get('ps') == 'chair', 'posture on the same seat in beat 1 was not reused'


# ---------------------------------------------------------------- box select
def test_shift_drag_box_selects(open_app):
    app = room(open_app)
    x0, y0 = app.to_px(5, 4)
    x1, y1 = app.to_px(12.5, 6)
    app.mouse_drag(x0, y0, x1, y1, modifiers=('Shift',))
    assert sorted(app.S('multi')) == ['ann', 'bob']


def test_box_select_skips_hidden_layer(open_app):
    def m(sc):
        sc['layerState'] = {'cast': {'hidden': True}}
    app = room(open_app, mutate=m)
    x0, y0 = app.to_px(1, 1)
    x1, y1 = app.to_px(15, 13)
    app.mouse_drag(x0, y0, x1, y1, modifiers=('Shift',))
    multi = app.S('multi')
    assert multi and not ({'ann', 'bob', 'camA', 'camB'} & set(multi))


# ---------------------------------------------------------------- hidden layer chip
def test_hidden_layer_chip_names_layer_and_count(open_app):
    app = open_app()  # the owner's scene hides Lighting
    chip = app.js("()=>{const e=document.querySelector('#hidchip');return e.hidden?'':e.textContent}")
    n = sum(1 for i in sp.WS['items'] if i['kind'] in ('light', 'frame'))
    assert chip == 'Hidden: Lighting (%d)' % n


def test_adding_light_into_hidden_layer_shows_it(open_app):
    app = open_app()
    app.space('set')
    app.page.click('#tools [data-menu="light"]')
    app.page.click('#sheet [data-l="point"]')
    app.wait(150)
    sc = app.scene()
    assert not sc['layerState'].get('light', {}).get('hidden'), 'light added into a hidden layer'
    assert 'Lighting layer shown again' in app.toast()
    assert not app.js("()=>document.querySelector('#layersBtn').classList.contains('dot')")


def test_new_items_spawn_inside_room(open_app):
    app = room(open_app)
    app.set_view(x=-40, y=-40)  # look at empty space outside the room
    app.page.click('#tools [data-menu="rig"]')
    app.page.click('[data-newcam]')
    app.wait(150)
    cam = [i for i in app.scene()['items'] if i['kind'] == 'cam' and i['id'] not in ('camA', 'camB', 'camC')][0]
    assert cam['held'] is True, 'new cameras should start locked off'
    q = cam['k'][0]
    assert 0 <= q['x'] <= 16 and 0 <= q['y'] <= 14, 'new camera spawned outside the room: %s' % q


# ---------------------------------------------------------------- group move, tablet layout
def test_group_drag_of_people_is_beat_local(open_app):
    app = room(open_app)
    app.go(shot='s1', beat=1)
    x0, y0 = app.to_px(5, 4)
    x1, y1 = app.to_px(12.5, 6)
    app.mouse_drag(x0, y0, x1, y1, modifiers=('Shift',))
    assert sorted(app.S('multi')) == ['ann', 'bob']
    sx, sy = app.item_px('bob')
    s = app.S('view')['s']
    app.mouse_drag(sx, sy, sx, sy + 2 * s)
    ann, bob = app.item('ann')['k'], app.item('bob')['k']
    assert ann[1]['y'] == 7 and bob[1]['y'] == 7, 'group did not move in beat 2'
    assert ann[0]['y'] == 5 and bob[0]['y'] == 5, 'group move of people leaked into beat 1'


def test_tablet_uses_side_column(open_app):
    app = room(open_app, 'tablet')
    x, y = app.item_px('bob')
    app.page.touchscreen.tap(x, y)
    app.wait(400)
    assert app.S('sel') == 'bob'
    vis = app.js("()=>({side:!!document.querySelector('#side').offsetParent,inspD:document.querySelector('#insp-d').children.length>0,inspM:!document.querySelector('#insp-m').hidden&&!!document.querySelector('#insp-m').offsetParent})")
    assert vis['side'] and vis['inspD'] and not vis['inspM'], vis
