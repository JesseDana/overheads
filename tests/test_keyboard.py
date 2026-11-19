"""Keyboard shortcuts on desktop."""
import sp


def room(open_app):
    app = open_app({'room': sp.room_scene()})
    app.go(shot='s1')
    return app


def test_arrow_nudge_and_shift_nudge(open_app):
    app = room(open_app)
    app.select('bob')
    app.page.keyboard.press('ArrowLeft')
    app.page.keyboard.press('Shift+ArrowDown')
    p = app.item('bob')['k'][0]
    assert (p['x'], p['y']) == (10.75, 6)


def test_brackets_turn(open_app):
    app = room(open_app)
    app.select('bob')
    app.page.keyboard.press(']')
    assert app.item('bob')['k'][0]['r'] % 360 == 195
    app.page.keyboard.press('Shift+BracketLeft')  # '{' = 1 degree
    assert app.item('bob')['k'][0]['r'] % 360 == 194


def test_cmd_d_duplicates(open_app):
    app = room(open_app)
    n = len(app.scene()['items'])
    app.select('tbl')
    app.page.keyboard.press('Control+d')
    items = app.scene()['items']
    assert len(items) == n + 1
    assert app.S('sel') not in (None, 'tbl')


def test_cmd_a_selects_visible(open_app):
    sc = sp.room_scene()
    sc['layerState'] = {'light': {'hidden': True}}
    app = open_app({'room': sc})
    app.go(shot='s1')
    app.page.keyboard.press('Control+a')
    multi = set(app.S('multi'))
    assert {'ann', 'bob', 'camA', 'camB'} <= multi
    assert 'tbl' not in multi, 'Cmd+A in Shots picked up the set'
    assert 'key' not in multi, 'Cmd+A selected a hidden light'
    assert 'ann2' not in multi and 'camC' not in multi, 'Cmd+A reached into another shot'
    app.space('set')
    app.page.click('#cv', position={'x': 5, 'y': 300})
    app.page.keyboard.press('Control+a')
    multi = set(app.S('multi'))
    assert 'tbl' in multi and 'ann' not in multi and 'camA' not in multi


def test_page_down_up_change_shot(open_app):
    app = room(open_app)
    app.page.keyboard.press('PageDown')
    assert app.S('shotId') == 's2'
    app.page.keyboard.press('PageUp')
    assert app.S('shotId') == 's1'


def test_digits_and_arrows_change_beat(open_app):
    app = room(open_app)
    app.page.keyboard.press('2')
    assert app.S('beat') == 1
    app.page.keyboard.press('ArrowLeft')
    assert app.S('beat') == 0
    app.page.keyboard.press('9')
    assert app.S('beat') == 0


def test_question_mark_opens_keys(open_app):
    app = room(open_app)
    app.page.keyboard.press('?')
    assert app.js("()=>!document.querySelector('#sheet').hidden&&document.querySelector('#sheet').textContent.includes('Keyboard')")
    app.page.keyboard.press('Escape')
    assert app.js("()=>document.querySelector('#sheet').hidden")


def test_delete_and_escape(open_app):
    app = room(open_app)
    app.select('tbl')
    app.page.keyboard.press('Escape')
    assert app.S('sel') is None
    app.select('tbl')
    app.page.keyboard.press('Backspace')
    assert app.item('tbl') is None


def test_typing_in_a_field_does_not_trigger_shortcuts(open_app):
    app = room(open_app)
    app.select('camA')
    f = app.page.locator('#insp-d [data-f="name"]')
    f.click()
    app.page.keyboard.press('End')
    app.page.keyboard.press('Backspace')
    app.page.keyboard.type('2')
    app.page.keyboard.press('ArrowLeft')
    app.wait(200)
    assert app.item('camA') is not None, 'Backspace in the name field deleted the camera'
    assert app.S('beat') == 0, 'typing a digit in the name field switched beats'
    assert app.item('camA')['k'][0]['x'] == 8

