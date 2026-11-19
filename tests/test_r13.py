"""Copy for AI and Paste overhead: a round trip with any AI through the plan JSON."""
import json
from test_r11 import grouped, OUT

CAPTURE = "()=>{window.__copied=null;navigator.clipboard.writeText=async t=>{window.__copied=t}}"


def ai_reply(app):
    """what an AI might send back: words, a fenced block, a changed plan"""
    d = app.js("()=>{const P=window.__shotplans;return JSON.parse(JSON.stringify(P.cur()))}")
    if d.get('stash'):
        d['items'] += d.pop('stash')
    d['shots'][0]['name'] = 'Wide, from the door'
    furn = next(i for i in d['items'] if i['kind'] == 'furn' and i['id'] == 'f_sofa')
    furn['x'] += 2
    return 'Here is the updated plan. I renamed shot 1A and moved the sofa.\n\n```json\n' + json.dumps(d) + '\n```\nLet me know if you want more changes.'


def test_copy_for_ai_has_instructions_and_the_whole_plan(open_app):
    app = open_app({'workshop_doc': grouped()})
    app.js(CAPTURE)
    app.page.click('#moreBtn')
    app.page.click('#sheet [data-m="ai"]')
    app.wait(200)
    t = app.js("()=>window.__copied")
    assert t and t.startswith('Below is an overhead camera plan as JSON') and 'Paste overhead' in t
    plan = json.loads(t.split('Plan:\n', 1)[1])
    assert 'stash' not in plan and len(plan['groups']) == 3 and len(plan['items']) == len(app.scene()['items'])
    assert not app.errors, app.errors


def test_copy_falls_back_to_selectable_text_when_blocked(open_app):
    app = open_app({'workshop_doc': grouped()}, device='phone')
    app.js("()=>{navigator.clipboard.writeText=async()=>{throw new Error('blocked')}}")
    app.page.tap('#moreBtn')
    app.page.tap('#sheet [data-m="ai"]')
    app.wait(300)
    v = app.page.locator('#aiTxt').input_value()
    assert v.startswith('Below is an overhead camera plan')


def test_read_overhead_finds_the_plan(open_app):
    app = open_app({'workshop_doc': grouped()})
    reply = ai_reply(app)
    r = app.js("t=>window.__shotplans.readOverhead(t)", reply)
    assert r.get('list') and r['list'][0]['shots'][0]['name'] == 'Wide, from the door'
    bare = reply.split('```json\n', 1)[1].split('\n```', 1)[0]
    assert app.js("t=>window.__shotplans.readOverhead(t).list.length", bare) == 1
    assert app.js("t=>window.__shotplans.readOverhead('Sure! Here it is: ' + t + ' Hope that helps.').list.length", bare) == 1
    assert app.js("()=>window.__shotplans.readOverhead('no plan here').err")
    assert app.js("()=>window.__shotplans.readOverhead('{\"a\":1}').err")


def test_paste_overhead_replaces_the_plan_and_undo_restores(open_app):
    app = open_app({'workshop_doc': grouped()}, device='phone')
    x0 = app.item('f_sofa')['x']
    reply = ai_reply(app)
    app.page.tap('#moreBtn')
    app.page.tap('#sheet [data-m="paste"]')
    app.wait(200)
    app.page.fill('#ovPaste', reply)
    app.wait(200)
    prev = app.page.locator('#ovPrev').inner_text()
    assert '3 scenes, 8 shots' in prev and 'Sofa' in prev, prev
    app.page.screenshot(path=OUT + 'v42_phone_paste.png')
    app.page.tap('#sheet [data-c="replace"]')
    app.wait(300)
    s = app.scene()
    assert s['shots'][0]['name'] == 'Wide, from the door' and app.item('f_sofa')['x'] == x0 + 2
    assert len(s['groups']) == 3 and s['id'] if 'id' in s else True
    app.page.tap('#undoBtn')
    app.wait(300)
    assert app.item('f_sofa')['x'] == x0 and app.scene()['shots'][0]['name'] != 'Wide, from the door'
    assert not app.errors, app.errors


def test_paste_overhead_as_a_new_production(open_app):
    app = open_app({'workshop_doc': grouped()})
    reply = ai_reply(app)
    app.page.click('#sceneBtn')
    app.page.click('#sheet [data-do="paste"]')
    app.wait(200)
    app.page.fill('#ovPaste', reply)
    app.wait(150)
    app.page.click('#sheet [data-c="new"]')
    app.wait(400)
    assert app.js("()=>window.__shotplans.S.scenes.size") == 2
    assert app.scene()['shots'][0]['name'] == 'Wide, from the door'


def test_bad_paste_says_why_and_buttons_stay_off(open_app):
    app = open_app({'workshop_doc': grouped()})
    app.page.click('#moreBtn')
    app.page.click('#sheet [data-m="paste"]')
    app.page.fill('#ovPaste', 'I could not do that, sorry.')
    app.wait(150)
    assert 'No plan found' in app.page.locator('#ovPrev').inner_text()
    assert app.page.locator('#sheet [data-c="replace"]').is_disabled()
