from __future__ import annotations
import ast, json, pathlib

def load_manifest(root:pathlib.Path): return json.loads((root/'SCOPE_MANIFEST.json').read_text())

def _normalized_nodes(source:str):
    tree=ast.parse(source); functions={}; module_nodes=[]
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            functions[node.name]=ast.dump(node,include_attributes=False)
        else:
            module_nodes.append(ast.dump(node,include_attributes=False))
    return functions, tuple(module_nodes)

def changed_symbols(before:str,candidate:str):
    try:
        bf,bm=_normalized_nodes(before); cf,cm=_normalized_nodes(candidate)
    except SyntaxError:
        return {'__SYNTAX_ERROR__'}
    changed={name for name in set(bf)|set(cf) if bf.get(name)!=cf.get(name)}
    if bm!=cm: changed.add('__MODULE__')
    return changed

def assess_scope(*,target:str,before:str,candidate:str,manifest:dict):
    changed=changed_symbols(before,candidate); allowed=set(manifest['target_closures'].get(target,[]))
    ok=bool(changed) and target in changed and changed.issubset(allowed)
    return {'target':target,'changed_symbols':sorted(changed),'allowed_symbols':sorted(allowed),'scope_ok':ok,'unknown_defaults_closed':True}
