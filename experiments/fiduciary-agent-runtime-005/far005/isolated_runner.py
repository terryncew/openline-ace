from __future__ import annotations
import json, pathlib, sys, traceback

def semantic_transform(x):
    if isinstance(x,dict) and set(x)=={'value'}: return x['value']
    if isinstance(x,(int,float)): return x
    raise ValueError('bad transform shape')

def main():
    repo=pathlib.Path(sys.argv[1]); cases=json.loads(pathlib.Path(sys.argv[2]).read_text())
    sys.path.insert(0,str(repo/'src'))
    from core import codec
    from workers import parse as parse_mod
    from workers import transform as transform_mod
    import pipeline
    out=[]
    for c in cases:
        ok=False
        try:
            kind=c['kind']; value=c.get('value'); tag=c.get('tag','x')
            if kind=='codec_roundtrip':
                p={'value':value,'tag':tag}; ok=(codec.decode(codec.encode(p))==p)
            elif kind=='parse_value':
                p={'value':value,'tag':tag}; ok=(parse_mod.parse(codec.encode(p))==int(value))
            elif kind=='transform_semantic':
                ok=(semantic_transform(transform_mod.transform(value))==int(value)*2)
            elif kind=='pipeline_result':
                p={'value':value,'tag':tag}; ok=(pipeline.run(codec.encode(p))=={'result':int(value)*2})
            elif kind=='contract_transform_schema':
                x=transform_mod.transform(value); ok=(isinstance(x,dict) and set(x)=={'value'} and isinstance(x['value'],int))
            elif kind=='contract_parse_type':
                p={'value':value,'tag':tag}; ok=isinstance(parse_mod.parse(codec.encode(p)),int)
            elif kind=='contract_codec_object':
                p={'value':value,'tag':tag}; ok=isinstance(codec.decode(codec.encode(p)),dict)
            else: raise KeyError(kind)
        except Exception:
            ok=False
        out.append({'id':c['id'],'passed':bool(ok)})
    print(json.dumps(out,sort_keys=True))
if __name__=='__main__': main()
