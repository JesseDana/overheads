"""Lighting model sanity. Geometry: the person stands at (0,0) facing +y (r=180), the camera at (0,10) looks back
(r=0). Screen right is +x. psi: 0 = from the lens, + = from frame right, |psi| > 90 deg = from behind."""
import math
import pytest
import sp

PERSON = {'x': 0, 'y': 0, 'r': 180}
CAM = {'x': 0, 'y': 10, 'r': 0}


def bearing(dx, dy):
    return math.degrees(math.atan2(dx, -dy))


def light(id='L', x=5, y=5, at=(0, 0), level=100, type='point', spread=40):
    return {'id': id, 'kind': 'light', 'type': type, 'x': x, 'y': y, 'r': bearing(at[0] - x, at[1] - y), 'level': level, 'spread': spread, 'w': 3}


def frame(id, type, x, y, r, size=4):
    return {'id': id, 'kind': 'frame', 'type': type, 'x': x, 'y': y, 'r': r, 'size': size}


@pytest.fixture(scope='module')
def terms(browser, tmp_path_factory):
    """lightTerms is pure; one page serves the whole module."""
    d = tmp_path_factory.mktemp('light')
    (d / '_app.html').write_text(sp.page_html())
    ctx = browser.new_context(**sp.DEVICES['desktop'])
    ctx.add_init_script(sp.STUB + sp.seed_js({'room': sp.room_scene()}))
    pg = ctx.new_page()
    pg.goto('file://' + str(d / '_app.html'))
    pg.wait_for_timeout(700)

    def f(items, q=PERSON, cp=CAM):
        return pg.evaluate("([items,q,cp])=>window.__shotplans.lightTerms({items,layerState:{}},q,cp)", [items, q, cp])
    yield f
    ctx.close()


def test_key_from_camera_right_reads_frame_right(terms):
    t = terms([light()])
    assert len(t) == 1 and t[0]['I'] > 0
    assert 40 < math.degrees(t[0]['psi']) < 50


def test_diff_makes_soft_source_at_frame_capped_at_half(terms):
    direct = terms([light()])[0]['I']
    t = terms([light(), frame('F', 'diff', 2.5, 2.5, -45)])
    assert len(t) == 1 and t[0].get('via') == 'F'
    assert t[0]['soft'] >= .6
    assert t[0]['I'] <= .5 * direct + 1e-9, 'diff passes more than half the direct light'


def test_silk_also_diffuses(terms):
    t = terms([light(), frame('F', 'silk', 2.5, 2.5, -45)])
    assert t and t[0].get('via') == 'F'


def test_neg_in_path_cuts_light_and_darkens_its_side(terms):
    t = terms([light(), frame('N', 'neg', 2.5, 2.5, -45)])
    assert not any(x['I'] > 0 for x in t), 'a neg between light and person did not cut it'
    neg = [x for x in t if x['I'] < 0]
    assert neg and math.degrees(neg[0]['psi']) > 0, 'neg on frame right should darken frame right'


def test_neg_beside_person_darkens_screen_left(terms):
    t = terms([light(), frame('N', 'neg', -2, 0, 0)])
    neg = [x for x in t if x['I'] < 0]
    assert neg and math.degrees(neg[0]['psi']) < 0


def test_bounce_sends_light_back_from_its_side(terms):
    lt = light(x=3, y=6, at=(-3, 2), spread=20)
    assert terms([lt]) == [], 'test light should miss the person'
    t = terms([lt, frame('B', 'bounce', -3, 2, 90)])
    assert len(t) == 1 and t[0]['I'] > 0
    assert math.degrees(t[0]['psi']) < 0, 'bounce on frame left should light from frame left'


def test_bounce_with_person_on_far_side_does_nothing(terms):
    lt = light(x=3, y=6, at=(-3, 3), spread=20)
    assert terms([lt]) == []
    assert terms([lt, frame('B', 'bounce', -3, 3, 0)]) == [], 'a bounce lit from one side lit a person on its other side'


def test_backlight_reads_from_behind_on_its_side(terms):
    t = terms([light(x=3, y=-5)])
    assert t and math.degrees(t[0]['psi']) > 100, 'backlight from behind-right'


def test_zero_output_light_ignored(terms):
    assert terms([light(level=0)]) == []


# ---------------------------------------------------------------- rendered frames
def lit_scene():
    sc = sp.room_scene()
    sc['items'] = [i for i in sc['items'] if i['kind'] != 'light']
    # Ann at (6,5), Bob at (11,5). Key on Ann only (narrow, close); a weak broad on Bob.
    sc['items'] += [dict(light('keyAnn', 4, 8, (6, 5), 100, 'point', 20)),
                    dict(light('fillBob', 13, 8, (11, 5), 40, 'point', 20)),
                    dict(light('backR', 13, 2, (11, 5), 100, 'point', 30))]
    for i in sc['items']:
        if i['id'] == 'camA':  # a tight single on Bob
            i['k'] = [{'x': 11, 'y': 11, 'r': 0, 'f': 85, 'h': 5}] * 2
    return sc


def gradients(app, cam):
    return app.js("""c=>{const P=window.__shotplans,sc=P.cur(),f=P.frameInfo(sc,sc.items.find(i=>i.id===c),0,320);
      const bob=sc.items.find(i=>i.id==='bob').color,rgb=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));
      // keep only Bob's gradients (blue: b > r), so off-frame figures drawn into the same svg don't count
      const gs=[...f.svg.matchAll(/<linearGradient[^>]*>(.*?)<\/linearGradient>/g)].map(m=>[...m[1].matchAll(/stop-color="([^"]+)"/g)].map(x=>x[1]))
        .filter(st=>{const [r,,b]=rgb(st[9]);return b>r});
      return {stops:gs.map(g=>g.join(',')).join(';'),read:f.read.map(r=>r.name),note:f.litNote}}""", cam)


def test_exposure_is_per_camera(open_app):
    """Turning Ann's key up must not darken Bob in a camera that frames only Bob."""
    app = open_app({'room': lit_scene()})
    app.go(shot='s1')
    g0 = gradients(app, 'camA')
    assert g0['read'] == ['Bob'], 'test setup: camera A should frame Bob only, got %s' % g0['read']
    assert g0['stops'], 'no lit gradient found for Bob'
    app.js("()=>{window.__shotplans.cur().items.find(i=>i.id==='keyAnn').level=20}")
    g1 = gradients(app, 'camA')
    assert g0['stops'] == g1['stops'], 'exposure in camera A follows a light on someone it does not frame'


def test_rim_drawn_on_backlight_side(open_app):
    app = open_app({'room': lit_scene()})
    app.go(shot='s1')
    r = app.js("""()=>{const P=window.__shotplans,sc=P.cur(),f=P.frameInfo(sc,sc.items.find(i=>i.id==='camA'),0,320);const cx=f.read[0].cx;
      const rims=[...f.svg.matchAll(/<path d="M([-\\d.]+) [^"]*" fill="none" stroke="[^"]+" stroke-opacity/g)].map(m=>+m[1]);return {cx,rims}}""")
    assert r['rims'], 'no rim drawn for a strong backlight'
    assert all(x > r['cx'] for x in r['rims']), 'rim on the wrong side: %s vs centre %s' % (r['rims'], r['cx'])


def test_unlit_person_flagged(open_app):
    sc = lit_scene()
    sc['items'] = [i for i in sc['items'] if i['id'] not in ('fillBob', 'backR')]
    app = open_app({'room': sc})
    app.go(shot='s1')
    assert gradients(app, 'camA')['note'] == 'No light reaches Bob.'


def test_hidden_lighting_renders_flat(open_app):
    sc = lit_scene()
    sc['layerState'] = {'light': {'hidden': True}}
    app = open_app({'room': sc})
    app.go(shot='s1')
    g = gradients(app, 'camA')
    assert g['stops'] == '' and g['note'] == ''
