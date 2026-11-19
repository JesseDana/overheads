"""Defensive normalize: hand-written or legacy scenes (Claude writes these documents too) must load, render, list,
and save without errors."""
import copy
import pytest
import sp

CAST = [{'id': 'cj', 'name': 'Nora', 'color': '#e9c84a'}]
WALL = {'id': 'w1', 'kind': 'wall', 'name': 'Back', 'x1': 0, 'y1': 0, 'x2': 12, 'y2': 0}


def base(items, **kw):
    d = {'name': 'Bad', 'updatedAt': 5, 'cast': copy.deepcopy(CAST), 'shots': [{'id': 's1', 'beats': [{'id': 'b1'}, {'id': 'b2'}]}],
         'items': [dict(WALL)] + items}
    d.update(kw)
    return d


T = lambda **k: {'id': 'T', 'kind': 'char', 'cast': 'cj', 'shot': 's1', **k}
C = lambda **k: {'id': 'C', 'kind': 'cam', 'shot': 's1', **k}

CASES = {
    'string_numbers': base([T(k=[{'x': '6', 'y': '5', 'r': '180'}, {'x': '6', 'y': '5', 'r': '180'}]), C(k=[{'x': '6', 'y': '11', 'r': '0', 'f': '50'}] * 2),
                            {'id': 'F', 'kind': 'furn', 'shape': 'sofa', 'x': '3', 'y': '2', 'w': '7', 'h': '3'}]),
    'unknown_postures': base([T(k=[{'x': 6, 'y': 5, 'r': 180, 'ps': 'kneel'}, {'x': 6, 'y': 5, 'r': 180, 'ps': 'Seated'}]),
                              {'id': 'T2', 'kind': 'char', 'cast': 'cj', 'shot': 's1', 'k': [{'x': 8, 'y': 5, 'r': 180, 'ps': 'stool'}] * 2}, C(k=[{'x': 6, 'y': 11, 'r': 0}] * 2)]),
    'null_poses': base([T(k=[None, {'x': 6, 'y': 5, 'r': 180}]), C(k=[{'x': 6, 'y': 11, 'r': 0}, None])]),
    'legacy_top_level': base([{'id': 'T', 'kind': 'char', 'cast': 'cj', 'shot': 's1', 'x': 6, 'y': 5, 'r': 180, 'ps': 'bar'},
                              {'id': 'C', 'kind': 'cam', 'shot': 's1', 'x': 6, 'y': 11, 'r': 0, 'f': 85, 'h': 4, 'aim': 'T'}]),
    'cast_by_name_and_no_id': base([T(cast='Nora', k=[{'x': 6, 'y': 5, 'r': 180}]), {'id': 'U', 'kind': 'char', 'shot': 's1', 'name': 'Ravi', 'k': [{'x': 8, 'y': 5, 'r': 180}]},
                                    C(k=[{'x': 6, 'y': 11, 'r': 0}])], cast=[{'id': 'cj', 'name': 'Nora'}, {'name': 'Sam'}]),
    'duplicate_ids_across_shots': base([T(k=[{'x': 3, 'y': 3, 'r': 180}]), C(k=[{'x': 3, 'y': 10, 'r': 0, 'aim': 'T'}]),
                                        {'id': 'T', 'kind': 'char', 'cast': 'cj', 'shot': 's2', 'k': [{'x': 9, 'y': 3, 'r': 180}]},
                                        {'id': 'C', 'kind': 'cam', 'shot': 's2', 'k': [{'x': 9, 'y': 10, 'r': 0, 'aim': 'T'}]}],
                                       shots=[{'id': 's1', 'beats': [{'id': 'b1'}]}, {'id': 's2', 'beats': [{'id': 'b2'}]}]),
    'nan_geometry': base([T(k=[{'x': None, 'y': 'abc', 'r': 180}]), C(k=[{'x': 6, 'y': 11, 'r': 0, 'f': 0}]),
                          {'id': 'F', 'kind': 'furn', 'shape': 'spaceship', 'x': 'NaN', 'y': 2},
                          {'id': 'W2', 'kind': 'wall', 'x1': 'oops'}, {'id': 'L', 'kind': 'light', 'type': 'broad', 'x': 2, 'y': 2},
                          {'id': 'Fr', 'kind': 'frame', 'type': 'mirror', 'x': 4, 'y': 4}]),
    'no_shots_top_level_beats': {'name': 'Old', 'cast': CAST, 'beats': [{'name': 'One'}, {'name': 'Two'}],
                                 'items': [dict(WALL), {'id': 'T', 'kind': 'char', 'cast': 'cj', 'k': [{'x': 6, 'y': 5, 'r': 180}] * 3},
                                           {'id': 'C', 'kind': 'cam', 'k': [{'x': 6, 'y': 11, 'r': 0}]}]},
    'junk_containers': {'name': 'Junk', 'cast': None, 'shots': [None, {'id': 's1', 'name': 'Shot 1', 'beats': ['Opening', None]}],
                        'items': [None, 7, dict(WALL), {'id': 'C', 'kind': 'cam', 'shot': 'nope', 'k': [{'x': 6, 'y': 11, 'r': 0}]}]},
}


@pytest.mark.parametrize('case', list(CASES))
def test_malformed_scene_loads_lists_and_saves(open_app, case):
    app = open_app({'bad': CASES[case]})
    assert not app.errors, app.errors
    assert app.S('mode') == 'local' and app.S('curId') == 'bad'
    assert app.js("()=>!document.body.innerText.includes('Loading plans')")
    sc = app.scene()
    for it in sc['items']:
        for q in it.get('k', []):
            for f in ('x', 'y', 'r'):
                assert isinstance(q[f], (int, float)), (case, it['id'], q)
            assert q.get('ps', 'stand') in ('stand', 'walk', 'bar', 'chair'), q
        for f in ('x', 'y', 'x1', 'y1', 'x2', 'y2', 'w', 'h'):
            if f in it:
                assert isinstance(it[f], (int, float)), (case, it['id'], f, it[f])
    app.open_more('list')
    app.wait(150)
    assert app.js("()=>document.querySelectorAll('#sheet .slist > div').length") > 0
    app.page.keyboard.press('Escape')
    cam = next(i for i in sc['items'] if i['kind'] == 'cam')
    app.go(shot=cam['shot'])
    app.select(cam['id'])
    app.page.keyboard.press('ArrowRight')
    app.wait(1300)
    st = app.stored('bad')
    k = next(i for i in st['items'] if i['id'] == cam['id'])['k']
    assert isinstance(k[0]['x'], (int, float)) and k[0]['x'] == next(i for i in sc['items'] if i['id'] == cam['id'])['k'][0]['x'] + .25
    assert not app.errors, app.errors


def test_string_numbers_become_numbers(open_app):
    app = open_app({'bad': CASES['string_numbers']})
    app.go(shot='s1')
    app.select('T')
    app.page.keyboard.press('ArrowRight')
    assert app.item('T')['k'][0]['x'] == 6.25


def test_posture_aliases(open_app):
    app = open_app({'bad': CASES['unknown_postures']})
    sc = app.scene()
    t, t2 = [next(i for i in sc['items'] if i['id'] == n) for n in ('T', 'T2')]
    assert [q['ps'] for q in t['k']] == ['stand', 'chair'] and t2['k'][0]['ps'] == 'bar'


def test_legacy_camera_keeps_lens_height_aim(open_app):
    app = open_app({'bad': CASES['legacy_top_level']})
    c = app.item('C')
    assert c['k'][0]['f'] == 85 and c['k'][0]['h'] == 4 and c['k'][0]['aim'] == 'T'
    assert app.item('T')['k'][0]['ps'] == 'bar'


def test_cast_linking(open_app):
    app = open_app({'bad': CASES['cast_by_name_and_no_id']})
    sc = app.scene()
    names = sorted(c['name'] for c in sc['cast'])
    assert names == ['Nora', 'Ravi', 'Sam'], names
    assert app.item('T')['name'] == 'Nora' and app.item('U')['name'] == 'Ravi'


def test_duplicate_ids_reassigned_and_aims_follow(open_app):
    app = open_app({'bad': CASES['duplicate_ids_across_shots']})
    sc = app.scene()
    ids = [i['id'] for i in sc['items']]
    assert len(ids) == len(set(ids))
    cams = {i['shot']: i for i in sc['items'] if i['kind'] == 'cam'}
    chars = {i['shot']: i for i in sc['items'] if i['kind'] == 'char'}
    for s in ('s1', 's2'):
        assert cams[s]['k'][0]['aim'] == chars[s]['id'], 'camera in %s aims at the other shot\'s copy' % s
    app.go(shot='s2')
    app.select(cams['s2']['id'])
    app.page.keyboard.press('ArrowRight')
    assert app.item(cams['s2']['id'])['k'][0]['x'] == 9.25 and app.item(cams['s1']['id'])['k'][0]['x'] == 3


def test_poses_padded_to_beats(open_app):
    sc0 = base([T(k=[{'x': 6, 'y': 5, 'r': 180}, {'x': 7, 'y': 5, 'r': 180}, {'x': 8, 'y': 5, 'r': 180}])], shots=[{'id': 's1', 'beats': [{'id': 'b1'}]}])
    app = open_app({'bad': sc0})
    assert len(app.scene()['shots'][0]['beats']) == 3
    assert app.item('T')['k'][2]['x'] == 8


@pytest.mark.parametrize('case', ['no_shot_field', 'top_level_beats'])
def test_poses_padded_when_item_has_no_shot(open_app, case):
    """Claude may omit 'shot' on items of a one-shot scene. Their extra poses must not be cut off."""
    if case == 'top_level_beats':
        sc0 = CASES['no_shots_top_level_beats']
    else:
        sc0 = base([{'id': 'T', 'kind': 'char', 'cast': 'cj', 'k': [{'x': 6, 'y': 5, 'r': 180}, {'x': 7, 'y': 5, 'r': 180}, {'x': 8, 'y': 5, 'r': 180}]}],
                   shots=[{'id': 's1', 'beats': [{'id': 'b1'}]}])
    app = open_app({'bad': sc0})
    t = app.item('T')
    assert len(t['k']) == 3 and t['k'][2]['x'] in (6, 8), 'third pose cut off: beats=%d, k=%s' % (len(app.scene()['shots'][0]['beats']), t['k'])
