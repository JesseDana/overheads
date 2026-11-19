"""Locked-off cameras: one position, lens, height and tilt in every beat; aimed + auto tilt hold across beats."""
import sp


def setup(open_app, posture_change=True):
    sc = sp.room_scene()
    if posture_change:  # Ann sits on a bar stool in beat 1, stands and steps right in beat 2
        ann = next(i for i in sc['items'] if i['id'] == 'ann')
        ann['k'][0]['ps'] = 'bar'
    app = open_app({'room': sc})
    app.go(shot='s1')
    return app


def aim(app, cam, who):
    app.select(cam)
    app.page.locator('#insp-d [data-act="aimto"][data-v=""]').click()
    app.wait(80)
    app.page.locator('#insp-d [data-act="aimto"][data-v="%s"]' % who).click()
    app.wait(150)


def frame(app, cam, beat):
    return app.js("([c,b])=>{const P=window.__shotplans,sc=P.cur(),cam=sc.items.find(i=>i.id===c),f=P.frameInfo(sc,cam,b,320);return {tilt:f.tilt,f:f.f,h:f.h,read:f.read.map(r=>({name:r.name,cut:r.cut,off:r.off,dir:r.dir,across:r.across}))}}", [cam, beat])


def test_locked_aim_holds_pan_across_beats(open_app):
    app = setup(open_app)
    aim(app, 'camA', 'ann')
    r0, r1 = app.pose('camA', 0)['r'], app.pose('camA', 1)['r']
    assert abs(r0 - r1) < .01, 'locked-off camera aimed at Ann pans between beats: %.2f vs %.2f' % (r0, r1)


def test_locked_auto_tilt_holds_across_beats(open_app):
    app = setup(open_app)
    aim(app, 'camA', 'ann')
    t0, t1 = frame(app, 'camA', 0)['tilt'], frame(app, 'camA', 1)['tilt']
    assert abs(t0 - t1) < .01, 'auto tilt on a locked-off camera changes between beats: %.2f vs %.2f' % (t0, t1)


def test_locked_frame_keeps_eyes_in_frame_for_both_beats(open_app):
    app = setup(open_app)
    aim(app, 'camA', 'ann')
    for b in (0, 1):
        ann = [r for r in frame(app, 'camA', b)['read'] if r['name'] == 'Ann'][0]
        assert 'eyes out' not in ann['cut'] and 'out of frame' not in ann['cut'], (b, ann['cut'])


def test_unlocked_aimed_camera_pans(open_app):
    app = setup(open_app)
    aim(app, 'camB', 'ann')
    assert abs(app.pose('camB', 0)['r'] - app.pose('camB', 1)['r']) > 2, 'a moving camera aimed at someone should follow them'


def test_locked_lens_height_change_applies_to_every_beat(open_app):
    app = setup(open_app)
    app.go(shot='s1', beat=1)
    app.select('camA')
    f = app.page.locator('#insp-d [data-f="pose.f"]')
    f.fill('85')
    f.dispatch_event('change')
    app.wait(150)
    k = app.item('camA')['k']
    assert [q['f'] for q in k] == [85, 85], k


def test_unlock_then_move_one_beat_only(open_app):
    app = setup(open_app)
    app.select('camA')
    app.page.click('#insp-d [data-act="held"][data-v="0"]')
    app.wait(100)
    assert app.item('camA')['held'] is False
    app.go(shot='s1', beat=1)
    app.drag_item_to('camA', 5, 12)
    k = app.item('camA')['k']
    assert (k[0]['x'], k[1]['x']) == (8, 5), k


def test_held_migration_for_matching_beats(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['kind'] == 'cam':
            i.pop('held', None)
    app = open_app({'room': sc})
    held = {i['id']: i['held'] for i in app.scene()['items'] if i['kind'] == 'cam'}
    assert held == {'camA': True, 'camB': False, 'camC': True}


def test_moving_camera_cut_row_uses_each_beats_camera(open_app):
    """CA r2 #1: for a moving camera, the across-beat row must use that beat's own camera pose."""
    app = setup(open_app)
    for b in (0, 1):  # camB moves from (12,12) to (12,10); point it at Bob in both beats
        app.go(shot='s1', beat=b)
        aim(app, 'camB', 'bob')
    f0, f1 = frame(app, 'camB', 0), frame(app, 'camB', 1)
    bob0 = [r for r in f0['read'] if r['name'] == 'Bob'][0]
    bob1 = [r for r in f1['read'] if r['name'] == 'Bob'][0]
    row = {a['b']: a['cut'] for a in bob0['across']}
    assert row.get(1) == bob1['cut'], 'beat-2 entry of the cut row (%r) disagrees with beat 2\'s own frame (%r)' % (row.get(1), bob1['cut'])


def test_relock_copies_current_beat(open_app):
    app = setup(open_app)
    app.go(shot='s1', beat=1)
    app.select('camB')
    app.page.click('#insp-d [data-act="held"][data-v="1"]')
    app.wait(100)
    k = app.item('camB')['k']
    assert k[0] == k[1] and (k[0]['x'], k[0]['y']) == (12, 10)
    assert "beat 2's camera" in app.toast()


def test_new_camera_exists_in_every_beat(open_app):
    app = setup(open_app)
    app.go(shot='s1', beat=1)
    app.page.click('#tools [data-menu="rig"]')
    app.page.click('[data-newcam]')
    app.wait(150)
    cam = [i for i in app.scene()['items'] if i['kind'] == 'cam' and i['id'] not in ('camA', 'camB', 'camC')][0]
    assert len(cam['k']) == 2 and not any(q.get('out') for q in cam['k'])
