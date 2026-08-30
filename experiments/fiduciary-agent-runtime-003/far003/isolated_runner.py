from __future__ import annotations
import importlib.util, json, pathlib, sys, uuid

def load(repo):
    name='far003_isolated_'+uuid.uuid4().hex
    spec=importlib.util.spec_from_file_location(name,repo/'src/targetlib/core.py')
    mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod

def main():
    repo=pathlib.Path(sys.argv[1]); cases=json.loads(sys.stdin.read()); passed=[]
    for case in cases:
        try:
            mod=load(repo); got=None
            for call in case['sequence']:
                got=getattr(mod,call['fn'])(*call['args'])
            if got==case['expected']: passed.append(case['id'])
        except Exception: pass
    print(json.dumps({'passed':passed},sort_keys=True))
if __name__=='__main__': main()
