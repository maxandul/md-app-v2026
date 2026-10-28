"""Recheck the six supplied E2 originals without copying them into the repo.

Usage: python scripts/validate_e2_samples.py --input-dir PATH [--output PATH]
Expected values were read from the rendered originals on 28 October 2026.
This is a parser/exception check, not HR approval or a Windows integration test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from webapp.services.word_pdf import inspect_word_pdf


def run(directory):
    expected=json.loads((Path(__file__).resolve().parents[1]/'tests'/'fixtures'/'e2_expected.json').read_text(encoding='utf-8'))
    results=[]
    for spec in expected['files']:
        path=directory/spec['filename'];errors=[]
        if not path.is_file():
            results.append({'filename':spec['filename'],'passed':False,'errors':['Original fehlt']});continue
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if sha!=spec['sha256']:
            results.append({'filename':spec['filename'],'passed':False,'errors':['Prüfsumme weicht vom geprüften Original ab']});continue
        parsed=inspect_word_pdf(path)
        for key,value in spec['expected_parser'].items():
            actual=parsed.get(key)
            if key in ('performance_goals','development_goals'):
                actual=[{k:v for k,v in goal.items() if k!='evidence'} for goal in actual]
            if actual!=value:errors.append({'field':key,'expected':value,'actual':actual})
        if parsed['validation']['eligible']:
            errors.append('Widersprüchliches Testformular oder Scan darf nicht automatisch übernommen werden')
        results.append({'filename':spec['filename'],'sha256':sha,'passed':not errors,'errors':errors,
                        'profile':parsed['validation']['profile'],'source_role':parsed['source_role'],
                        'automatic':parsed['validation']['eligible'],'review_reasons':parsed['validation']['reasons']})
    return {'checked_at':'2026-10-28','expected_values':'Aus den sichtbaren Originalen abgeleitet; keine zusätzliche fachliche Freigabe behauptet.',
            'passed':all(r['passed'] for r in results),'files':results}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=run(args.input_dir)
    encoded=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(encoded+'\n',encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'files':[{'filename':r['filename'],'passed':r['passed'],'errors':r['errors']} for r in result['files']]},ensure_ascii=False))
    raise SystemExit(0 if result['passed'] else 1)
