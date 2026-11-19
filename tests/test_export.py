"""Shot list sheet and PDF export (text layer, page count)."""
import re
import subprocess
import sp


def shot_list(app):
    app.open_more('list')
    app.wait(200)
    return app.js("()=>[...document.querySelectorAll('#sheet .slist > div')].map(d=>[d.className,d.textContent])")


def room(open_app, **kw):
    app = open_app({'room': sp.room_scene()}, **kw)
    app.go(shot='s1')
    return app


def test_shot_list_structure(open_app):
    app = room(open_app)
    L = shot_list(app)
    heads = [t for c, t in L if c == 'sl-h']
    assert heads[:2] == ['Shot 1A · Two', 'Shot 1B · Single'] and 'Lights' in heads and 'Notes' in heads
    cams = [t for c, t in L if c == 'sl-c']
    assert any(t.startswith('A · 35mm') and t.endswith('locked off') for t in cams), cams
    assert any(t.startswith('B') and t.endswith('moves') for t in cams), cams


def test_shot_list_moves_words(open_app):
    app = room(open_app)
    L = shot_list(app)
    i = next(n for n, (c, t) in enumerate(L) if c == 'sl-c' and t.startswith('B'))
    b2 = L[i + 2][1]
    assert b2.startswith('Beat 2 Stand: PUSH IN 2′-0″ · PAN 20°'), b2


def test_shot_list_reads_people_with_side(open_app):
    sc = sp.room_scene()
    for i in sc['items']:
        if i['id'] == 'ann2':
            i['k'] = [{'x': 8, 'y': 5, 'r': 135}] * 2
    app = open_app({'room': sc})
    app.go(shot='s1')
    txt = '\n'.join(t for _, t in shot_list(app))
    assert re.search(r'Ann 6′-0″, 45° ¾ screen-right, ', txt), txt


def test_shot_list_lights_and_hidden_flag(open_app):
    sc = sp.room_scene()
    sc['layerState'] = {'light': {'hidden': True}}
    app = open_app({'room': sc})
    txt = [t for c, t in shot_list(app) if c == 'sl-t']
    assert any(t.startswith('L1 Key: broad, 3′-0″ wide · output 80%') and t.endswith('(hidden on the plan)') for t in txt), txt


def test_shot_list_copy_text(open_app, browser):
    app = room(open_app)
    app.page.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    shot_list(app)
    app.page.click('#sheet [data-c="copy"]')
    app.wait(300)
    txt = app.js("()=>navigator.clipboard.readText()")
    assert txt.startswith('Test room\nFull frame') and '\nSHOT 1A · TWO\n' in txt and '\n  A · 35mm' in txt, txt[:300]


def pdf_text(path, page=None):
    args = ['pdftotext', '-layout'] + (['-f', str(page), '-l', str(page)] if page else []) + [path, '-']
    return subprocess.run(args, capture_output=True, text=True).stdout


def pdf_pages(path):
    out = subprocess.run(['pdfinfo', path], capture_output=True, text=True).stdout
    return int(re.search(r'Pages:\s+(\d+)', out).group(1))


def export(app, which='pdf'):
    app.open_more(which)
    for _ in range(60):
        app.wait(250)
        if app.js('window.__saved.length'):
            break
        if app.toast().startswith('Export failed'):
            break
    files = app.saved_files()
    assert files, 'no PDF saved; toast: %r' % app.toast()
    return files[-1]


def test_pdf_all_shots(open_app):
    app = room(open_app)
    f = export(app)
    assert f.endswith('Test room.pdf')
    n = pdf_pages(f)
    assert n == 1 + 1 + 4, 'expected overview + 4 beat pages + shot list, got %d' % n
    p1 = pdf_text(f, n)
    assert 'Shot list' in p1 and 'Shot 1' in p1 and 'PUSH IN' in p1, p1[:500]
    p2 = pdf_text(f, 1)
    assert 'every setup' in p2 and 'Setups' in p2
    p3 = pdf_text(f, 2)
    assert 'Beat 1 of 2' in p3 and 'Lights' in p3 and 'L1 Key' in p3
    assert not app.errors


def test_pdf_this_shot(open_app):
    app = room(open_app)
    app.go(shot='s2')
    f = export(app, 'pdf1')
    assert f.endswith('Test room - shot 2.pdf')
    assert pdf_pages(f) == 1 + 2
    assert 'Shot 1B' in pdf_text(f, 2)


def test_pdf_notes_not_clipped(open_app):
    sc = sp.room_scene()
    sc['notes'] = ' '.join('word%d' % i for i in range(120)) + ' ENDOFNOTES'
    app = open_app({'room': sc})
    f = export(app)
    txt = re.sub(r'\s+', ' ', pdf_text(f))
    assert 'ENDOFNOTES' in txt and 'word60' in txt


def test_pdf_owners_scene(open_app):
    app = open_app()
    f = export(app)
    shots = len(sp.WS['shots'])
    beats = sum(len(s['beats']) for s in sp.WS['shots'])
    n = pdf_pages(f)
    assert 1 + 1 + beats <= n <= 3 + 1 + beats, n
    txt = pdf_text(f)
    codes = app.js("()=>{const P=window.__shotplans,sc=P.cur();return sc.shots.map(s=>P.shotCode(sc,s))}")
    assert len(codes) == shots and all('Shot ' + c in txt for c in codes)
    assert not app.errors
