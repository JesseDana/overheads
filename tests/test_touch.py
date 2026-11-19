"""Phone touch: tap-through (a tap's own click must not land on the sheet it opens) and the 30 px swallow limit."""
import pytest
import sp


def _phone(open_app):
    sc = sp.room_scene()
    return open_app({'room': sc}, device='phone')


def test_tap_opens_sheet_without_editing(open_app):
    app = _phone(open_app)
    app.go(shot='s1')
    x, y = app.item_px('key')
    before = app.item('key')
    app.page.touchscreen.tap(x, y)
    app.wait(600)
    assert app.S('sel') == 'key'
    assert app.js("()=>!document.querySelector('#insp-m').hidden"), 'phone edit sheet should open on tap'
    assert app.item('key') == before, 'a plain tap changed the light'
    assert app.hist_len() == 0, 'a plain tap was recorded in undo'


def test_tap_click_does_not_land_on_control_under_finger(open_app):
    """Put the light exactly under a control of its own phone sheet (a slider or button), then tap it: the
    follow-on click must be swallowed (round-1 bug: tapping a light changed broad to point)."""
    app = _phone(open_app)
    app.go(shot='s1')
    x, y = app.item_px('key')
    app.page.touchscreen.tap(x, y)
    app.wait(500)
    cv = app.js("()=>{const r=document.querySelector('#cv').getBoundingClientRect();return [r.top,r.bottom]}")
    ctl = app.js("""([t,b])=>{const els=[...document.querySelectorAll('#insp-m input,#insp-m select,#insp-m [data-act]')].filter(e=>e.offsetParent&&e.dataset.act!=='close');
      for(const e of els){const r=e.getBoundingClientRect(),cx=r.left+Math.min(r.width/2,40),cy=r.top+r.height/2;if(cy>t+10&&cy<b-10&&cx>10)return [cx,cy,e.dataset.f||e.dataset.act]}return null}""", cv)
    if not ctl:
        pytest.skip('no control of the light sheet sits over the plan')
    bx, by, what = ctl
    before = app.item('key')
    app.go(shot='s1')  # deselect: sheet closes
    app.page.click('#layersBtn'); app.page.click('#sheet [data-vw="frames0"]'); app.page.keyboard.press('Escape')  # hide the phone frames strip so the plan under the control is reachable
    app.wait(100)
    s = app.S('view')['s']
    app.set_view(x=3 - bx / s, y=9 - (by - cv[0]) / s)
    px, py = app.item_px('key')
    assert abs(px - bx) < 2 and abs(py - by) < 2
    app.page.touchscreen.tap(px, py)
    app.wait(600)
    assert app.S('sel') == 'key', 'tap at %s,%s selected %r (top element %s); control was %r' % (px, py, app.S('sel'), app.js("([x,y])=>{const e=document.elementFromPoint(x,y);return e&&e.outerHTML.slice(0,120)}", [px, py]), what)
    assert app.item('key') == before, 'the tap fell through to the sheet control %r and edited the light' % what
    assert app.hist_len() == 0


def test_swallow_is_limited_to_the_lift_point(open_app):
    """A second tap on a different control right after (within 450 ms, more than 30 px away) must work."""
    app = _phone(open_app)
    app.go(shot='s1')
    x, y = app.item_px('bob')
    app.page.touchscreen.tap(x, y)
    app.wait(60)
    b = app.page.locator('#beatNext').bounding_box()
    app.page.touchscreen.tap(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2)
    app.wait(300)
    assert app.S('beat') == 1, 'a quick second tap elsewhere was swallowed'


def test_touch_drag_threshold_and_move(open_app):
    """A finger wobble under 10 px is a tap (no move); a real drag moves the person and is one undo step."""
    app = _phone(open_app)
    app.go(shot='s1')
    x, y = app.item_px('bob')
    p0 = app.pose('bob')
    app.touch_drag(x, y, x + 6, y + 3, steps=3)
    assert app.pose('bob')['x'] == p0['x'] and app.hist_len() == 0, 'a 6 px wobble moved the person'
    app.go(shot='s1')
    x, y = app.item_px('bob')
    s = app.S('view')['s']
    app.touch_drag(x, y, x + 2 * s, y, steps=10)
    app.wait(200)
    assert abs(app.pose('bob')['x'] - (p0['x'] + 2)) < .3
    assert app.hist_len() == 1
