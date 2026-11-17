"""Validación estática documental SOL. No inicia servicios ni escribe bases o archivos."""
import ast
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote

BASE=Path(__file__).resolve().parents[1]
REPO=BASE.parents[1]


def local_target(document,target):
    target=target.strip().strip('<>')
    if not target or target.startswith(('#','http:','https:','mailto:','data:','javascript:')):return None
    target=unquote(target.split('#',1)[0].split('?',1)[0])
    if not target:return None
    return (REPO/target.lstrip('/')) if target.startswith('/') else document.parent/target


class Resources(HTMLParser):
    def __init__(self):super().__init__();self.targets=[]
    def handle_starttag(self,tag,attrs):
        for name,value in attrs:
            if name in {'src','href'} and value:self.targets.append(value)


def validate():
    errors=[];counts=Counter()
    files=[p for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    markdown=[p for p in files if p.suffix=='.md']+[REPO/n for n in ['README.md','EMPEZAR_AQUI_SOL.md','README-INICIO.md'] if (REPO/n).exists()]
    for p in markdown:
        content=re.sub(r'^```.*?^```[^\n]*','',p.read_text(),flags=re.M|re.S)
        targets=re.findall(r'!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)',content)
        targets+=re.findall(r'^\s*\[[^\]]+\]:\s*(\S+)',content,flags=re.M)
        parser=Resources();parser.feed(content);targets+=parser.targets
        for target in targets:
            dest=local_target(p,target)
            if dest is not None:
                counts['markdown_links']+=1
                if not dest.exists():errors.append({'source':str(p.relative_to(REPO)),'target':target})
    for p in files:
        if p.suffix=='.xml':ET.parse(p);counts['xml']+=1
        if p.suffix=='.json':json.loads(p.read_text());counts['json']+=1
        if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p));counts['python_ast']+=1
        if p.suffix=='.html':
            parser=Resources();parser.feed(p.read_text());counts['html']+=1
            for target in parser.targets:
                dest=local_target(p,target)
                if dest is not None:
                    counts['html_resources']+=1
                    if not dest.exists():errors.append({'source':str(p.relative_to(REPO)),'target':target})
        if p.suffix=='.png':
            assert p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'),p
            counts['png']+=1
    inv=BASE/'06-historico/inventario-documental.json'
    if inv.exists():
        entries=json.loads(inv.read_text())['archivos'];counts['original_files']=len(entries)
        for record in entries:
            if record.get('publicacion')=='LOCAL_NO_VERSIONAR':
                counts['local_originals_optional']+=1
                continue
            dest=REPO/record['destino']
            if not dest.exists():errors.append({'source':'inventario','target':record['destino']})
            elif record['categoria'] in {'E','F'}:
                if hashlib.sha256(dest.read_bytes()).hexdigest()!=record['sha256']:
                    errors.append({'source':'hash original','target':record['destino']})
    evidence=json.loads((BASE/'04-pruebas/p20/evidencias.json').read_text())
    assert evidence['integration']['status']=='passed' and len(evidence['integration']['checks'])==150
    assert all(row['passed'] for row in evidence['integration']['checks'])
    assert len(evidence['integration']['fault_checks'])==2
    for key,n in [('SOL',219),('COREDB',57),('CAP',35),('CAP_SOL',4),('EVA_MySQL',65),('EVA_ack_unit',9),('EVA_ack_TCP',7)]:
        run=evidence['regressions'][key];assert run['exit']==0 and f'{n} passed' in run['summary'],key
    assert '114 passed' in evidence['regressions']['frontend']['summary']
    counts['recorded_p20_checks']=150
    return {'status':'passed' if not errors else 'failed','counts':dict(counts),'errors':errors}


if __name__=='__main__':
    result=validate();print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(result['status']!='passed')
