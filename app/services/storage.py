from pathlib import Path
ROOT=Path("/data/private-media")
def safe_path(key:str):
    p=(ROOT/key).resolve()
    if ROOT.resolve() not in p.parents: raise ValueError("invalid media key")
    return p
def verification_public_url(key:str): return None
