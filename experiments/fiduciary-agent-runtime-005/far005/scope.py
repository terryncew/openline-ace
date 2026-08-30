from __future__ import annotations
import ast, json, pathlib
from .substrate import NODE_PATHS, top_level_shape

def load_manifest(root:pathlib.Path): return json.loads((root/'DEPENDENCY_MANIFEST.json').read_text())
def path_to_node(manifest): return {v['path']:k for k,v in manifest['nodes'].items()}
def affected_consumers(manifest,node): return list(manifest['transitive_consumers'][node])

def imports(source:str):
    tree=ast.parse(source); out=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Import): out.extend(a.name for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module: out.append(n.module)
    return sorted(set(out))

def assess_patch(*,manifest:dict,node:str,path:str,before:str,candidate:str,extra_paths=()):
    reasons=[]; expected=manifest['nodes'][node]['path']
    if path!=expected: reasons.append('TARGET_PATH_MISMATCH')
    if tuple(extra_paths): reasons.append('UNREGISTERED_ADDITIONAL_PATH')
    try:
        bshape,bimports=top_level_shape(before); cshape,cimports=top_level_shape(candidate)
    except Exception:
        return {'scope_ok':False,'reasons':['SYNTAX_OR_AST_FAILURE'],'affected_consumers':affected_consumers(manifest,node),'new_imports':[]}
    # Function/import topology is frozen. Bodies may change; top-level names/import statements may not.
    if [x for x in bshape if x[0] != 'function'] != [x for x in cshape if x[0] != 'function']:
        reasons.append('MODULE_LEVEL_STRUCTURE_CHANGED')
    if [x[1] for x in bshape if x[0]=='function'] != [x[1] for x in cshape if x[0]=='function']:
        reasons.append('TOP_LEVEL_FUNCTION_SET_CHANGED')
    allowed=set(manifest['nodes'][node]['allowed_imports']); cand=set(cimports); new=sorted(cand-set(bimports))
    if not cand.issubset(allowed): reasons.append('IMPORT_OUTSIDE_FROZEN_MANIFEST')
    if new: reasons.append('NEW_DEPENDENCY_EDGE_NOT_PREREGISTERED')
    return {'scope_ok':not reasons,'reasons':sorted(set(reasons)),'affected_consumers':affected_consumers(manifest,node),'new_imports':new,'changed_path':path}

def assess_paths_only(manifest:dict,paths:list[str]):
    registered=set(path_to_node(manifest)); bad=[p for p in paths if p not in registered]
    return {'scope_ok':not bad,'unregistered_paths':sorted(bad)}
