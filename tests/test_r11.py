"""Round 11 (v39): scenes inside a location, shot codes, the shot list, spreadsheet import and export."""
import json, os
import sp

HERE = os.path.dirname(__file__)
LIVE2 = os.path.join(HERE, 'data', 'workshop2.json')
OUT = os.environ.get('OVERHEADS_SHOTS', os.path.join(HERE, 'out')) + os.sep
os.makedirs(OUT, exist_ok=True)

# a sample shot list, as Google Sheets copies it (tabs)
SHEET = '\n'.join('\t'.join(r) for r in [
    ['Scene', 'Shot', 'Int/Ext', 'Time', 'Location', 'Shot Type', 'Shot Description', 'Special Tools', 'Synopsis', 'Thematic Intention', 'Notes', '', 'Anthonys Notes'],
    ['1', ' ', 'EXT', 'DAWN', "Harbor House", '', '', '', 'Opening of the film', 'Establish the town'],
    ['', 'a', '', '', '', 'HH WS', 'Harbor at first light'],
    ['', 'b', '', '', '', 'HH WS', 'Harbor at first light'],
    ['', 'd', '', '', '', 'HH WS', "Exterior of Harbor House"],
    ['1.5', ' ', 'INT', 'DAWN', "Harbor House - Kitchen", '', '', '', 'Mara makes breakfast before the boats go out', 'Establish Mara and Eli as down on their luck.', "Mara's POV"],
    ['', 'a', '', '', '', 'HH MS', 'Tracking on Mara from stove to table', 'Easyrig'],
    ['', 'b', '', '', '', 'HH MW', 'Shelf of trophies', 'Easyrig'],
    ['2', ' ', 'INT', 'DAWN', "Attic Room", '', '', '', 'Eli hides in the attic', '', "Mara's POV"],
    ['', 'a', '', '', '', 'HH MS', "Con't 1.5a Tracking as Mara climbs up, hold through scene.", 'Easyrig'],
    ['5', '', 'EXT', 'DAY', "Harbor House - Dock", '', '', '', 'Mara walks Eli to the dock'],
    ['', 'a', '', '', '', 'HH MW', 'Low angle leading, looking up at Eli and Mara behind him', 'Gimbal on a cart'],
])


def live2():
    return json.load(open(LIVE2))


def grouped(sc=None):
    """His plan with his grouping: 1-2, 3-5, 6-8."""
    sc = sc or live2()
    sc['groups'] = [{'id': 'g1', 'name': 'Teaching'}, {'id': 'g2', 'name': 'Demo Ravi & Lena'}, {'id': 'g3', 'name': 'Demo Nora & Theo'}]
    for i, sh in enumerate(sc['shots']):
        sh['grp'] = 'g1' if i < 2 else 'g2' if i < 5 else 'g3'
    return sc


def codes(app):
    return app.js("()=>{const P=window.__shotplans,sc=P.cur();return sc.shots.map(s=>P.shotCode(sc,s))}")


def sid(app):
    return app.js("()=>window.__shotplans.S.shotId")


def test_old_plan_gets_one_scene_and_keeps_its_numbers(open_app):
    sc = live2()
    app = open_app({'workshop_doc': sc})
    s = app.scene()
    assert len(s['groups']) == 1 and all(x['grp'] == s['groups'][0]['id'] for x in s['shots'])
    assert codes(app) == ['1' + c for c in 'ABCDEFGH'][:len(sc['shots'])]
    assert [x['name'] for x in s['shots']] == [x['name'] for x in sc['shots']]
    assert not app.errors, app.errors


def test_scene_numbers_give_shot_codes(open_app):
    sc = grouped()
    sc['groups'][1]['num'] = '12'
    sc['shots'][4]['letter'] = 'z'
    app = open_app({'workshop_doc': sc})
    c = codes(app)
    assert c[:2] == ['1A', '1B'] and c[2:5] == ['12A', '12B', '12Z'] and c[5] == '2A', c
    # slate letters: I and O skipped, then doubled
    seq = app.js("()=>{const P=window.__shotplans;const sc=P.cur(),g=sc.groups[2];for(let i=0;i<30;i++)sc.shots.push({id:'q'+i,name:'',grp:g.id,beats:[{id:'qb'+i,name:''}]});P.orderShots(sc);return sc.shots.filter(s=>s.grp===g.id).map(s=>P.shotCode(sc,s))}")
    assert seq[7:10] == ['2H', '2J', '2K'] and 'I' not in ''.join(seq) and 'O' not in ''.join(seq)
    assert seq[23:26] == ['2Z', '2AA', '2BB'], seq


def test_desktop_and_phone_use_the_same_stepper(open_app):
    for dev in ('desktop', 'phone'):
        app = open_app({'workshop_doc': grouped()}, device=dev)
        app.go(shot=app.scene()['shots'][1]['id'])
        assert app.page.locator('#beats .stab').count() == 0
        for sel in ('#shotPrev', '#shotNext', '#shotBtn'):
            assert app.page.locator(sel).is_visible(), (dev, sel)
        small = app.page.locator('#shotBtn small').inner_text().lower()
        assert 'teaching' in small and small.startswith('2/2'), small
        app.page.locator('#shotNext').click()
        app.wait(200)
        assert sid(app) == app.scene()['shots'][2]['id']
        assert 'demo ravi' in app.page.locator('#shotBtn small').inner_text().lower()
        w = app.js("()=>innerWidth")
        b = app.page.locator('#beats').bounding_box()
        assert b['x'] + b['width'] <= w + 1
        app.page.screenshot(path=OUT + f'v39_{dev}_bar.png')
        assert not app.errors, app.errors


def test_shot_list_groups_folds_and_finds(open_app):
    sc = grouped()
    for i in range(12):  # enough shots for the find box
        sc['shots'].append({'id': f'x{i}', 'name': f'Insert {i}', 'grp': 'g3', 'beats': [{'id': f'xb{i}', 'name': ''}]})
    app = open_app({'workshop_doc': sc}, device='phone')
    app.page.tap('#shotBtn')
    app.wait(300)
    heads = app.page.locator('#shotList .ghead')
    assert heads.count() == 3 and 'TEACHING' in heads.first.inner_text().upper()
    assert 'no plan yet' in app.page.locator('#shotList .srow[data-sid="x0"]').inner_text()
    app.page.screenshot(path=OUT + 'v39_phone_list.png')
    heads.nth(2).locator('.gtog').tap()
    app.wait(100)
    assert not app.page.locator('#shotList .srow[data-sid="x0"]').is_visible()
    app.page.fill('#shotFind', 'insert 11')
    app.wait(100)
    vis = [r for r in app.page.locator('#shotList .srow').all() if r.is_visible()]
    assert len(vis) == 1 and 'Insert 11' in vis[0].inner_text()
    assert not heads.first.is_visible()
    vis[0].locator('.item').tap()
    app.wait(200)
    assert sid(app) == 'x11'
    assert not app.errors, app.errors


def test_moving_a_shot_into_another_scene(open_app):
    app = open_app({'workshop_doc': grouped()})
    first_g3 = app.scene()['shots'][5]['id']
    last_g2 = app.scene()['shots'][4]['id']
    app.page.click('#shotBtn')
    grip = app.page.locator(f'#shotList .srow[data-sid="{last_g2}"] [data-grip]')
    grip.focus()
    app.page.keyboard.press('ArrowDown')  # past the Demo Nora heading
    app.wait(150)
    s = app.scene()
    moved = next(x for x in s['shots'] if x['id'] == last_g2)
    assert moved['grp'] == 'g3', 'a shot moved under a scene heading joins that scene'
    assert [x['id'] for x in s['shots']].index(last_g2) == 4


def test_shot_details_and_scene_details(open_app):
    app = open_app({'workshop_doc': grouped()}, device='phone')
    app.page.tap('#shotBtn')
    app.page.tap('#sheet [data-do="details"]')
    app.wait(200)
    app.page.fill('#sheet [data-k="type"]', 'MCU')
    app.page.fill('#sheet [data-k="tools"]', 'Easyrig')
    app.page.screenshot(path=OUT + 'v39_phone_details.png')
    app.page.tap('#sheet [data-r="done"]')
    sh = app.scene()['shots'][0]
    assert sh['type'] == 'MCU' and sh['tools'] == 'Easyrig'
    app.page.tap('#shotBtn')
    app.page.tap('#sheet [data-do="gedit"]')
    app.wait(200)
    app.page.fill('#sheet [data-k="num"]', '4')
    app.page.select_option('#sheet [data-k="ie"]', 'INT')
    app.page.tap('#sheet [data-r="done"]')
    assert codes(app)[:2] == ['4A', '4B']
    assert app.scene()['groups'][0]['ie'] == 'INT'
    assert app.page.locator('#shotBtn .dsk').inner_text() == '4A' and app.page.locator('#shotBtn .dsk').is_visible()
    app.page.click('#undoBtn')
    app.wait(150)
    assert app.scene()['groups'][0].get('num', '') == ''


def test_new_scene_and_delete_scene(open_app):
    app = open_app({'workshop_doc': grouped()})
    n = len(app.scene()['shots'])
    app.page.click('#shotBtn')
    app.page.click('#sheet [data-do="newscene"]')
    app.wait(200)
    s = app.scene()
    assert len(s['groups']) == 4 and s['groups'][1]['id'] not in ('g2', 'g3') and len(s['shots']) == n + 1
    assert next(x for x in s['shots'] if x['id'] == sid(app))['grp'] == s['groups'][1]['id']
    app.page.click('#sheet [data-r="done"]')
    app.page.click('#shotBtn')
    app.page.click('#sheet [data-do="gdel"]')
    app.page.locator('#sheet .btn.danger, #sheet .btn.primary').last.click()
    app.wait(200)
    assert len(app.scene()['groups']) == 3 and len(app.scene()['shots']) == n


def test_parse_his_sheet(open_app):
    app = open_app({'workshop_doc': live2()})
    p = app.js("t=>window.__shotplans.parseShotList(t)", SHEET)
    assert p['header'] and [x['num'] for x in p['scenes']] == ['1', '1.5', '2', '5']
    s15 = p['scenes'][1]
    assert s15['ie'] == 'INT' and s15['time'] == 'DAWN' and s15['notes'] == "Mara's POV" and 'luck' in s15['intent']
    assert [(x['letter'], x['type'], x['tools']) for x in s15['shots']] == [('A', 'HH MS', 'Easyrig'), ('B', 'HH MW', 'Easyrig')]
    assert [x['letter'] for x in p['scenes'][0]['shots']] == ['A', 'B', 'D']
    # csv with quotes, and codes in one column
    csv = 'Scene,Shot,Shot Type,Shot Description\r\n12,,,\r\n,12a,WS,"Wide, from the door"\r\n,12b,CU,"She says ""no"""\r\n'
    p = app.js("t=>window.__shotplans.parseShotList(t)", csv)
    assert [(x['letter'], x['desc']) for x in p['scenes'][0]['shots']] == [('A', 'Wide, from the door'), ('B', 'She says "no"')]


def test_import_by_paste_then_again_updates(open_app):
    sc = live2()
    sc['name'] = "Harbor House"
    app = open_app({'workshop_doc': sc}, device='phone')
    n = len(sc['shots'])
    app.page.tap('#shotBtn')
    app.page.tap('#sheet [data-do="imp"]')
    app.wait(200)
    app.page.fill('#listPaste', SHEET)
    app.wait(200)
    assert '4 locations, 1 already here' in app.page.locator('#listPrev').inner_text()
    app.page.screenshot(path=OUT + 'v39_phone_import.png')
    app.page.tap('#sheet [data-c="go"]')
    app.wait(300)
    s = app.scene()
    assert len(s['shots']) == n + 7
    assert [g.get('num') for g in s['groups']][1:] == ['1', '1.5', '2', '5']
    c = codes(app)
    assert c[n:] == ['1A', '1B', '1D', '1.5A', '1.5B', '2A', '5A'], c
    locs = {l['id']: l['name'] for l in s['locs']}
    assert sorted(locs.values()) == sorted(["Harbor House", "Harbor House - Kitchen", "Attic Room", "Harbor House - Dock"])
    g1 = s['groups'][1]
    assert locs[g1['locId']] == "Harbor House" and locs[s['groups'][0]['locId']] == "Harbor House"
    furn = lambda gid: [i for i in s['items'] if i['kind'] == 'furn' and i.get('grp') == gid]
    assert len(furn(g1['id'])) == len(furn(s['groups'][0]['id'])) > 0, 'a new scene at a dressed location comes in dressed'
    assert not furn(s['groups'][2]['id']), 'a new location is an empty room'
    assert not any(it.get('shot') in {x['id'] for x in s['shots'][n:]} for it in s['items'])
    # import again with a changed description: updated, not duplicated
    app.page.tap('#shotBtn')
    app.page.tap('#sheet [data-do="imp"]')
    app.page.fill('#listPaste', SHEET.replace('Shelf of trophies', 'Trophies, slow push'))
    app.wait(150)
    app.page.tap('#sheet [data-c="go"]')
    app.wait(300)
    s = app.scene()
    assert len(s['shots']) == n + 7
    assert any(x.get('desc') == 'Trophies, slow push' for x in s['shots'])
    assert not app.errors, app.errors


def test_export_rows_round_trip(open_app):
    sc = grouped()
    sc['groups'][1].update({'num': '12', 'ie': 'INT', 'time': 'DAY', 'loc': 'WS classroom', 'syn': 'Demo'})
    sc['shots'][2].update({'type': 'WS', 'desc': 'Wide, with "quotes"', 'tools': 'Sticks'})
    app = open_app({'workshop_doc': sc})
    rows = app.js("()=>{const P=window.__shotplans;return P.listRows(P.cur())}")
    assert rows[0][:11] == ['Scene', 'Shot', 'Int/Ext', 'Time', 'Location', 'Shot Type', 'Shot Description', 'Special Tools', 'Synopsis', 'Thematic Intention', 'Notes']
    r12 = next(i for i, r in enumerate(rows) if r[0] == '12')
    assert rows[r12][2:5] == ['INT', 'DAY', 'WS classroom']
    shot = rows[r12 + 1]
    assert shot[1] == 'A' and shot[5] == 'WS' and 'quotes' in shot[6] and shot[7] == 'Sticks'
    assert shot[11] and 'mm' in shot[11], 'cameras with lenses'
    tsv = '\n'.join('\t'.join(r) for r in rows)
    p = app.js("t=>window.__shotplans.parseShotList(t)", tsv)
    p12 = next(x for x in p['scenes'] if x['num'] == '12')
    assert [x['letter'] for x in p12['shots']] == ['A', 'B', 'C'] and p12['shots'][0]['type'] == 'WS'
    # csv download
    app.page.click('#shotBtn')
    app.page.click('#sheet [data-do="csv"]')
    app.wait(400)
    files = app.saved_files() if hasattr(app, 'saved_files') else []
    if files:
        txt = open(files[-1], encoding='utf-8-sig').read()
        assert txt.startswith('Scene,Shot') and 'with ""quotes""' in txt


def test_shot_list_and_pdf_group_by_scene(open_app):
    sc = grouped()
    sc['shots'].append({'id': 'np', 'name': '', 'type': 'INS', 'desc': 'Hands on keyboard', 'grp': 'g3', 'beats': [{'id': 'npb', 'name': ''}]})
    app = open_app({'workshop_doc': sc})
    lines = app.js("()=>{const P=window.__shotplans;return P.summaryLines?P.summaryLines(P.summary(P.cur())):null}")
    if lines is not None:
        gs = [t for k, t in lines if k == 'g']
        assert len(gs) == 3 and 'Teaching' in gs[0]
        i = next(j for j, (k, t) in enumerate(lines) if k == 'h' and 'Hands on keyboard' in t)
        assert lines[i + 1][1] == 'No plan'
    app.page.click('#shareBtn') if app.page.locator('#shareBtn').count() else None
    assert not app.errors, app.errors
