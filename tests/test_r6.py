"""Round 6: the scene's cameras (roster) with per-shot format and aspect; scout photos on a camera."""
import io
import os
import sp
from test_export import export


def two_shot_scene():
    """camA in shot 1 and camA2 (also named A) in shot 2, so both are camera A."""
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'camC':
            i['name'] = 'A'
    return sc


def geom(app, cam):
    return app.js("c=>{const P=window.__shotplans,sc=P.cur();return P.camGeom(sc,sc.items.find(i=>i.id===c))}", cam)


def test_same_name_in_two_shots_is_one_camera(open_app):
    app = open_app({'room': two_shot_scene()})
    s = app.scene()
    names = [r['name'] for r in s['rig']]
    assert sorted(names) == ['A', 'B'], s['rig']
    a = [i for i in s['items'] if i['kind'] == 'cam' and i['name'] == 'A']
    assert len(a) == 2 and a[0]['rig'] == a[1]['rig']


def test_legacy_per_camera_format_moves_to_roster(open_app):
    sc = two_shot_scene()
    for i in sc['items']:
        if i['id'] == 'camA':
            i.update(body='fx6', mode=1, sq=1.5, ar='2.39')
    app = open_app({'room': sc})
    s = app.scene()
    A = next(r for r in s['rig'] if r['name'] == 'A')
    assert A.get('body') == 'fx6' and A.get('mode') == 1 and A.get('sq') == 1.5, A
    assert s.get('ar') == '2.39'
    camC = app.item('camC')
    assert 'body' not in camC and 'ar' not in camC
    # camera A in shot 2 now has the same format
    app.go(shot='s2')
    g = geom(app, 'camC')
    assert g['body'] == 'fx6' and g['sq'] == 1.5 and abs(g['ar'] - 2.39) < .01


def test_format_edit_applies_to_every_shot_until_shot_overrides(open_app):
    app = open_app({'room': two_shot_scene()})
    app.go(shot='s1')
    app.select('camA')
    app.page.select_option('#insp-d #f-body', 'burano')
    app.wait(150)
    assert geom(app, 'camC')['body'] == 'burano'
    # shot 2: camera A goes anamorphic for this shot only
    app.go(shot='s2')
    app.select('camC')
    app.page.click('#insp-d [data-act="fmtown"][data-v="1"]')
    app.page.click('#insp-d [data-act="sq"][data-v="2"]')
    app.wait(150)
    assert geom(app, 'camC')['sq'] == 2 and geom(app, 'camA')['sq'] == 1
    # back to A's usual
    app.page.click('#insp-d [data-act="fmtown"][data-v="0"]')
    app.wait(150)
    assert geom(app, 'camC')['sq'] == 1 and geom(app, 'camC')['body'] == 'burano'


def test_aspect_scene_wide_then_per_shot(open_app):
    app = open_app({'room': two_shot_scene()})
    app.go(shot='s1')
    app.select('camA')
    app.page.click('#insp-d [data-act="ar"][data-v="1.85"]')
    app.wait(150)
    assert abs(geom(app, 'camC')['ar'] - 1.85) < .01 and abs(geom(app, 'camB')['ar'] - 1.85) < .01
    app.page.click('#insp-d [data-act="arown"][data-v="1"]')
    app.page.click('#insp-d [data-act="ar"][data-v="2.39"]')
    app.wait(150)
    # every camera in shot 1 changes; shot 2 keeps the scene's
    assert abs(geom(app, 'camA')['ar'] - 2.39) < .01 and abs(geom(app, 'camB')['ar'] - 2.39) < .01
    assert abs(geom(app, 'camC')['ar'] - 1.85) < .01
    assert app.scene()['shots'][0]['ar'] == '2.39' and app.scene()['ar'] == '1.85'


def test_camera_tool_lists_cameras_and_places_one(open_app):
    app = open_app({'room': two_shot_scene()})
    app.go(shot='s2')
    app.page.click('#tools [data-menu="rig"]')
    app.wait(150)
    txt = app.js("()=>document.querySelector('#sheet').textContent")
    assert 'Place in shot 1B' in txt
    B = next(r for r in app.scene()['rig'] if r['name'] == 'B')
    app.page.click('[data-place="%s"]' % B['id'])
    app.wait(150)
    placed = [i for i in app.scene()['items'] if i['kind'] == 'cam' and i['shot'] == 's2' and i['rig'] == B['id']]
    assert len(placed) == 1 and placed[0]['name'] == 'B' and placed[0]['color'] == B['color']


def test_new_camera_gets_next_letter_and_copies_format(open_app):
    sc = two_shot_scene()
    for i in sc['items']:
        if i['id'] == 'camB':
            i.update(body='fx3')
    app = open_app({'room': sc})
    app.go(shot='s1')
    app.page.click('#tools [data-menu="rig"]')
    app.page.click('[data-newcam]')
    app.wait(150)
    s = app.scene()
    C = next(r for r in s['rig'] if r['name'] == 'C')
    assert C.get('body') == 'fx3'


def test_renaming_camera_renames_it_in_every_shot(open_app):
    app = open_app({'room': two_shot_scene()})
    app.go(shot='s1')
    app.select('camA')
    f = app.page.locator('#insp-d [data-f="name"]')
    f.fill('Wide')
    f.dispatch_event('change')
    app.wait(150)
    assert app.item('camC')['name'] == 'Wide'


# ---------------------------------------------------------------- scout photos
def jpeg(f35=None, size=(400, 300)):
    from PIL import Image
    im = Image.new('RGB', size, (120, 140, 160))
    buf = io.BytesIO()
    if f35:
        ex = Image.Exif()
        ex.get_ifd(0x8769)[0xA405] = f35
        im.save(buf, 'JPEG', exif=ex)
    else:
        im.save(buf, 'JPEG')
    return buf.getvalue()


def add_photo(app, cam, data, tmp):
    p = os.path.join(tmp, 'scout.jpg')
    open(p, 'wb').write(data)
    app.select(cam)
    with app.page.expect_file_chooser() as fc:
        app.page.click('#insp-d [data-act="phadd"]')
    fc.value.set_files(p)
    for _ in range(40):
        app.wait(100)
        if app.item(cam).get('photos'):
            break


def test_phone_photo_reads_lens_and_shows_in_frame(open_app, tmp_path):
    app = open_app({'room': two_shot_scene()})
    app.go(shot='s1')
    add_photo(app, 'camA', jpeg(24), str(tmp_path))
    ph = app.item('camA')['photos']['all']
    assert ph['f35'] == 24 and ph['src2'] == 'phone'
    # 24mm equivalent on a 4:3 frame: 34.6 mm wide, about 71.6 degrees
    assert abs(ph['hf'] - 71.6) < .5, ph['hf']
    info = app.js("()=>{const P=window.__shotplans,sc=P.cur(),c=sc.items.find(i=>i.id==='camA'),f=P.frameInfo(sc,c,0,320);return {photo:f.photo,img:/<image /.test(f.svg)}}")
    assert info['photo'] and info['img']


def test_viewfinder_frame_without_exif_matches_lens(open_app, tmp_path):
    app = open_app({'room': two_shot_scene()})
    app.go(shot='s1')
    add_photo(app, 'camB', jpeg(None, (480, 270)), str(tmp_path))
    c = app.item('camB')
    key = next(iter(c['photos']))
    assert key != 'all', 'a moving camera keeps one photo per beat'
    ph = c['photos'][key]
    g = geom(app, 'camB')
    import math
    expect = 2 * math.degrees(math.atan(g['w'] / (2 * 50)))
    assert ph['src2'] == 'lens' and abs(ph['hf'] - expect) < .2


def test_drag_moves_photo_not_camera_in_photo_mode(open_app, tmp_path):
    app = open_app({'room': two_shot_scene()})
    app.go(shot='s1')
    add_photo(app, 'camA', jpeg(24), str(tmp_path))
    app.page.click('#insp-d [data-act="phalign"][data-v="photo"]')
    app.wait(100)
    r0 = app.pose('camA', 0)['r']
    pr0 = app.item('camA')['photos']['all']['r']
    box = app.page.locator('#insp-d .insp-frame svg').bounding_box()
    m = app.page.mouse
    m.move(box['x'] + 100, box['y'] + 60)
    m.down()
    m.move(box['x'] + 140, box['y'] + 70, steps=5)
    m.up()
    app.wait(150)
    assert abs(app.pose('camA', 0)['r'] - r0) < .01
    assert app.item('camA')['photos']['all']['r'] > pr0 + 1


def test_pdf_includes_photo(open_app, tmp_path):
    app = open_app({'room': two_shot_scene()})
    app.go(shot='s1')
    add_photo(app, 'camA', jpeg(24), str(tmp_path))
    f = export(app, 'pdf')
    assert os.path.getsize(f) > 10000


def test_hostile_photo_src_dropped(open_app):
    sc = two_shot_scene()
    for i in sc['items']:
        if i['id'] == 'camA':
            i['photos'] = {'all': {'src': 'javascript:alert(1)', 'r': 0}, 'b1': {'src': 'data:image/svg+xml;base64,PHN2Zz4=', 'r': 0},
                           'x"y': {'src': 'https://example.com/a.jpg'}}
    app = open_app({'room': sc})
    assert 'photos' not in app.item('camA')
