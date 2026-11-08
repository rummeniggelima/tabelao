"""Atualiza unidades.json e promocoes.json a partir do arquivo baixado do portal.
Uso: python3 scripts/atualizar.py <arquivo-baixado.json>
O arquivo tem {"out": <unidades>, "st": {"empreendimento|bloco|unidade": status}} (nomes normalizados).
"""
import json, sys, unicodedata, re, os
from collections import Counter
from datetime import datetime, timezone, timedelta
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def norm(s):
    s = unicodedata.normalize('NFD', s); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s.lower()).strip()
raw = json.load(open(sys.argv[1]))
out, st = raw['out'], raw.get('st', {})
assert len(out['rows']) >= 3000 and len(out['consultados']) >= 40, 'carga pequena demais: nao publicar'
old = json.load(open(os.path.join(R, 'unidades.json')))
co, cn = Counter(r[0] for r in old['rows']), Counter(r[0] for r in out['rows'])
print('unidades:', len(old['rows']), '->', len(out['rows']), '| consultados:', len(out['consultados']))
for n in sorted(set(co) | set(cn)):
    a, b = co.get(n, 0), cn.get(n, 0)
    if (a and not b) or (b and not a) or (a > 20 and b < a / 2): print(f'  n{n}: {a} -> {b}')
json.dump(out, open(os.path.join(R, 'unidades.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
# Promoções: marca disp=1 (Disponível), 0 (outro status = vendida/reservada) ou None (não achou)
pp = os.path.join(R, 'promocoes.json')
if os.path.exists(pp) and st:
    P = json.load(open(pp)); C = P['campos']; iD = C.index('disp')
    agora = datetime.now(timezone(timedelta(hours=-3)))
    if agora.strftime('%Y-%m-%d') > P['validoAte']: P['ativo'] = False
    canon = lambda u: re.sub(r'[A-Za-z]+$', '', str(u).strip()).lstrip('0') or '0'
    alt = {}
    for k, v in st.items():
        e, b, u = k.split('|', 2); alt.setdefault(e + '|' + b + '|' + canon(u), v)
    sts = Counter(); fora = []
    for x in P['rows']:
        g = P['grupos'][x[0]]; s = None
        for nm in g['sf']:
            s = st.get(norm(nm) + '|' + norm(x[1]) + '|' + str(x[2]).strip())
            if s: break
        if s is None:
            for nm in g['sf']:
                s = alt.get(norm(nm) + '|' + norm(x[1]) + '|' + canon(x[2]))
                if s: break
        x[iD] = None if s is None else (1 if s == 'Disponível' else 0)
        sts[s] += 1
        if s is None: fora.append(g['nome'] + ' ' + x[1] + ' ' + x[2])
    # faixa: SÓ do que o encarte diz (coluna Renda): 3.200 = trava MCMV Faixa 1; 4.863 HIS1; 9.726 HIS2; 16.210 HMP; sem renda = R2V
    if 'faixa' not in C: C.append('faixa'); [x.append(None) for x in P['rows']]
    iF, iR = C.index('faixa'), C.index('renda')
    porRenda = {3200: 'Faixa 1', 4863: 'HIS1', 9726: 'HIS2', 16210: 'HMP', None: 'R2V'}
    for x in P['rows']: x[iF] = porRenda.get(x[iR])
    P['conferidoEm'] = out['geradoEm']
    json.dump(P, open(pp, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('promo:', dict(sts), '| ativas:', sum(1 for x in P['rows'] if x[iD] != 0), '| campanha ativa:', P.get('ativo', True))
    if fora: print('  nao achadas no Salesforce:', fora[:20])
