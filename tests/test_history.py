"""Undo/redo: navigation to the changed shot and beat, labels, redo, no-op drags, nudge merging."""
import sp


def room(open_app):
    app = open_app({'room': sp.room_scene()})
    app.go(shot='s1')
    return app


def nudge(app, id, key='ArrowRight', n=1):
    app.select(id)
    for _ in range(n):
        app.page.keyboard.press(key)
    app.wait(50)


def test_undo_returns_to_changed_shot_and_beat_and_names_it(open_app):
    app = room(open_app)
    app.go(shot='s2', beat=1)
    x0 = app.item('ann2')['k'][1]['x']
    nudge(app, 'ann2', n=2)
    assert app.item('ann2')['k'][1]['x'] == x0 + .5
    app.go(shot='s1', beat=0)
    app.page.keyboard.press('Control+z')
    app.wait(100)
    assert app.S('shotId') == 's2' and app.S('beat') == 1, 'undo did not take me to the shot and beat it changed'
    assert app.item('ann2')['k'][1]['x'] == x0
    t = app.toast()
    assert t.startswith('Undone') and 'Ann' in t and 'Shot 1B' in t and 'beat 2' in t, t
    assert app.js("()=>!document.querySelector('#redoBtn').disabled"), 'Redo button not enabled after undo'


def test_redo_reapplies_and_navigates(open_app):
    app = room(open_app)
    app.go(shot='s2', beat=1)
    x0 = app.item('ann2')['k'][1]['x']
    nudge(app, 'ann2')
    app.page.keyboard.press('Control+z')
    app.go(shot='s1', beat=0)
    app.page.keyboard.press('Control+Shift+z')
    app.wait(100)
    assert app.item('ann2')['k'][1]['x'] == x0 + .25
    assert app.S('shotId') == 's2' and app.S('beat') == 1
    assert app.toast().startswith('Redone')


def test_redo_button_click(open_app):
    app = room(open_app)
    nudge(app, 'bob')
    app.page.click('#undoBtn')
    app.page.click('#redoBtn')
    assert app.item('bob')['k'][0]['x'] == 11.25


def test_new_edit_clears_redo(open_app):
    app = room(open_app)
    nudge(app, 'bob')
    app.page.keyboard.press('Control+z')
    app.wait(1300)  # outside the nudge-merge window; the inside case is test_nudge_right_after_undo_is_its_own_step
    nudge(app, 'ann', 'ArrowDown')
    assert app.js("()=>document.querySelector('#redoBtn').disabled")
    app.page.keyboard.press('Control+Shift+z')
    assert app.toast() == 'Nothing to redo'


def test_undo_deletion_brings_it_back(open_app):
    app = room(open_app)
    app.select('tbl')
    app.page.keyboard.press('Delete')
    assert app.item('tbl') is None
    app.page.keyboard.press('Control+z')
    assert app.item('tbl') is not None
    assert 'brought back' in app.toast() and 'Table' in app.toast()


def test_drag_out_and_back_is_not_recorded(open_app):
    app = room(open_app)
    x, y = app.item_px('bob')
    m = app.page.mouse
    m.move(x, y); m.down(); m.move(x + 80, y + 40, steps=5); m.move(x, y, steps=5); m.up()
    app.wait(150)
    assert app.item('bob')['k'][0]['x'] == 11
    assert app.hist_len() == 0, 'a drag that ended where it started was recorded'


def test_tap_and_pan_not_recorded(open_app):
    app = room(open_app)
    x, y = app.item_px('bob')
    app.page.mouse.click(x, y)
    ex, ey = app.to_px(8, 8.5)
    app.mouse_drag(ex, ey, ex + 100, ey + 50)
    assert app.hist_len() == 0


def test_nudges_in_a_run_merge_into_one_step(open_app):
    app = room(open_app)
    nudge(app, 'bob', n=4)
    assert app.hist_len() == 1, 'four quick nudges made %d undo steps' % app.hist_len()
    app.wait(1400)
    app.page.keyboard.press('ArrowRight')
    assert app.hist_len() == 2, 'a nudge after a pause should start a new step'
    app.page.keyboard.press('Control+z')
    assert app.item('bob')['k'][0]['x'] == 12


def test_turn_runs_merge_too(open_app):
    app = room(open_app)
    nudge(app, 'bob', ']', 3)
    assert app.hist_len() == 1
    app.page.keyboard.press('Control+z')
    assert app.item('bob')['k'][0]['r'] % 360 == 180


def test_noop_keypress_on_locked_item_not_recorded(open_app):
    sc = sp.room_scene()
    next(i for i in sc['items'] if i['id'] == 'tbl')['lock'] = True
    app = open_app({'room': sc})
    app.go(shot='s1')
    nudge(app, 'tbl', n=2)
    assert app.item('tbl')['x'] == 3
    assert app.hist_len() == 0, 'nudging a locked item recorded an empty undo step'


def test_nudge_right_after_undo_is_its_own_step(open_app):
    """Nudge, Cmd+Z, nudge again within the 1.2 s merge window: the second nudge must be undoable and must not be
    thrown away by Redo."""
    app = room(open_app)
    app.select('bob')
    app.page.keyboard.press('ArrowRight')
    app.page.keyboard.press('Control+z')
    app.page.keyboard.press('ArrowDown')  # same selection, well inside 1.2 s
    assert app.item('bob')['k'][0]['y'] == 5.25
    app.page.keyboard.press('Control+z')
    t = app.toast()
    assert app.item('bob')['k'][0]['y'] == 5, 'the nudge after an undo could not be undone (toast: %r)' % t


def test_nudge_run_does_not_span_beats(open_app):
    """Nudge in beat 1, switch to beat 2, nudge again within 1.2 s: one Cmd+Z should undo only the beat-2 nudge."""
    app = room(open_app)
    app.select('ann')
    app.page.keyboard.press('ArrowDown')
    app.page.keyboard.press('2')
    app.page.keyboard.press('ArrowDown')
    k = app.item('ann')['k']
    assert (k[0]['y'], k[1]['y']) == (5.25, 5.25)
    app.page.keyboard.press('Control+z')
    k = app.item('ann')['k']
    assert (k[0]['y'], k[1]['y']) == (5.25, 5), 'one undo reverted nudges in two beats: %s' % [q['y'] for q in k]
