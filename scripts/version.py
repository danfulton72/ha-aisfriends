#!/usr/bin/env python3
"""Semantic version helpers for CI/release automation."""
from __future__ import annotations
import argparse,json,re,subprocess
from pathlib import Path
TAG_RE=re.compile(r"^v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
MANIFEST=Path("custom_components/aisfriends/manifest.json")
def semantic_tags():
    parsed=[]
    for tag in subprocess.check_output(["git","tag","--list"],text=True).splitlines():
        m=TAG_RE.fullmatch(tag.strip())
        if m: parsed.append((tuple(int(m.group(p)) for p in ("major","minor","patch")),tag))
    return parsed
def highest():
    tags=semantic_tags(); return max(tags,key=lambda i:i[0]) if tags else ((0,0,0),"v0.0.0")
def version_text(v): return ".".join(map(str,v))
def next_patch():
    v,_=highest(); return (v[0],v[1],v[2]+1)
def read_manifest(): return json.loads(MANIFEST.read_text())
def sync_manifest(v):
    data=read_manifest(); expected=version_text(v)
    if data.get("version")==expected: return False
    data["version"]=expected; MANIFEST.write_text(json.dumps(data,indent=2)+"\n"); return True
def main():
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command",required=True)
    for c in ("highest","next","check-manifest-current","sync-manifest-current","sync-manifest-next"): sub.add_parser(c)
    a=parser.parse_args(); current,current_tag=highest(); current_text=version_text(current); upcoming=next_patch(); upcoming_text=version_text(upcoming)
    if a.command=="highest": print(current_text); return
    if a.command=="next": print(upcoming_text); return
    if a.command=="check-manifest-current":
        mv=str(read_manifest().get("version",""))
        if mv!=current_text: raise SystemExit(f"manifest.json version {mv!r} is out of sync: highest semantic Git tag is {current_tag} ({current_text})")
        print(f"Version sync OK: {current_tag}; manifest={mv}"); return
    if a.command=="sync-manifest-current": sync_manifest(current); print(current_text); return
    if a.command=="sync-manifest-next": sync_manifest(upcoming); print(upcoming_text); return
if __name__=="__main__": main()
