"""Edge light traces the figure's outline and fades in smoothly; lights go to 200%."""
import math, re


def scene():
    return {'name': 'Rim test', 'schemaVersion': 2, 'cast': [{'id': 'c1', 'name': 'Maya', 'color': '#e5675f'}], 'rig': [{'id': 'rA', 'name': 'A'}],
            'shots': [{'id': 's1', 'name': '', 'beats': [{'id': 'b1', 'name': ''}]}],
            'items': [{'id': 'm', 'kind': 'char', 'shot': 's1', 'cast': 'c1', 'k': [{'x': 8, 'y': 5, 'r': 180, 'ps': 'stand'}]},
                      {'id': 'A', 'kind': 'cam', 'shot': 's1', 'rig': 'rA', 'held': True, 'k': [{'x': 8, 'y': 12, 'r': 0, 'f': 35, 'h': 5.2}]},
                      {'id': 'key', 'kind': 'light', 'type': 'broad', 'x': 4, 'y': 10, 'r': 40, 'w': 4, 'level': 80},
                      {'id': 'back', 'kind': 'light', 'type': 'point', 'x': 5, 'y': 1, 'r': 135, 'level': 100, 'spread': 40}]}


def rim_at(app, deg):
    """camera A's frame with the back light swung round the subject: deg 0 = beside the camera's line, 90 = straight behind"""
    return app.js("""a=>{const P=window.__shotplans,sc=P.cur(),L=sc.items.find(i=>i.id==='back'),r=a*Math.PI/180;
        L.x=8-4*Math.cos(r);L.y=5-4*Math.sin(r);L.r=Math.atan2(8-L.x,-(5-L.y))*180/Math.PI;
        const svg=P.frameInfo(sc,sc.items.find(i=>i.id==='A'),0,480).svg;
        return [...svg.matchAll(/fill-opacity="([0-9.]+)" mask="url\\(#[^)]*m\\d+\\)"/g)].map(m=>+m[1])}""", deg)


def test_edge_light_fades_in_without_a_jump(open_app):
    app = open_app({'rim': scene()})
    seen = []
    for deg in range(-20, 95, 5):
        ops = rim_at(app, deg)
        seen.append(max(ops) if ops else 0.0)
    assert seen[0] < 0.05, 'a light beside the camera gives no edge'
    assert max(seen) > 0.5, 'a light behind gives a strong edge'
    jumps = [b - a for a, b in zip(seen, seen[1:])]
    assert max(abs(j) for j in jumps) < 0.3, seen


def test_edge_light_follows_the_outline(open_app):
    """drawn as the figure's silhouette minus a shifted copy, not as a fixed stroke"""
    app = open_app({'rim': scene()})
    app.js("()=>0")
    svg = app.js("""()=>{const P=window.__shotplans,sc=P.cur();return P.frameInfo(sc,sc.items.find(i=>i.id==='A'),0,480).svg}""")
    masks = re.findall(r'<mask id="[^"]+m\d+"[^>]*>(.*?)</mask>', svg)
    assert masks, 'no edge-light mask'
    assert all('<circle' in m and ('<path' in m) for m in masks), 'mask holds the head and body shapes'
    assert 'stroke-opacity' not in svg.split('<mask')[1].split('</mask>')[0]


def test_light_output_goes_to_200(open_app):
    app = open_app({'rim': scene()})
    app.space('set')
    app.select('key')
    assert app.page.locator('#f-level').get_attribute('max') == '200'
