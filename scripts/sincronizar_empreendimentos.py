"""Sincroniza a lista de empreendimentos (const D do index.html) com o tabelao-online (Firestore).
Uso: python3 scripts/sincronizar_empreendimentos.py <export.json> [--init]
export.json = {"docs":[{id, nome, status, ...campos do Firestore}], "imgs":{id: dataURL jpeg}}  (ou só a lista de docs)
Só aplica os campos que MUDARAM no tabelao-online desde a última sincronização (base-firestore.json),
para não desfazer as correções de acentos/nomes feitas no Tabelão da equipe.
"""
import json, re, sys, os, base64
from datetime import datetime, timedelta, timezone
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TZ = timezone(timedelta(hours=-3)); agora = datetime.now(TZ)
ST = {'lançado': 'L', 'obras': 'O', 'entregue': 'E', 'lançamento': 'N', 'novidade': 'V', 'esgotado': 'X'}
def dt(t): return datetime.fromisoformat(t.replace('Z', '+00:00')).astimezone(TZ) if t else None
def ym(t): d = dt(t); return d.strftime('%Y-%m') if d else None
def drv(u):
    m = re.search(r'/folders/([\w-]+)', u or '') or re.search(r'[?&]id=([\w-]+)', u or ''); return m.group(1) if m else None
def row(e):
    g = e.get
    return [g('nome'), ST.get(g('status'), 'O'), g('regiao'), g('bairro'), g('endereco'), g('valorMinimo'), g('valorMaximo'),
            g('areaPrivativaMin'), g('areaPrivativaMax'), g('dormsMin'), g('dormsMax'), g('vagasMin'), g('vagasMax'), g('tipoVaranda'),
            ym(g('dataEntrega')), ym(g('lancamento')), g('unidadesTotais'), g('torres'), ' '.join(g('tiposRenda') or []), drv(g('linkDrive'))]
K = ["nome","st","reg","bairro","end","vMin","vMax","aMin","aMax","dMin","dMax","vgMin","vgMax","var","ent","lanc","un","torres","renda","drive"]
raw = json.load(open(sys.argv[1])); docs = raw['docs'] if isinstance(raw, dict) else raw; imgs = raw.get('imgs', {}) if isinstance(raw, dict) else {}
assert len(docs) >= 30, 'export pequeno demais: nao publicar'
byid = {d['id']: d for d in docs}
pi = os.path.join(R, 'index.html'); s = open(pi).read()
a = s.index('const D'); b = s.index('[', a); c = s.index('\n];', b) + 3
D = json.loads(s[b:c - 1])
pm, pb = os.path.join(R, 'mapa-firestore.json'), os.path.join(R, 'base-firestore.json')
M = {int(k): v for k, v in json.load(open(pm)).items()}
base = json.load(open(pb)) if os.path.exists(pb) else {}
log = []
def sameval(x, y): return x == y or (isinstance(x, (int, float)) and isinstance(y, (int, float)) and abs(x - y) < 0.005)
if '--init' not in sys.argv:
    for n, i in sorted(M.items()):
        r = D[n - 1]
        while len(r) < 21: r.append(None)
        x = r[20] or {}
        e = byid.get(i)
        if not e:
            if r[1] != 'X': r[1] = 'X'; x['esg'] = x.get('esg') or agora.strftime('%d/%m/%Y'); log.append(f'n{n} {r[0]}: saiu do tabelao-online -> esgotado')
            r[20] = x or None; continue
        new, old = row(e), base.get(i)
        if old is None: old = new
        for j in range(1, 20):
            if not sameval(new[j], old[j]) and not sameval(new[j], r[j]):
                log.append(f'n{n} {r[0]}: {K[j]} {r[j]!r} -> {new[j]!r}'); r[j] = new[j]
        if new[0] != old[0]: log.append(f'n{n} {r[0]}: nome no tabelao-online mudou para {new[0]!r} (mantido o nome atual)')
        if e.get('status') == 'esgotado':
            d = dt(e.get('esgotadoEm')); x['esg'] = d.strftime('%d/%m/%Y') if d else x.get('esg') or agora.strftime('%d/%m/%Y')
        elif 'esg' in x and r[1] != 'X': x.pop('esg')
        r[20] = x or None
    # novos empreendimentos
    for e in docs:
        if e['id'] in M.values(): continue
        if e.get('status') == 'esgotado': continue
        n = len(D) + 1; r = row(e); x = {'novo': agora.strftime('%d/%m/%Y')}
        if e['id'] in imgs:
            os.makedirs(os.path.join(R, 'fotos'), exist_ok=True)
            open(os.path.join(R, 'fotos', f'{n}.jpg'), 'wb').write(base64.b64decode(imgs[e['id']].split(',', 1)[1])); x['img'] = f'fotos/{n}.jpg'
        r.append(x); D.append(r); M[n] = e['id']; log.append(f'n{n} NOVO: {r[0]} ({e.get("status")}, {r[2]}, {r[3]})')
# tira null final das linhas sem extras
for r in D:
    while len(r) > 20 and r[-1] is None: r.pop()
body = '[\n' + ',\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in D) + '\n];'
s = s[:b] + body + s[c:]
s = re.sub(r'<div class="pub">[^<]*</div>', f'<div class="pub">Empreendimentos conferidos no Tabelão Online em {agora.strftime("%d/%m/%Y")}</div>', s, count=1)
open(pi, 'w').write(s)
json.dump({str(k): v for k, v in sorted(M.items())}, open(pm, 'w'), ensure_ascii=False, indent=0)
json.dump({d['id']: row(d) for d in docs}, open(pb, 'w'), ensure_ascii=False, separators=(',', ':'))
print('empreendimentos no site:', len(D)); print('\n'.join(log) if log else 'sem mudancas no tabelao-online')
