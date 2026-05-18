from __future__ import annotations
import argparse, copy, json, os, platform, re, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path
APP_NAME='codex-redteam-optin-mode'; APP_VERSION='0.4.0'
AGENTS_BLOCK_START='<!-- codex-redteam-optin-mode:start -->'; AGENTS_BLOCK_END='<!-- codex-redteam-optin-mode:end -->'
SESSION_STATUS='Loading session mode context'; PROMPT_STATUS='Checking mode-gated offensive routing'
def color(text:str,code:str)->str: return text if os.environ.get('NO_COLOR') else f'\033[{code}m{text}\033[0m'
def info(msg:str)->None: print(color(f'[INFO] {msg}','36'))
def good(msg:str)->None: print(color(f'[OK] {msg}','32'))
def manifest_path(codex_home:Path)->Path: return codex_home/'redteam-install-manifest.json'
def detect_codex_home(explicit:str|None)->Path: return Path(explicit).expanduser() if explicit else Path(os.environ.get('CODEX_HOME') or (Path.home()/'.codex'))
def detect_agents_home(explicit:str|None)->Path: return Path(explicit).expanduser() if explicit else Path.home()/'.agents'
def remove_path(path:Path,dry_run:bool)->None:
    info(f'remove {path}')
    if dry_run or not path.exists(): return
    shutil.rmtree(path) if path.is_dir() else path.unlink()
def copy_file(src:Path,dst:Path,dry_run:bool)->None:
    info(f'copy {src} -> {dst}')
    if dry_run: return
    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src,dst)
def copy_tree(src:Path,dst:Path,dry_run:bool)->None:
    info(f'copy {src} -> {dst}')
    if dry_run: return
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src,dst)
def seed_prompt_files(repo_root:Path,codex_home:Path,dry_run:bool)->None:
    src_dir=repo_root/'codex'/'prompts'; dst_dir=codex_home/'prompts'
    if not src_dir.exists(): return
    for src in src_dir.glob('*.md'):
        dst=dst_dir/src.name
        if dst.exists(): info(f'keep existing prompt {dst}'); continue
        info(f'seed prompt {src} -> {dst}')
        if dry_run: continue
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src,dst)
def build_hooks_payload(repo_root:Path,codex_home:Path)->dict:
    src=repo_root/'templates'/'hooks.json.template'; python_cmd='python' if os.name=='nt' else 'python3'; script_dir=str(codex_home/'hooks')
    if os.name=='nt': script_dir=script_dir.replace('\\','\\\\')
    return json.loads(src.read_text(encoding='utf-8').replace('{{PYTHON_CMD}}', python_cmd).replace('{{CODEX_HOOKS_DIR}}', script_dir))
def managed_agents_block(repo_root:Path)->str:
    body=(repo_root/'codex'/'AGENTS.md').read_text(encoding='utf-8').strip()
    return f'{AGENTS_BLOCK_START}\n{body}\n{AGENTS_BLOCK_END}\n'
def upsert_agents_file(repo_root:Path,codex_home:Path,dry_run:bool)->None:
    dst=codex_home/'AGENTS.md'; block=managed_agents_block(repo_root); info(f"merge {repo_root/'codex'/'AGENTS.md'} -> {dst}")
    if dry_run: return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        current=dst.read_text(encoding='utf-8'); pattern=re.compile(rf'{re.escape(AGENTS_BLOCK_START)}.*?{re.escape(AGENTS_BLOCK_END)}\n?', re.S)
        merged=pattern.sub(lambda _: block, current) if pattern.search(current) else f"{current}{'' if current.endswith(chr(10)) or current=='' else chr(10)}\n{block}"
    else: merged=block
    dst.write_text(merged, encoding='utf-8')
def remove_agents_block(codex_home:Path,dry_run:bool)->None:
    dst=codex_home/'AGENTS.md'
    if not dst.exists(): return
    info(f'remove managed block from {dst}')
    if dry_run: return
    current=dst.read_text(encoding='utf-8'); pattern=re.compile(rf'\n?{re.escape(AGENTS_BLOCK_START)}.*?{re.escape(AGENTS_BLOCK_END)}\n?', re.S); updated=pattern.sub('\n', current).strip()
    dst.write_text(updated+'\n', encoding='utf-8') if updated else dst.unlink()
def is_managed_hook(hook:dict)->bool:
    command=str(hook.get('command','')); status=str(hook.get('statusMessage',''))
    return 'session-start-context.py' in command or 'hook-security-context-hook.py' in command or status in {SESSION_STATUS, PROMPT_STATUS}
def scrub_managed_hooks(payload:dict)->dict:
    hooks_root=payload.get('hooks',{}); cleaned={}
    for event, entries in hooks_root.items():
        new_entries=[]
        for entry in entries:
            hooks=[hook for hook in entry.get('hooks',[]) if not is_managed_hook(hook)]
            if hooks:
                cloned=copy.deepcopy(entry); cloned['hooks']=hooks; new_entries.append(cloned)
        if new_entries: cleaned[event]=new_entries
    payload['hooks']=cleaned; return payload
def merge_hooks_json(repo_root:Path,codex_home:Path,dry_run:bool)->None:
    dst=codex_home/'hooks.json'; rendered=build_hooks_payload(repo_root,codex_home); info(f"merge {repo_root/'templates'/'hooks.json.template'} -> {dst}")
    if dry_run: return
    dst.parent.mkdir(parents=True, exist_ok=True)
    existing=json.loads(dst.read_text(encoding='utf-8')) if dst.exists() else {'hooks':{}}
    existing=scrub_managed_hooks(existing); hooks_root=existing.setdefault('hooks',{})
    for event, entries in rendered.get('hooks',{}).items(): hooks_root.setdefault(event,[]).extend(copy.deepcopy(entries))
    dst.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
def remove_managed_hooks(codex_home:Path,dry_run:bool)->None:
    dst=codex_home/'hooks.json'
    if not dst.exists(): return
    info(f'remove managed hooks from {dst}')
    if not dry_run:
        payload=scrub_managed_hooks(json.loads(dst.read_text(encoding='utf-8'))); hooks_root=payload.get('hooks',{})
        dst.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8') if hooks_root else dst.unlink()
def run_validate(repo_root:Path,codex_home:Path,dry_run:bool)->None:
    if dry_run: return
    subprocess.run([sys.executable, str(repo_root/'scripts'/'validate.py'), '--codex-home', str(codex_home)], check=True)
def repo_skill_dirs(repo_root:Path)->list[Path]:
    skills_root=repo_root/'agents'/'skills'; return sorted(path for path in skills_root.iterdir() if path.is_dir()) if skills_root.exists() else []
def managed_targets(repo_root:Path,codex_home:Path,agents_home:Path)->list[Path]:
    targets=[codex_home/'instruction.ctf.md',codex_home/'hooks'/'session-start-context.py',codex_home/'hooks'/'hook-security-context-hook.py',codex_home/'hooks'/'redteam_state.py',codex_home/'hooks'/'core',codex_home/'router',codex_home/'orchestrator']
    targets.extend(agents_home/'skills'/skill_dir.name for skill_dir in repo_skill_dirs(repo_root)); return targets
def legacy_cleanup_targets(codex_home:Path,agents_home:Path)->list[Path]:
    return [codex_home/'hooks'/'legacy-redteam-hook.py', agents_home/'skills'/'red-team-command-doctrine-old']
def load_manifest_targets(codex_home:Path)->list[Path]:
    manifest=manifest_path(codex_home)
    if not manifest.exists(): return []
    try: data=json.loads(manifest.read_text(encoding='utf-8'))
    except (json.JSONDecodeError,OSError): return []
    targets=[]; 
    for raw in data.get('managed_paths',[]):
        try: targets.append(Path(raw))
        except TypeError: pass
    return targets
def write_manifest(codex_home:Path,targets:list[Path],dry_run:bool)->None:
    manifest=manifest_path(codex_home); payload={'name':APP_NAME,'version':APP_VERSION,'installed_at':datetime.now().isoformat(timespec='seconds'),'managed_paths':[str(path) for path in targets],'merged_files':[str(codex_home/'AGENTS.md'),str(codex_home/'hooks.json')]}
    info(f'write manifest {manifest}')
    if dry_run: return
    manifest.parent.mkdir(parents=True, exist_ok=True); manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
def upgrade_cleanup(codex_home:Path,agents_home:Path,default_targets:list[Path],dry_run:bool)->None:
    manifest=manifest_path(codex_home); previous_targets=load_manifest_targets(codex_home); cleanup_targets=previous_targets or default_targets; protected={str(codex_home/'AGENTS.md'), str(codex_home/'hooks.json')}
    remove_path(manifest,dry_run); seen=set()
    for target in cleanup_targets + legacy_cleanup_targets(codex_home,agents_home):
        key=str(target)
        if key in seen or key in protected: continue
        seen.add(key); remove_path(target,dry_run)
def uninstall(repo_root:Path,codex_home:Path,agents_home:Path,dry_run:bool)->None:
    targets=load_manifest_targets(codex_home) or managed_targets(repo_root,codex_home,agents_home)
    for target in targets: remove_path(target,dry_run)
    for target in legacy_cleanup_targets(codex_home,agents_home): remove_path(target,dry_run)
    remove_agents_block(codex_home,dry_run); remove_managed_hooks(codex_home,dry_run); remove_path(manifest_path(codex_home),dry_run)
def main()->None:
    parser=argparse.ArgumentParser(); parser.add_argument('--codex-home'); parser.add_argument('--agents-home'); parser.add_argument('--dry-run', action='store_true'); parser.add_argument('--uninstall', action='store_true'); args=parser.parse_args()
    repo_root=Path(__file__).resolve().parents[1]; codex_home=detect_codex_home(args.codex_home); agents_home=detect_agents_home(args.agents_home)
    info(f'platform: {platform.system()}'); info(f'codex home: {codex_home}'); info(f'agents home: {agents_home}')
    current_targets=managed_targets(repo_root,codex_home,agents_home)
    if args.uninstall: uninstall(repo_root,codex_home,agents_home,args.dry_run); good('uninstall complete'); return
    upgrade_cleanup(codex_home,agents_home,current_targets,args.dry_run)
    copy_file(repo_root/'instruction.ctf.md', codex_home/'instruction.ctf.md', args.dry_run); seed_prompt_files(repo_root,codex_home,args.dry_run); upsert_agents_file(repo_root,codex_home,args.dry_run)
    copy_file(repo_root/'codex'/'hooks'/'session-start-context.py', codex_home/'hooks'/'session-start-context.py', args.dry_run)
    copy_file(repo_root/'codex'/'hooks'/'hook-security-context-hook.py', codex_home/'hooks'/'hook-security-context-hook.py', args.dry_run)
    copy_file(repo_root/'codex'/'hooks'/'redteam_state.py', codex_home/'hooks'/'redteam_state.py', args.dry_run)
    copy_tree(repo_root/'codex'/'hooks'/'core', codex_home/'hooks'/'core', args.dry_run)
    copy_tree(repo_root/'codex'/'router', codex_home/'router', args.dry_run)
    copy_tree(repo_root/'codex'/'orchestrator', codex_home/'orchestrator', args.dry_run)
    for skill_dir in repo_skill_dirs(repo_root): copy_tree(skill_dir, agents_home/'skills'/skill_dir.name, args.dry_run)
    merge_hooks_json(repo_root,codex_home,args.dry_run); write_manifest(codex_home,current_targets,args.dry_run); run_validate(repo_root,codex_home,args.dry_run); good('install complete')
if __name__=='__main__': main()
