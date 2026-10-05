#!/usr/bin/env python3
"""Validate and merge approved BAYYIN source records from JSON/JSONL.

This script deliberately does not scrape religious websites. Provide an export
or API-derived file whose provenance you are allowed to store, then validate it
before merging into data/sources.json.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_HOSTS = {
    'quranpedia.net','www.quranpedia.net','api.quranpedia.net',
    'quranenc.com','www.quranenc.com',
    'dorar.net','www.dorar.net',
    'hadeethenc.com','www.hadeethenc.com',
    'shamela.ws','www.shamela.ws',
    'islamic-content.com','www.islamic-content.com',
    'terminologyenc.com','www.terminologyenc.com',
    'icadb.com','www.icadb.com',
}
REQUIRED={'id','source_type','reference','text_ar','source_url','provenance'}

def load(path: Path):
    if path.suffix.lower()=='.jsonl':
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    obj=json.loads(path.read_text(encoding='utf-8'))
    return obj if isinstance(obj,list) else obj.get('records',[])

def validate(row):
    errors=[]
    missing=REQUIRED-{k for k,v in row.items() if v not in ('',None,[])}
    if missing: errors.append('missing: '+', '.join(sorted(missing)))
    if row.get('source_type') not in {'quran','hadith','tafsir','terminology','islamic_content'}:
        errors.append('unsupported source_type')
    host=urlparse(str(row.get('source_url',''))).hostname or ''
    if host.lower() not in ALLOWED_HOSTS: errors.append(f'unapproved host: {host or "<none>"}')
    if row.get('source_type')=='hadith' and not (row.get('grading_ar') or row.get('grading_en') or row.get('hadith_grading_ar')):
        errors.append('hadith record lacks documented grading')
    if row.get('source_type')=='quran' and not row.get('reference'):
        errors.append('quran record lacks verse reference')
    return errors

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('input',type=Path)
    ap.add_argument('--target',type=Path,default=Path('data/sources.json'))
    ap.add_argument('--write',action='store_true',help='merge valid records; default is validation only')
    args=ap.parse_args()
    incoming=load(args.input)
    bad=[]
    for i,row in enumerate(incoming):
        e=validate(row)
        if e: bad.append((i,row.get('id'),e))
    if bad:
        for item in bad: print('ERROR',item)
        raise SystemExit(2)
    print(f'Validated {len(incoming)} approved-domain records.')
    if not args.write: return
    current=json.loads(args.target.read_text(encoding='utf-8')) if args.target.exists() else []
    by_id={r['id']:r for r in current}
    collisions=[r['id'] for r in incoming if r['id'] in by_id]
    if collisions:
        raise SystemExit('Refusing to overwrite existing ids: '+', '.join(collisions[:10]))
    current.extend(incoming)
    args.target.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Wrote {len(current)} total records to {args.target}')

if __name__=='__main__': main()
