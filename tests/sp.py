"""Shared helpers for the Overheads regression suite.

Black-box by design: tests drive the real app file through the DOM, keyboard, mouse and touch, and read state only
through the read-only handle the app exposes (window.__shotplans = {S, cur, inShot, poseT, poseAt, frameInfo,
lightTerms}). Nothing is injected into the app. The app path comes from the harness, which honours SHOTPLANS_APP.
"""
import copy, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
from harness import STUB, JSPDF  # noqa: E402

APP = harness.APP  # OVERHEADS_APP or ../index.html
WS = json.load(open(os.path.join(HERE, 'seeds', 'workshop.json')))

# In-page mock of the host's db capability (collection('scenes'): onSnapshot, doc(id).get/set/delete, with
# hasPendingWrites echoes). Tests play "another device / Claude" through window.__db.remote(id, data).
# Adapted from review/work/r2-data-integrity/lib.py so the suite does not depend on a reviewer's work folder.
DBMOCK = r"""
(()=>{const store=new Map();const subs=[];let getDelay=0;
 const snapOf=(pending)=>({docs:[...store.entries()].map(([id,d])=>({id,data:()=>JSON.parse(JSON.stringify(d)),metadata:{hasPendingWrites:pending&&pending.has(id)}}))});
 const emit=(pending)=>subs.forEach(f=>f(snapOf(pending)));
 const col={onSnapshot:(f)=>{subs.push(f);setTimeout(()=>f(snapOf()),30);return ()=>{}},
  doc:(id)=>({get:async()=>{await new Promise(r=>setTimeout(r,getDelay));const d=store.get(id);return {exists:!!d,data:()=>d&&JSON.parse(JSON.stringify(d))}},
    set:async(o)=>{window.__db.log.push({who:'app',id,t:Date.now()});store.set(id,JSON.parse(JSON.stringify(o)));emit(new Set([id]));await new Promise(r=>setTimeout(r,20));emit()},
    delete:async()=>{store.delete(id);emit()}})};
 window.__db={store,log:[],setGetDelay:v=>getDelay=v,
   seed:(id,d)=>store.set(id,d),
   remote:(id,d)=>{window.__db.log.push({who:'remote',id,t:Date.now()});if(d===null)store.delete(id);else store.set(id,JSON.parse(JSON.stringify(d)));emit()},
   read:(id)=>JSON.parse(JSON.stringify(store.get(id)||null))};
 // other collections (usage counters, snapshots) live apart from scenes, as in the host
 const other=new Map();const ocol=n=>{if(!other.has(n))other.set(n,new Map());const m=other.get(n);
   return {onSnapshot:()=>()=>{},doc:(id)=>({get:async()=>({exists:m.has(id),data:()=>m.get(id)}),set:async(o)=>{m.set(id,JSON.parse(JSON.stringify(o)))},delete:async()=>{m.delete(id)}})}};
 window.__db.other=other;
 const prev=window.claude.use;window.claude.use=async(n)=>n==='db'?{collection:(c)=>c==='scenes'?col:ocol(c)}:prev(n);})();
"""

DEVICES = {
    'phone': dict(viewport={'width': 393, 'height': 852}, device_scale_factor=2, has_touch=True, is_mobile=True),
    'tablet': dict(viewport={'width': 820, 'height': 1180}, device_scale_factor=2, has_touch=True, is_mobile=True),
    'desktop': dict(viewport={'width': 1440, 'height': 900}, device_scale_factor=1),
}


def page_html():
    """The app is a full document; inside claude.ai the same body runs inside the host's skeleton."""
    return open(APP, encoding='utf8').read()


def seed_js(scenes, db=False, extra_local=None):
    """scenes: {id: doc}. Local mode seeds localStorage once per context; db mode seeds the mock store on every load."""
    extra = ''.join('localStorage.setItem(%s,%s);' % (json.dumps(k), json.dumps(v if isinstance(v, str) else json.dumps(v)))
                    for k, v in (extra_local or {}).items())
    if db:
        return ';'.join('window.__db.seed(%s,%s)' % (json.dumps(k), json.dumps(v)) for k, v in scenes.items()) + \
            ";if(!localStorage.getItem('__seeded')){localStorage.clear();%s localStorage.setItem('__seeded','1')}" % extra
    sets = ''.join('localStorage.setItem(%s,%s);' % (json.dumps('shotplans:' + k), json.dumps(json.dumps(v))) for k, v in scenes.items())
    return ("if(!localStorage.getItem('__seeded')){localStorage.clear();localStorage.setItem('shotplans:index',%s);%s%s"
            "localStorage.setItem('__seeded','1')}" % (json.dumps(json.dumps(list(scenes))), sets, extra))


# ---------------------------------------------------------------- scenes
def room_scene(name='Test room', two_beats=True):
    """A 16 x 14 ft room. Shot 1: Ann (moves between beats) and Bob, camera A locked off, camera B moving.
    Shot 2: Ann alone, camera C. Camera looks up the plan (r=0) at talent facing it (r=180)."""
    walls = [((0, 0), (16, 0), 'Back wall'), ((16, 0), (16, 14), 'Right wall'), ((16, 14), (0, 14), 'Near wall'), ((0, 14), (0, 0), 'Left wall')]
    items = [{'id': 'w%d' % i, 'kind': 'wall', 'name': n, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1], 't': .45} for i, (a, b, n) in enumerate(walls)]
    nb = 2 if two_beats else 1
    ann = [{'x': 6, 'y': 5, 'r': 180}, {'x': 9, 'y': 5, 'r': 180}][:nb]
    items += [
        {'id': 'ann', 'kind': 'char', 'cast': 'c_ann', 'shot': 's1', 'k': ann},
        {'id': 'bob', 'kind': 'char', 'cast': 'c_bob', 'shot': 's1', 'k': [{'x': 11, 'y': 5, 'r': 180}] * nb},
        {'id': 'camA', 'kind': 'cam', 'name': 'A', 'color': '#a383d8', 'shot': 's1', 'held': True, 'k': [{'x': 8, 'y': 12, 'r': 0, 'f': 35, 'h': 5}] * nb},
        {'id': 'camB', 'kind': 'cam', 'name': 'B', 'color': '#6dbb72', 'shot': 's1', 'held': False,
         'k': [{'x': 12, 'y': 12, 'r': -10, 'f': 50, 'h': 5}, {'x': 12, 'y': 10, 'r': -30, 'f': 50, 'h': 5}][:nb]},
        {'id': 'ann2', 'kind': 'char', 'cast': 'c_ann', 'shot': 's2', 'k': [{'x': 8, 'y': 5, 'r': 180}] * nb},
        {'id': 'camC', 'kind': 'cam', 'name': 'C', 'color': '#ef9a50', 'shot': 's2', 'held': True, 'k': [{'x': 8, 'y': 11, 'r': 0, 'f': 50, 'h': 5}] * nb},
        {'id': 'sofa1', 'kind': 'furn', 'shape': 'sofa', 'label': 'Sofa', 'x': 4, 'y': 1.8, 'w': 7, 'h': 3, 'r': 0},
        {'id': 'stool1', 'kind': 'furn', 'shape': 'barstool', 'label': 'Bar stool', 'x': 13.5, 'y': 3, 'w': 1.4, 'h': 1.4, 'r': 0},
        {'id': 'tbl', 'kind': 'furn', 'shape': 'table', 'label': 'Table', 'x': 3, 'y': 10, 'w': 4, 'h': 2.2, 'r': 0},
        {'id': 'key', 'kind': 'light', 'name': 'Key', 'type': 'broad', 'w': 3, 'x': 3, 'y': 9, 'r': 30, 'level': 80, 'spread': 40},
    ]
    beats = [{'id': 'b1', 'name': 'Sit'}, {'id': 'b2', 'name': 'Stand'}][:nb]
    return {'name': name, 'updatedAt': 1000, 'sensor': 'ff', 'notes': 'Test notes.', 'layerState': {},
            'cast': [{'id': 'c_ann', 'name': 'Ann', 'color': '#e5675f'}, {'id': 'c_bob', 'name': 'Bob', 'color': '#5b9be0'}],
            'shots': [{'id': 's1', 'name': 'Two', 'beats': beats}, {'id': 's2', 'name': 'Single', 'beats': [{'id': 'b3', 'name': ''}, {'id': 'b4', 'name': ''}][:nb]}],
            'items': items}


def workshop():
    return copy.deepcopy(WS)


# ---------------------------------------------------------------- page wrapper
class App:
    """A page plus small helpers. All coordinates are plan feet unless named *_px."""

    def __init__(self, page, out_dir):
        self.page, self.out_dir = page, out_dir
        self.errors = []
        page.on('pageerror', lambda e: self.errors.append(str(e)))

    # state
    def js(self, expr, arg=None):
        return self.page.evaluate(expr, arg) if arg is not None else self.page.evaluate(expr)

    def S(self, key):
        return self.js("k=>{const v=window.__shotplans.S[k];return v instanceof Map||v instanceof Set?[...v]:JSON.parse(JSON.stringify(v??null))}", key)

    def scene(self):
        return self.js("()=>{const o=JSON.parse(JSON.stringify(window.__shotplans.cur()));if(o.stash){o.items=[...o.items,...o.stash];delete o.stash}return o}")

    def item(self, id):
        return self.js("id=>{const c=window.__shotplans.cur(),i=[...c.items,...(c.stash||[])].find(i=>i.id===id);return i?JSON.parse(JSON.stringify(i)):null}", id)

    def pose(self, id, beat=None):
        return self.js("([id,b])=>{const P=window.__shotplans,sc=P.cur(),it=sc.items.find(i=>i.id===id);return P.poseT(sc,it,b??P.S.beat)}", [id, beat])

    def hist_len(self):
        return self.js("()=>{const S=window.__shotplans.S;return (S.hist.get(S.curId)||[]).length}")

    def toast(self):
        return self.js("()=>{const t=document.querySelector('#toast');return t&&!t.hidden?t.textContent:''}")

    def stored(self, id):
        return self.js("id=>JSON.parse(localStorage.getItem('shotplans:'+id)||'null')", id)

    def db(self, id):
        return self.js("id=>window.__db.read(id)", id)

    def wait(self, ms):
        self.page.wait_for_timeout(ms)

    def go(self, scene=None, shot=None, beat=0):
        """Navigate without the UI (selection cleared), then re-render through the app's own key handler."""
        self.js("([sc,sh,b])=>{const S=window.__shotplans.S;if(sc)S.curId=sc;if(sh)S.shotId=sh;S.beat=b;S.t=null;S.sel=null;S.multi=[]}", [scene, shot, beat])
        self.page.keyboard.press('Escape')  # renderAll
        self.wait(80)

    def select(self, id):
        self.js("id=>{const S=window.__shotplans.S;S.sel=id;S.multi=[];S.sceneInsp=false}", id)
        self.rerender()

    def space(self, sp):
        self.page.click('#spaceSeg [data-space="%s"]' % sp)
        self.wait(250)

    def rerender(self):
        self.js("()=>window.dispatchEvent(new Event('resize'))")
        self.wait(220)

    # geometry
    def to_px(self, x, y):
        return self.js("([x,y])=>{const S=window.__shotplans.S,r=document.querySelector('#cv').getBoundingClientRect();return [r.left+(x-S.view.x)*S.view.s,r.top+(y-S.view.y)*S.view.s]}", [x, y])

    def item_px(self, id):
        p = self.js("id=>{const P=window.__shotplans,sc=P.cur(),it=sc.items.find(i=>i.id===id);if(it.kind==='char'||it.kind==='cam'){const q=P.poseT(sc,it,P.S.beat);return [q.x,q.y]}return [it.x,it.y]}", id)
        return self.to_px(*p)

    def set_view(self, s=None, x=None, y=None):
        self.js("([s,x,y])=>{const v=window.__shotplans.S.view;if(s!=null)v.s=s;if(x!=null)v.x=x;if(y!=null)v.y=y}", [s, x, y])
        self.rerender()

    def mouse_drag(self, x0, y0, x1, y1, steps=8, modifiers=()):
        m = self.page.mouse
        for k in modifiers:
            self.page.keyboard.down(k)
        m.move(x0, y0); m.down(); m.move(x1, y1, steps=steps); m.up()
        for k in modifiers:
            self.page.keyboard.up(k)
        self.wait(120)

    def drag_item_to(self, id, x, y, modifiers=()):
        sx, sy = self.item_px(id)
        tx, ty = self.to_px(x, y)
        self.mouse_drag(sx, sy, tx, ty, modifiers=modifiers)

    def touch_drag(self, x0, y0, x1, y1, steps=8):
        """A finger drag through CDP touch events (pointerType 'touch')."""
        cdp = self.page.context.new_cdp_session(self.page)
        pt = lambda x, y: [{'x': x, 'y': y, 'id': 1, 'radiusX': 4, 'radiusY': 4, 'force': 1}]
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': pt(x0, y0)})
        for i in range(1, steps + 1):
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': pt(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)})
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        self.wait(150)

    def open_more(self, which):
        self.page.click('#moreBtn')
        self.page.click('#sheet [data-m="%s"]' % which)

    def saved_files(self):
        out = []
        import base64
        for f in self.js('window.__saved'):
            fp = os.path.join(self.out_dir, f['filename'])
            open(fp, 'wb').write(base64.b64decode(f['b64']))
            out.append(fp)
        return out
