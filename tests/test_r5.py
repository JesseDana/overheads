"""Round 5 (owner requests): camera bodies, desqueeze and aspect ratio; group framing; dragging the frame preview; pinned preview on phone."""
import sp


def scene_with(cam_patch=None, beats=True):
    sc = sp.room_scene(two_beats=beats)
    for it in sc['items']:
        if it['id'] == 'camB' and cam_patch:
            it.update(cam_patch)
    return sc


def geom(app, cam):
    return app.js("c=>{const P=window.__shotplans,sc=P.cur();return P.camGeom(sc,sc.items.find(i=>i.id===c))}", cam)


def read(app, cam, beat=0, W=320):
    return app.js("([c,b,W])=>{const P=window.__shotplans,sc=P.cur(),f=P.frameInfo(sc,sc.items.find(i=>i.id===c),b,W);return {H:f.H,read:f.read.map(r=>({id:r.id,cut:r.cut,cx:r.cx,off:r.off}))}}", [cam, beat, W])


def test_anamorphic_desqueeze_and_crop(open_app):
    # Alexa Mini 2.8K 4:3 (23.76 x 17.82) with a 2x lens is 47.52 x 17.82 unsqueezed; a 2.39 extraction keeps full height
    app = open_app({'room': scene_with({'body': 'amini', 'mode': 3, 'sq': 2, 'ar': '2.39'})})
    g = geom(app, 'camB')
    assert abs(g['h'] - 17.82) < .01 and abs(g['w'] - 17.82 * 2.39) < .05, g
    assert abs(g['ar'] - 2.39) < .01


def test_spherical_native_and_letterbox(open_app):
    app = open_app({'room': scene_with({'body': 'fx3', 'mode': 0})})
    g = geom(app, 'camB')
    assert abs(g['w'] - 35.6) < .1 and abs(g['h'] - 20.0) < .01
    # 2.39 from a 16:9 sensor crops height, keeps width
    app.js("()=>{window.__shotplans.cur().ar='2.39'}")
    g = geom(app, 'camB')
    assert abs(g['w'] - 35.6) < .1 and abs(g['ar'] - 2.39) < .01


def test_bad_camera_fields_are_dropped(open_app):
    app = open_app({'room': scene_with({'body': 'constructor', 'mode': 99, 'sq': 7, 'ar': '<b>'})})
    c = app.item('camB')
    g = geom(app, 'camB')
    assert c.get('body') in (None, '') and c.get('sq') in (None, 1) and c.get('ar') in (None, 'native', '1.78'), c
    assert g['w'] > 20


def test_group_aim_holds_both_people_centred(open_app):
    app = open_app({'room': scene_with()})
    app.go(shot='s1')
    app.select('camB')
    app.page.locator('#insp-d [data-act="aimto"][data-v="ann"]').click()
    app.page.locator('#insp-d [data-act="aimto"][data-v="bob"]').click()
    app.wait(200)
    p = app.pose('camB', 0)
    assert p.get('aim') == 'ann' and p.get('aims') == ['bob'], p
    f = read(app, 'camB', 0)
    xs = [r['cx'] for r in f['read'] if r['id'] in ('ann', 'bob')]
    assert len(xs) == 2 and all(0 < x < 320 for x in xs), f
    mid = sum(xs) / 2
    assert abs(mid - 160) < 30, 'pair not centred: %s' % xs


def test_frame_drag_snaps_to_left_third(open_app):
    app = open_app({'room': scene_with()})
    app.go(shot='s1')
    app.select('camB')
    app.wait(200)
    # find Bob's left-third snap and the drag that reaches it
    plan = app.js("""()=>{const P=window.__shotplans,sc=P.cur(),cam=sc.items.find(i=>i.id==='camB'),p=P.poseT(sc,cam,0),G=P.camGeom(sc,cam),
      sn=P.frameSnaps(sc,cam,p,G,p.f||35).find(s=>s.ids.length===1&&s.ids[0]==='bob'&&s.ap==='l'),
      fi=P.frameInfo(sc,cam,0,320,{lite:true}),el=document.querySelector('#insp-d .insp-frame svg'),rc=el.getBoundingClientRect(),
      hf=2*Math.atan(G.w/(2*(p.f||35)))*180/Math.PI,vf=2*Math.atan(G.w/G.ar/(2*(p.f||35)))*180/Math.PI;
      let dr=((sn.r-p.r+540)%360)-180;return {x:rc.left+rc.width/2,y:rc.top+rc.height/2,dx:-dr/hf*rc.width,dy:(sn.tl-fi.tilt)/vf*rc.height}}""")
    m = app.page.mouse
    m.move(plan['x'], plan['y'])
    m.down()
    for i in range(1, 9):
        m.move(plan['x'] + plan['dx'] * i / 8, plan['y'] + plan['dy'] * i / 8)
    m.up()
    app.wait(200)
    p = app.pose('camB', 0)
    assert p.get('aim') == 'bob' and p.get('ap') == 'l', p
    f = read(app, 'camB', 0)
    bob = next(r for r in f['read'] if r['id'] == 'bob')
    assert abs(bob['cx'] - 320 / 3) < 12, 'Bob not on the left third: cx=%.1f' % bob['cx']


def test_frame_drag_off_snap_is_manual_pan_and_tilt(open_app):
    app = open_app({'room': scene_with()})
    app.go(shot='s1')
    app.select('camB')
    app.wait(200)
    box = app.page.locator('#insp-d .insp-frame svg').bounding_box()
    r0 = app.pose('camB', 0)['r']
    m = app.page.mouse
    m.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    m.down()
    m.move(box['x'] + box['width'] / 2 + 37, box['y'] + box['height'] / 2 + 23, steps=6)
    m.up()
    app.wait(150)
    p = app.pose('camB', 0)
    assert p.get('tm') == 'man' or p.get('aim'), p
    assert abs(p['r'] - r0) > 1
    # one undo step puts it back
    app.page.keyboard.press('Control+z')
    app.wait(150)
    assert abs(app.pose('camB', 0)['r'] - r0) < .01


def test_phone_preview_stays_visible_while_scrolling_controls(open_app):
    app = open_app('workshop', device='phone')
    cam = app.js("()=>window.__shotplans.inShot(window.__shotplans.cur()).find(i=>i.kind==='cam').id")
    app.select(cam)
    app.wait(300)
    sc = app.page.locator('#insp-m .insp-scroll')
    for y in (0, 200, 600, 5000):
        sc.evaluate('(el,y)=>el.scrollTop=y', y)
        app.wait(120)
        b = app.page.locator('#insp-m .insp-frame svg').bounding_box()
        assert b and b['height'] >= 80, 'preview collapsed at scroll %d: %s' % (y, b)
        assert b['y'] >= 0 and b['y'] + b['height'] <= 852, 'preview off screen at scroll %d: %s' % (y, b)


def test_fx5_open_gate_with_2x_at_239(open_app):
    # FX5 open gate 35.9 x 24.0; 2x unsqueezed 71.8 wide, so 2.39 keeps full height
    app = open_app({'room': scene_with({'body': 'fx5', 'mode': 2, 'sq': 2, 'ar': '2.39'})})
    g = geom(app, 'camB')
    assert abs(g['h'] - 24.0) < .01 and abs(g['ar'] - 2.39) < .01, g
