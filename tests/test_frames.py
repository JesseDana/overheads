"""Camera frames panel: cut words, face angle and the side of frame it turns to, BG and in-frame lists,
tapping a frame opens its camera."""
import re
import pytest
import sp

CUTS = re.compile(r'^((full body|close-up|cut at (feet|knees|thighs|waist|chest))(, head cut)?|head cut|eyes out of frame|out of frame|'
                  r'partly in frame \((left|right) edge\))$')


@pytest.fixture
def app(open_app):
    a = open_app({'room': sp.room_scene()})
    a.go(shot='s2')  # Ann at (8,5) facing camera C at (8,11), 50mm, 6 ft away
    return a


def set_pose(app, id, **kw):
    app.js("([id,kw])=>{const it=window.__shotplans.cur().items.find(i=>i.id===id);it.k.forEach(q=>Object.assign(q,kw))}", [id, kw])


def read(app, cam='camC', beat=0):
    return app.js("([c,b])=>{const P=window.__shotplans,sc=P.cur(),f=P.frameInfo(sc,sc.items.find(i=>i.id===c),b,320);return {read:f.read.map(r=>({name:r.name,cut:r.cut,off:r.off,dir:r.dir,dist:r.dist})),bg:f.bg,furn:f.furn}}", [cam, beat])


@pytest.mark.parametrize('f,expect', [(10, 'full body'), (35, None), (85, None), (135, None)])
def test_cut_words_vocabulary_and_order(app, f, expect):
    set_pose(app, 'camC', f=f)
    cut = read(app)['read'][0]['cut']
    assert CUTS.match(cut), 'unexpected cut wording %r at %smm' % (cut, f)
    if expect:
        assert cut == expect


def test_cut_gets_tighter_with_lens(app):
    order = ['full body', 'cut at feet', 'cut at knees', 'cut at thighs', 'cut at waist', 'cut at chest', 'close-up']
    seen = []
    for f in (14, 24, 35, 50, 85, 135):
        set_pose(app, 'camC', f=f)
        c = read(app)['read'][0]['cut'].split(',')[0]
        seen.append(order.index(c) if c in order else -1)
    assert seen == sorted(seen) and seen[0] < seen[-1], 'cut words not monotonic with focal length: %s' % seen


def test_partly_in_frame_named(app):
    set_pose(app, 'ann2', x=10.6)
    r = read(app)['read']
    assert r and r[0]['cut'].startswith('partly in frame (right'), r


def test_face_to_lens(app):
    r = read(app)['read'][0]
    assert r['off'] < 1
    app.rerender()
    pill = app.page.locator('#frames-d .fr .pa').first.inner_text()
    assert pill.strip() == 'to lens', pill


@pytest.mark.parametrize('r,side,arrow', [(135, 'R', '▶'), (225, 'L', '◀')])
def test_turn_side_arrow(app, r, side, arrow):
    """r=135: Ann turns toward +x, which is screen right for camera C."""
    set_pose(app, 'ann2', r=r)
    rd = read(app)['read'][0]
    assert abs(rd['off'] - 45) < 1 and rd['dir'] == side, rd
    app.rerender()
    pa = app.page.locator('#frames-d .fr .pa').first
    assert '45°' in pa.inner_text()
    # the side is carried by the head icon and spelled out in the tooltip
    tip = pa.get_attribute('title')
    assert ('screen-right' if side == 'R' else 'screen-left') in tip, tip


def test_turn_side_measured_from_line_to_lens(app):
    """CA r2 #2: with the camera off to one side, a person facing straight up the room is turned away from the lens
    toward the side the lens is NOT on."""
    set_pose(app, 'camC', x=12, y=11, r=-34)  # camera to the right, looking back at Ann
    set_pose(app, 'ann2', r=180)
    rd = read(app)['read'][0]
    assert rd['dir'] == 'L', 'face turned away from a camera on the right should read screen-left: %s' % rd


def test_background_walls_named(app):
    assert read(app)['bg'] == ['Back wall']


def test_furniture_in_frame_listed(app):
    set_pose(app, 'camC', x=8, y=12, r=-35, f=24)
    assert 'Sofa' in read(app)['furn']


def test_tap_frame_opens_its_camera(open_app):
    a = open_app({'room': sp.room_scene()}, device='phone')
    a.go(shot='s1')
    card = a.page.locator('#frames-m .fr[data-cam="camB"]')
    card.scroll_into_view_if_needed()
    bb = card.bounding_box()
    a.page.touchscreen.tap(bb['x'] + bb['width'] / 2, bb['y'] + 20)
    a.wait(400)
    assert a.S('sel') == 'camB'
