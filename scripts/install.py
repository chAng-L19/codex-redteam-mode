from __future__ import annotations
import argparse, base64, copy, hashlib, json, os, platform, re, shlex, shutil, subprocess, sys
from datetime import datetime
from fnmatch import fnmatchcase
from pathlib import Path
try:
    import tomlkit
    from tomlkit.exceptions import ParseError as TomlParseError
except ModuleNotFoundError as exc:
    print(
        "ERROR: missing dependency 'tomlkit'. Install dependencies with: "
        "python -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc
APP_NAME='codex-redteam-optin-mode'; APP_VERSION='1.3.0'
AGENTS_BLOCK_START='<!-- codex-redteam-optin-mode:start -->'; AGENTS_BLOCK_END='<!-- codex-redteam-optin-mode:end -->'
SESSION_STATUS='Loading session mode context'; PROMPT_STATUS='Checking mode-gated offensive routing'
SYSTEM_INSTRUCTIONS_CONFIG_VALUE='./redteam-mode/system-instructions.md'
SYSTEM_PROFILE_START='<!-- codex-redteam-system-profile:start -->'; SYSTEM_PROFILE_END='<!-- codex-redteam-system-profile:end -->'
MODEL_CATALOG_START='<!-- codex-redteam-model-profiles:start -->'; MODEL_CATALOG_END='<!-- codex-redteam-model-profiles:end -->'
DEFAULT_MODEL_PROFILE_FILES={'gpt-5.6*':'Jailbreak.gpt-5.6.md','gpt-5.5*':'Jailbreak.gpt-5.5.md','gpt-5.4*':'Jailbreak.gpt-5.4.md','default':'Jailbreak.default.md'}
_MISSING=object()
class ManifestValidationError(ValueError): pass
class InstallPreflightError(RuntimeError): pass
def configure_stdio()->None:
    for stream in (sys.stdout,sys.stderr):
        reconfigure=getattr(stream,'reconfigure',None)
        if reconfigure: reconfigure(encoding='utf-8',errors='backslashreplace')
def color(text:str,code:str)->str: return text if os.environ.get('NO_COLOR') else f'\033[{code}m{text}\033[0m'
def info(msg:str)->None: print(color(f'[INFO] {msg}','36'))
def warn(msg:str)->None: print(color(f'[WARN] {msg}','33'))
def good(msg:str)->None: print(color(f'[OK] {msg}','32'))
def manifest_path(codex_home:Path)->Path: return codex_home/'redteam-install-manifest.json'
def transaction_path(codex_home:Path)->Path: return codex_home/'redteam-install-transaction.json'
def normalize_path(value:str|Path)->Path: return Path(value).expanduser().resolve(strict=False)
def detect_codex_home(explicit:str|None)->Path: return normalize_path(explicit or os.environ.get('CODEX_HOME') or (Path.home()/'.codex'))
def detect_agents_home(explicit:str|None)->Path: return normalize_path(explicit or (Path.home()/'.agents'))
def resolve_install_paths(project_home:str|None,codex_home:str|None,agents_home:str|None)->tuple[Path,Path,Path]:
    if project_home:
        project_root=normalize_path(project_home)
        return project_root/'.codex', (normalize_path(agents_home) if agents_home else project_root/'.agents'), project_root/'AGENTS.md'
    resolved_codex=detect_codex_home(codex_home)
    return resolved_codex, detect_agents_home(agents_home), resolved_codex/'AGENTS.md'
def resolve_install_homes(project_home:str|None,codex_home:str|None,agents_home:str|None)->tuple[Path,Path]:
    codex_home,agents_home,_=resolve_install_paths(project_home,codex_home,agents_home)
    return codex_home,agents_home
def resolve_log_root(codex_home:Path,explicit:str|None)->Path:
    return normalize_path(explicit) if explicit else normalize_path(codex_home/'logs'/'codex-redteam')
def runtime_state_locations()->list[Path]:
    locations=[]; configured=os.environ.get('CODEX_HOME','').strip()
    if configured: locations.append(normalize_path(configured)/'redteam-mode'/'state')
    default=normalize_path(Path.home()/'.codex'/'redteam-mode'/'state')
    if default not in locations: locations.append(default)
    return locations
def _is_within(path:Path,*roots:Path)->bool:
    resolved=path.resolve()
    return any(resolved == root.resolve() or str(resolved).startswith(str(root.resolve())+os.sep) for root in roots if root)

_SAFE_ROOTS:list[Path]=[]

def remove_path(path:Path,dry_run:bool)->None:
    info(f'remove {path}')
    if dry_run or not path.exists(): return
    if _SAFE_ROOTS and not _is_within(path, *_SAFE_ROOTS):
        info(f'SKIP remove {path} — outside safe boundaries ({[str(r) for r in _SAFE_ROOTS]})')
        return
    shutil.rmtree(path) if path.is_dir() else path.unlink()
def copy_file(src:Path,dst:Path,dry_run:bool)->None:
    info(f'copy {src} -> {dst}')
    if dry_run: return
    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src,dst)
def _toml_container(value:object)->bool:
    return hasattr(value,'items')
def _toml_plain(value:object)->object:
    return value.unwrap() if hasattr(value,'unwrap') else value
def _read_toml_document(path:Path)->object:
    if not path.is_file(): return tomlkit.document()
    return tomlkit.parse(path.read_text(encoding='utf-8-sig'))
def _config_string(path:Path,key:str)->str:
    try: value=_read_toml_document(path).get(key)
    except (OSError,TomlParseError): return ''
    plain=_toml_plain(value)
    return plain.strip() if isinstance(plain,str) else ''
def _configured_profile_mapping(path:Path)->dict[str,str]:
    try: document=_read_toml_document(path)
    except (OSError,TomlParseError): return {}
    redteam=document.get('redteam'); configured=redteam.get('model_prompt_profiles') if hasattr(redteam,'get') else None
    if not hasattr(configured,'items'): return {}
    return {str(pattern).strip():str(_toml_plain(filename)).strip() for pattern,filename in configured.items() if str(pattern).strip() and isinstance(_toml_plain(filename),str) and str(_toml_plain(filename)).strip()}
def resolve_install_model(repo_root:Path,codex_home:Path,explicit:str|None,previous_system_prompt:dict|None=None)->tuple[str,str]:
    previous_model=previous_system_prompt.get('model','').strip() if isinstance(previous_system_prompt,dict) and isinstance(previous_system_prompt.get('model'),str) else ''
    candidates=[('argument',(explicit or '').strip()),('environment',os.environ.get('CODEX_MODEL','').strip()),('target-config',_config_string(codex_home/'config.toml','model')),('manifest',previous_model),('source-config',_config_string(repo_root/'config.toml','model'))]
    for source,value in candidates:
        if value: return value,source
    return 'unknown','default'
def model_profile_mapping(repo_root:Path,codex_home:Path)->dict[str,str]:
    mapping=dict(DEFAULT_MODEL_PROFILE_FILES); configured=_configured_profile_mapping(codex_home/'config.toml')
    if not configured: configured=_configured_profile_mapping(repo_root/'config.toml')
    mapping.update(configured); return mapping
def _owned_target_keys(targets:list[Path])->set[str]:
    return {str(path.resolve(strict=False)).casefold() for path in targets}
def resolve_profile_path(repo_root:Path,codex_home:Path,filename:str,owned_targets:list[Path])->tuple[str,Path]:
    safe_filename=Path(filename).name; installed=codex_home/'prompts'/safe_filename; bundled=repo_root/'codex'/'prompts'/safe_filename; owned=_owned_target_keys(owned_targets)
    if installed.is_file() and str(installed.resolve(strict=False)).casefold() not in owned: return safe_filename,installed
    if bundled.is_file(): return safe_filename,bundled
    if installed.is_file(): return safe_filename,installed
    return safe_filename,bundled
def select_model_profile(repo_root:Path,codex_home:Path,model:str,owned_targets:list[Path])->tuple[str,str,Path]:
    mapping=model_profile_mapping(repo_root,codex_home); normalized=model.casefold(); profile='default'; filename=mapping.get('default',DEFAULT_MODEL_PROFILE_FILES['default'])
    patterns=sorted((key for key in mapping if key.casefold()!='default'),key=len,reverse=True)
    for pattern in patterns:
        lowered=pattern.casefold()
        if fnmatchcase(normalized,lowered) or (not any(char in lowered for char in '*?[') and normalized.startswith(lowered)):
            profile=pattern; filename=mapping[pattern]; break
    safe_filename,prompt_path=resolve_profile_path(repo_root,codex_home,filename,owned_targets)
    if not prompt_path.is_file(): profile='default'; safe_filename,prompt_path=resolve_profile_path(repo_root,codex_home,mapping.get('default',DEFAULT_MODEL_PROFILE_FILES['default']),owned_targets)
    if not prompt_path.is_file(): safe_filename,prompt_path=resolve_profile_path(repo_root,codex_home,DEFAULT_MODEL_PROFILE_FILES['default'],owned_targets)
    if not prompt_path.is_file(): raise FileNotFoundError(f'model prompt profile not found: {prompt_path}')
    return profile,safe_filename,prompt_path
def _managed_config_value(metadata:dict,path:list[str])->object:
    config_merge=metadata.get('config_merge') if isinstance(metadata,dict) else None
    if not isinstance(config_merge,dict): return _MISSING
    for entry in config_merge.get('added_values',[]):
        if isinstance(entry,dict) and entry.get('path')==path: return entry.get('value')
    return _MISSING
def original_model_instructions_reference(codex_home:Path,ownership_data:dict)->str|None:
    config_path=codex_home/'config.toml'; current=_config_string(config_path,'model_instructions_file')
    previous_system=ownership_data.get('system_prompt') if isinstance(ownership_data,dict) else None
    previous_reference=previous_system.get('user_model_instructions_file') if isinstance(previous_system,dict) else None
    if current:
        managed=_managed_config_value(ownership_data,['model_instructions_file'])
        if current==SYSTEM_INSTRUCTIONS_CONFIG_VALUE: return previous_reference if isinstance(previous_reference,str) and previous_reference.strip() else None
        if managed is not _MISSING and current==managed: return None
        return current
    return previous_reference if isinstance(previous_reference,str) and previous_reference.strip() else None
def resolve_instruction_reference(config_path:Path,reference:str|None)->Path|None:
    if not reference: return None
    candidate=Path(reference).expanduser()
    if not candidate.is_absolute(): candidate=config_path.parent/candidate
    return candidate.resolve(strict=False)
def _sha256_text(value:str)->str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest() if value else ''
def build_model_profile_catalog(repo_root:Path,codex_home:Path,owned_targets:list[Path])->tuple[str,list[dict]]:
    entries=[]; sections=[]
    for pattern,configured_filename in model_profile_mapping(repo_root,codex_home).items():
        filename,prompt_path=resolve_profile_path(repo_root,codex_home,configured_filename,owned_targets)
        if not prompt_path.is_file(): continue
        profile_content=prompt_path.read_text(encoding='utf-8-sig').strip(); entries.append({'profile':pattern,'profile_file':filename,'profile_sha256':_sha256_text(profile_content)})
        sections.append(f'## Model system profile: {pattern}\n\nProfile file: `{filename}`\n\n{profile_content}')
    if not sections: raise FileNotFoundError('no model prompt profiles available for system catalog')
    routes='\n'.join(f'- `{entry["profile"]}` -> `{entry["profile_file"]}`' for entry in entries)
    router=(
        '# Automatic model system profile router\n\n'
        'At every new conversation, read the `[model-prompt-profile]` metadata emitted by SessionStart. '
        'Activate exactly the one model profile section whose pattern/file matches that metadata. '
        'Treat every non-matching model profile section as inert reference data and do not follow it. '
        'If metadata is absent, match the runtime model identifier against the patterns below; use `default` only when no specialized pattern matches.\n\n'
        f'{routes}\n\n{MODEL_CATALOG_START}\n'+'\n\n'.join(sections)+f'\n{MODEL_CATALOG_END}'
    )
    return router,entries
def build_system_instructions(repo_root:Path,codex_home:Path,model:str,model_source:str,user_reference:str|None,owned_targets:list[Path])->tuple[str,dict]:
    profile,filename,profile_path=select_model_profile(repo_root,codex_home,model,owned_targets)
    base_path=repo_root/'instruction.ctf.md'; generated_path=codex_home/'redteam-mode'/'system-instructions.md'; user_path=resolve_instruction_reference(codex_home/'config.toml',user_reference)
    user_content=''
    if user_path is not None and user_path not in {base_path.resolve(strict=False),generated_path.resolve(strict=False)}:
        try: user_content=user_path.read_text(encoding='utf-8-sig').strip()
        except OSError as exc: warn(f'user model instructions not loaded from {user_path}: {exc}')
    base_content=base_path.read_text(encoding='utf-8-sig').strip(); profile_content=profile_path.read_text(encoding='utf-8-sig').strip(); profile_catalog,catalog_entries=build_model_profile_catalog(repo_root,codex_home,owned_targets)
    metadata={'model':model,'model_source':model_source,'profile':profile,'profile_file':filename,'layer':'system','delivery':'model_instructions_file:app-dispatcher','generated_path':str(generated_path.resolve(strict=False)),'user_model_instructions_file':user_reference,'user_instructions_path':str(user_path) if user_path is not None else None,'user_instructions_sha256':_sha256_text(user_content),'base_instructions_sha256':_sha256_text(base_content),'profile_sha256':_sha256_text(profile_content),'profile_catalog':catalog_entries}
    sections=[]
    if user_content: sections.append(f'# Preserved user system instructions\n\n{user_content}')
    sections.extend((f'# Codex red-team base instructions\n\n{base_content}',profile_catalog))
    marker=json.dumps(metadata,ensure_ascii=False,separators=(',',':')); content=f'{SYSTEM_PROFILE_START}\n{marker}\n{SYSTEM_PROFILE_END}\n\n'+'\n\n'.join(sections)+'\n'
    metadata['combined_sha256']=_sha256_text(content)
    return content,metadata
def write_system_instructions(destination:Path,content:str,dry_run:bool)->None:
    info(f'write combined system instructions -> {destination}')
    if dry_run: return
    destination.parent.mkdir(parents=True,exist_ok=True); temporary=destination.with_name(f'{destination.name}.tmp'); temporary.write_text(content,encoding='utf-8'); os.replace(temporary,destination)
def write_launcher_scripts(codex_home:Path,dry_run:bool)->None:
    launcher_dir=codex_home/'redteam-mode'; windows_path=launcher_dir/'codex-redteam.cmd'; posix_path=launcher_dir/'codex-redteam'
    info(f'write model-aware launchers -> {windows_path}, {posix_path}')
    if dry_run: return
    launcher_dir.mkdir(parents=True,exist_ok=True); python_cmd=str(Path(sys.executable).resolve(strict=False))
    windows_path.write_text(f'@echo off\r\n"{python_cmd}" -B "%~dp0launcher.py" %*\r\n',encoding='utf-8')
    posix_path.write_text(f'#!/bin/sh\nexec {shlex.quote(python_cmd)} -B "$(dirname "$0")/launcher.py" "$@"\n',encoding='utf-8')
    posix_path.chmod(posix_path.stat().st_mode|0o111)
def _collect_toml_ownership(value:object,path:tuple[str,...],added_values:list[dict],added_tables:list[list[str]])->None:
    if _toml_container(value):
        added_tables.append(list(path))
        for key,nested in value.items(): _collect_toml_ownership(nested,path+(str(key),),added_values,added_tables)
        return
    added_values.append({'path':list(path),'value':_toml_plain(value)})
def _merge_toml_missing(template:object,existing:object,path:tuple[str,...]=(),added_values:list[dict]|None=None,added_tables:list[list[str]]|None=None)->bool:
    added_values=added_values if added_values is not None else []
    added_tables=added_tables if added_tables is not None else []
    changed=False
    for key,value in template.items():
        if key not in existing:
            existing[key]=copy.deepcopy(value); _collect_toml_ownership(value,path+(str(key),),added_values,added_tables); changed=True; continue
        current=existing[key]
        if _toml_container(value):
            if not _toml_container(current):
                full_key='.'.join(path+(str(key),))
                raise ValueError(f'config key {full_key!r} already exists and is not a table')
            changed=_merge_toml_missing(value,current,path+(str(key),),added_values,added_tables) or changed
    return changed
def merge_config_text(template_text:str,existing_text:str)->str:
    template=tomlkit.parse(template_text)
    existing=tomlkit.parse(existing_text) if existing_text.strip() else tomlkit.document()
    if not _merge_toml_missing(template,existing): return existing_text
    return tomlkit.dumps(existing)
def _toml_value_at(container:object,path:list[str])->object:
    current=container
    for key in path:
        if not _toml_container(current) or key not in current: return _MISSING
        current=current[key]
    return current
def _valid_config_merge(metadata:object,dst:Path)->dict:
    if not isinstance(metadata,dict) or not isinstance(metadata.get('path'),str): return {}
    try:
        if normalize_path(metadata['path']) != dst.resolve(strict=False): return {}
    except (OSError,ValueError): return {}
    return metadata
def _dedupe_owned_values(entries:list[dict])->list[dict]:
    deduped={}
    for entry in entries:
        path=entry.get('path') if isinstance(entry,dict) else None
        if isinstance(path,list) and path and all(isinstance(key,str) for key in path): deduped[tuple(path)]={'path':path,'value':entry.get('value')}
    return list(deduped.values())
def _dedupe_owned_tables(entries:list[list[str]])->list[list[str]]:
    deduped=[]; seen=set()
    for path in entries:
        if not isinstance(path,list) or not path or not all(isinstance(key,str) for key in path): continue
        key=tuple(path)
        if key not in seen: seen.add(key); deduped.append(path)
    return deduped
def _dedupe_replaced_values(entries:list[dict])->list[dict]:
    deduped={}
    for entry in entries:
        path=entry.get('path') if isinstance(entry,dict) else None
        if isinstance(path,list) and path and all(isinstance(key,str) for key in path): deduped[tuple(path)]={'path':path,'value':entry.get('value'),'previous_value':entry.get('previous_value')}
    return list(deduped.values())
def _set_toml_value(container:object,path:list[str],value:object)->None:
    parent=container
    for key in path[:-1]: parent=parent[key]
    parent[path[-1]]=value
def prepare_config_merge(src:Path,dst:Path,previous_config_merge:object=None,forced_values:dict[tuple[str,...],object]|None=None)->tuple[Path,str,str,dict]:
    template_text=src.read_text(encoding='utf-8-sig')
    existing_text=dst.read_text(encoding='utf-8-sig') if dst.exists() else ''
    template=tomlkit.parse(template_text); existing=tomlkit.parse(existing_text) if existing_text.strip() else tomlkit.document()
    previous=_valid_config_merge(previous_config_merge,dst); retained_values=[]; retained_tables=[]; previous_replaced={}
    for entry in previous.get('added_values',[]):
        path=entry.get('path') if isinstance(entry,dict) else None
        current=_toml_value_at(existing,path) if isinstance(path,list) and path and all(isinstance(key,str) for key in path) else _MISSING
        if current is not _MISSING and _toml_plain(current)==entry.get('value'): retained_values.append(entry)
    for path in previous.get('added_tables',[]):
        current=_toml_value_at(existing,path) if isinstance(path,list) and path and all(isinstance(key,str) for key in path) else _MISSING
        if current is not _MISSING and _toml_container(current): retained_tables.append(path)
    for entry in previous.get('replaced_values',[]):
        path=entry.get('path') if isinstance(entry,dict) else None
        if isinstance(path,list) and path and all(isinstance(key,str) for key in path): previous_replaced[tuple(path)]=entry
    added_values=[]; added_tables=[]; changed=_merge_toml_missing(template,existing,(),added_values,added_tables)
    replaced_values=[]
    for path_tuple,managed_value in (forced_values or {}).items():
        path=list(path_tuple); current=_toml_value_at(existing,path); previous_entry=previous_replaced.get(path_tuple)
        if current is _MISSING:
            _set_toml_value(existing,path,managed_value); added_values.append({'path':path,'value':managed_value}); changed=True; continue
        current_plain=_toml_plain(current)
        if current_plain!=managed_value:
            previous_value=previous_entry.get('previous_value') if isinstance(previous_entry,dict) and current_plain==previous_entry.get('value') else current_plain
            _set_toml_value(existing,path,managed_value); replaced_values.append({'path':path,'value':managed_value,'previous_value':previous_value}); changed=True
        elif isinstance(previous_entry,dict): replaced_values.append(previous_entry)
    merged=tomlkit.dumps(existing) if changed else existing_text
    existed_before=previous.get('existed_before') if isinstance(previous.get('existed_before'),bool) else dst.exists()
    metadata={'path':str(dst.resolve(strict=False)),'existed_before':existed_before,'added_values':_dedupe_owned_values(retained_values+added_values),'added_tables':_dedupe_owned_tables(retained_tables+added_tables),'replaced_values':_dedupe_replaced_values(replaced_values)}
    return dst,existing_text,merged,metadata
def backup_config_file(dst:Path,dry_run:bool)->Path:
    backup=dst.with_name(f'{dst.name}.{datetime.now().strftime("%Y%m%d%H%M%S")}.bak')
    info(f'backup {dst} -> {backup}')
    if not dry_run: shutil.copy2(dst,backup)
    return backup
def apply_config_merge(plan:tuple[Path,str,str,dict],dry_run:bool)->None:
    dst,existing_text,merged,_=plan
    if merged==existing_text: return
    if dst.exists(): backup_config_file(dst,dry_run)
    if dry_run: return
    dst.parent.mkdir(parents=True, exist_ok=True); dst.write_text(merged,encoding='utf-8')
def merge_config_file(src:Path,dst:Path,dry_run:bool)->None:
    info(f'merge {src} -> {dst}')
    apply_config_merge(prepare_config_merge(src,dst),dry_run)
def _remove_toml_path(container:object,path:list[str])->bool:
    parent=container
    for key in path[:-1]:
        if not _toml_container(parent) or key not in parent: return False
        parent=parent[key]
    if not _toml_container(parent) or path[-1] not in parent: return False
    del parent[path[-1]]; return True
def _configured_instruction_path(document:object,config_path:Path)->Path|None:
    value=_toml_value_at(document,['model_instructions_file'])
    if value is _MISSING or not isinstance(_toml_plain(value),str): return None
    candidate=Path(_toml_plain(value)).expanduser()
    if not candidate.is_absolute(): candidate=config_path.parent/candidate
    try: return candidate.resolve(strict=False)
    except OSError: return None
def _config_references_instruction(document:object,config_path:Path,instruction_paths:list[Path])->bool:
    candidate=_configured_instruction_path(document,config_path)
    return candidate is not None and candidate in {path.resolve(strict=False) for path in instruction_paths}
def prepare_config_removal(codex_home:Path,manifest_data:dict)->tuple[Path,str,str|None,bool]:
    dst=codex_home/'config.toml'; instructions=[codex_home/'redteam-mode'/'system-instructions.md',codex_home/'instruction.ctf.md']
    if not dst.exists(): return dst,'',None,False
    existing_text=dst.read_text(encoding='utf-8-sig'); document=tomlkit.parse(existing_text) if existing_text.strip() else tomlkit.document()
    metadata=_valid_config_merge(manifest_data.get('config_merge'),dst); changed=False
    for entry in metadata.get('replaced_values',[]):
        path=entry.get('path') if isinstance(entry,dict) else None
        current=_toml_value_at(document,path) if isinstance(path,list) and path and all(isinstance(key,str) for key in path) else _MISSING
        if current is _MISSING: continue
        if _toml_plain(current)!=entry.get('value'):
            warn(f"preserve user-modified config key {'.'.join(path)}")
            continue
        _set_toml_value(document,path,entry.get('previous_value')); changed=True
    for entry in metadata.get('added_values',[]):
        path=entry.get('path') if isinstance(entry,dict) else None
        current=_toml_value_at(document,path) if isinstance(path,list) and path and all(isinstance(key,str) for key in path) else _MISSING
        if current is _MISSING: continue
        if _toml_plain(current)!=entry.get('value'):
            warn(f"preserve user-modified config key {'.'.join(path)}")
            continue
        changed=_remove_toml_path(document,path) or changed
    owned_tables=[path for path in metadata.get('added_tables',[]) if isinstance(path,list) and path and all(isinstance(key,str) for key in path)]
    for path in sorted(owned_tables,key=len,reverse=True):
        current=_toml_value_at(document,path)
        if current is not _MISSING and _toml_container(current) and not list(current.items()): changed=_remove_toml_path(document,path) or changed
    rendered=tomlkit.dumps(document) if changed else existing_text
    if changed and not metadata.get('existed_before',True) and not list(document.items()) and not rendered.strip(): rendered=None
    return dst,existing_text,rendered,_config_references_instruction(document,dst,instructions)
def apply_config_removal(plan:tuple[Path,str,str|None,bool],dry_run:bool)->None:
    dst,existing_text,rendered,_=plan
    if rendered==existing_text: return
    if dst.exists(): backup_config_file(dst,dry_run)
    if dry_run: return
    if rendered is None:
        if dst.exists(): dst.unlink()
        return
    dst.write_text(rendered,encoding='utf-8')
def copy_tree(src:Path,dst:Path,dry_run:bool)->None:
    info(f'copy {src} -> {dst}')
    if dry_run: return
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo'))

def copy_skill_md(src_dir:Path,dst_dir:Path,dry_run:bool)->None:
    """Copy only SKILL.md from a skill directory (Loop Runtime format)."""
    src_file=src_dir/'SKILL.md'
    if not src_file.exists(): return
    info(f'copy skill {src_dir.name}/SKILL.md -> {dst_dir}')
    if dry_run: return
    dst_dir.mkdir(parents=True, exist_ok=True)
    import shutil; shutil.copy2(src_file, dst_dir/'SKILL.md')
def managed_prompt_targets(repo_root:Path,codex_home:Path,owned_targets:list[Path])->list[Path]:
    src_dir=repo_root/'codex'/'prompts'; dst_dir=codex_home/'prompts'
    if not src_dir.exists(): return []
    owned={str(path.resolve(strict=False)) for path in owned_targets}
    return [dst_dir/src.name for src in src_dir.glob('*.md') if not (dst_dir/src.name).exists() or str((dst_dir/src.name).resolve(strict=False)) in owned]
def seed_prompt_files(repo_root:Path,codex_home:Path,dry_run:bool)->None:
    src_dir=repo_root/'codex'/'prompts'; dst_dir=codex_home/'prompts'
    if not src_dir.exists(): return
    for src in src_dir.glob('*.md'):
        dst=dst_dir/src.name
        if dst.exists(): info(f'keep existing prompt {dst}'); continue
        info(f'seed prompt {src} -> {dst}')
        if dry_run: continue
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src,dst)
def _powershell_literal(value:str)->str: return "'" + value.replace("'","''") + "'"
def resolve_powershell_command()->str:
    for name in ('powershell.exe','pwsh.exe','pwsh','powershell'):
        resolved=shutil.which(name)
        if resolved: return resolved
    system_root=os.environ.get('SystemRoot','').strip()
    if system_root:
        legacy=Path(system_root)/'System32'/'WindowsPowerShell'/'v1.0'/'powershell.exe'
        if legacy.is_file(): return str(legacy)
    return 'powershell.exe'
def build_windows_hook_command(python_cmd:str,script_path:Path,powershell_cmd:str|None=None)->str:
    script=(
        "$ErrorActionPreference='Stop';"
        f"& {_powershell_literal(python_cmd)} '-B' {_powershell_literal(str(script_path))};"
        "exit $LASTEXITCODE"
    )
    encoded=base64.b64encode(script.encode('utf-16le')).decode('ascii')
    return subprocess.list2cmdline([powershell_cmd or resolve_powershell_command(),'-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',encoded])
def build_hooks_payload(repo_root:Path,codex_home:Path)->dict:
    src=repo_root/'templates'/'hooks.json.template'; python_cmd=str(Path(sys.executable).resolve(strict=False)); hooks_dir=codex_home/'hooks'
    commands={
        '{{SESSION_COMMAND}}':shlex.join([python_cmd,'-B',str(hooks_dir/'session-start-context.py')]),
        '{{SESSION_COMMAND_WINDOWS}}':build_windows_hook_command(python_cmd,hooks_dir/'session-start-context.py'),
        '{{PROMPT_COMMAND}}':shlex.join([python_cmd,'-B',str(hooks_dir/'hook-security-context-hook.py')]),
        '{{PROMPT_COMMAND_WINDOWS}}':build_windows_hook_command(python_cmd,hooks_dir/'hook-security-context-hook.py'),
    }
    rendered=src.read_text(encoding='utf-8-sig')
    for placeholder,command in commands.items(): rendered=rendered.replace(placeholder,json.dumps(command)[1:-1])
    payload=json.loads(rendered)
    return validate_hooks_payload(payload,src)
def managed_agents_block(repo_root:Path)->str:
    body=(repo_root/'codex'/'AGENTS.md').read_text(encoding='utf-8').strip()
    return f'{AGENTS_BLOCK_START}\n{body}\n{AGENTS_BLOCK_END}\n'
def upsert_agents_file(repo_root:Path,agents_file:Path,dry_run:bool)->None:
    dst=agents_file; block=managed_agents_block(repo_root); info(f"merge {repo_root/'codex'/'AGENTS.md'} -> {dst}")
    if dry_run: return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        current=dst.read_text(encoding='utf-8'); pattern=re.compile(rf'{re.escape(AGENTS_BLOCK_START)}.*?{re.escape(AGENTS_BLOCK_END)}\n?', re.S)
        merged=pattern.sub(lambda _: block, current) if pattern.search(current) else f"{current}{'' if current.endswith(chr(10)) or current=='' else chr(10)}\n{block}"
    else: merged=block
    dst.write_text(merged, encoding='utf-8')
def remove_agents_block(agents_file:Path,dry_run:bool)->None:
    dst=agents_file
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
def validate_hooks_payload(payload:object,source:Path)->dict:
    if not isinstance(payload,dict): raise ValueError(f'{source} must contain a JSON object')
    hooks_root=payload.get('hooks',{})
    if not isinstance(hooks_root,dict): raise ValueError(f'{source} key "hooks" must contain a JSON object')
    for event,entries in hooks_root.items():
        if not isinstance(entries,list): raise ValueError(f'{source} hook event {event!r} must contain a JSON array')
        for entry_index,entry in enumerate(entries):
            if not isinstance(entry,dict): raise ValueError(f'{source} hook event {event!r} entry {entry_index} must be a JSON object')
            hooks=entry.get('hooks')
            if not isinstance(hooks,list): raise ValueError(f'{source} hook event {event!r} entry {entry_index} key "hooks" must contain a JSON array')
            if not all(isinstance(hook,dict) for hook in hooks): raise ValueError(f'{source} hook event {event!r} entry {entry_index} contains a non-object hook')
    return payload
def load_hooks_payload(dst:Path)->dict:
    if not dst.exists(): return {'hooks':{}}
    try: payload=json.loads(dst.read_text(encoding='utf-8-sig'))
    except json.JSONDecodeError as exc: raise ValueError(f'invalid hooks JSON at {dst}: {exc}') from exc
    return validate_hooks_payload(payload,dst)
def prepare_hooks_merge(repo_root:Path,codex_home:Path)->tuple[Path,str]:
    dst=codex_home/'hooks.json'; rendered=build_hooks_payload(repo_root,codex_home); info(f"preflight hooks merge {repo_root/'templates'/'hooks.json.template'} -> {dst}")
    existing=scrub_managed_hooks(load_hooks_payload(dst)); hooks_root=existing.setdefault('hooks',{})
    for event,entries in rendered.get('hooks',{}).items(): hooks_root.setdefault(event,[]).extend(copy.deepcopy(entries))
    validate_hooks_payload(existing,dst)
    return dst,json.dumps(existing,ensure_ascii=False,indent=2)
def prepare_hooks_removal(codex_home:Path)->tuple[Path,str|None]:
    dst=codex_home/'hooks.json'; info(f'preflight managed hook removal from {dst}')
    if not dst.exists(): return dst,None
    payload=scrub_managed_hooks(load_hooks_payload(dst)); hooks_root=payload.get('hooks',{})
    return dst,(json.dumps(payload,ensure_ascii=False,indent=2) if hooks_root else None)
def apply_hooks_plan(plan:tuple[Path,str|None],dry_run:bool)->None:
    dst,rendered=plan
    if dry_run: return
    if rendered is None:
        if dst.exists(): dst.unlink()
        return
    dst.parent.mkdir(parents=True,exist_ok=True); dst.write_text(rendered,encoding='utf-8')
def merge_hooks_json(repo_root:Path,codex_home:Path,dry_run:bool)->None:
    plan=prepare_hooks_merge(repo_root,codex_home); info(f'apply hooks merge -> {plan[0]}'); apply_hooks_plan(plan,dry_run)
def remove_managed_hooks(codex_home:Path,dry_run:bool)->None:
    plan=prepare_hooks_removal(codex_home); info(f'apply managed hook removal -> {plan[0]}'); apply_hooks_plan(plan,dry_run)
def run_validate(repo_root:Path,codex_home:Path,dry_run:bool,manifest_candidate:Path|None=None)->None:
    if dry_run: return
    command=[sys.executable,str(repo_root/'scripts'/'validate.py'),'--codex-home',str(codex_home)]
    if manifest_candidate is not None: command.extend(['--manifest',str(manifest_candidate)])
    subprocess.run(command,check=True)
def repo_skill_dirs(repo_root:Path)->list[Path]:
    skills_root=repo_root/'agents'/'skills'; return sorted(path for path in skills_root.iterdir() if path.is_dir()) if skills_root.is_dir() else []
def deployment_source_requirements(repo_root:Path)->tuple[list[Path],list[Path]]:
    prompts_dir=repo_root/'codex'/'prompts'
    files=[
        repo_root/'config.toml',
        repo_root/'instruction.ctf.md',
        repo_root/'scripts'/'validate.py',
        repo_root/'templates'/'hooks.json.template',
        repo_root/'codex'/'launcher.py',
        repo_root/'codex'/'AGENTS.md',
        repo_root/'codex'/'hooks'/'session-start-context.py',
        repo_root/'codex'/'hooks'/'hook-security-context-hook.py',
        repo_root/'codex'/'hooks'/'redteam_state.py',
    ]
    files.extend(prompts_dir/filename for filename in sorted(set(DEFAULT_MODEL_PROFILE_FILES.values())))
    files.extend(skill_dir/'SKILL.md' for skill_dir in repo_skill_dirs(repo_root))
    directories=[
        repo_root/'agents'/'skills',
        repo_root/'codex'/'hooks'/'core',
        repo_root/'codex'/'router',
        repo_root/'codex'/'orchestrator',
        repo_root/'codex'/'automation',
        repo_root/'codex'/'session_patcher',
        prompts_dir,
    ]
    return files,directories
def preflight_deployment_sources(repo_root:Path)->None:
    files,directories=deployment_source_requirements(repo_root)
    invalid=[path for path in files if not path.is_file()]
    invalid.extend(path for path in directories if not path.is_dir())
    if not invalid: return
    details='\n'.join(f'  - {path}' for path in invalid)
    raise InstallPreflightError(f'install source preflight failed:\n{details}')
def managed_targets(repo_root:Path,codex_home:Path,agents_home:Path)->list[Path]:
    targets=[codex_home/'redteam-mode'/'system-instructions.md',codex_home/'redteam-mode'/'launcher.py',codex_home/'redteam-mode'/'codex-redteam.cmd',codex_home/'redteam-mode'/'codex-redteam',codex_home/'hooks'/'session-start-context.py',codex_home/'hooks'/'hook-security-context-hook.py',codex_home/'hooks'/'redteam_state.py',codex_home/'hooks'/'core',codex_home/'router',codex_home/'orchestrator',codex_home/'automation',codex_home/'session_patcher']
    targets.extend(agents_home/'skills'/skill_dir.name for skill_dir in repo_skill_dirs(repo_root)); return targets
def legacy_cleanup_targets(codex_home:Path,agents_home:Path)->list[Path]:
    return [codex_home/'hooks'/'legacy-redteam-hook.py', agents_home/'skills'/'red-team-command-doctrine-old']
def _unique_cleanup_targets(targets:list[Path],protected:set[str]|None=None)->list[Path]:
    protected=protected or set(); unique=[]; seen=set()
    for target in targets:
        key=str(target)
        if key in seen or key in protected: continue
        seen.add(key); unique.append(target)
    return unique
def preflight_cleanup_targets(targets:list[Path],operation:str)->None:
    if not _SAFE_ROOTS: return
    outside=[target for target in targets if target.exists() and not _is_within(target,*_SAFE_ROOTS)]
    if not outside: return
    print(f'ERROR: {operation} blocked because managed paths exist outside the current cleanup scope:',file=sys.stderr)
    for target in outside: print(f'  {target}',file=sys.stderr)
    print('Re-run with the original --agents-home value. No files were changed.',file=sys.stderr)
    raise SystemExit(2)
def _validated_absolute_paths(raw_paths:object,source:Path,label:str,field:str='managed_paths')->list[Path]:
    if not isinstance(raw_paths,list): raise ManifestValidationError(f'invalid {label} at {source}: {field} must be a JSON array')
    targets=[]
    for raw in raw_paths:
        if not isinstance(raw,str) or not raw.strip(): raise ManifestValidationError(f'invalid {label} at {source}: {field} entries must be non-empty strings')
        try: target=Path(raw).expanduser()
        except (TypeError,ValueError,OSError) as exc: raise ManifestValidationError(f'invalid {label} at {source}: invalid managed path {raw!r}') from exc
        if not target.is_absolute(): raise ManifestValidationError(f'invalid {label} at {source}: managed path must be absolute: {raw!r}')
        targets.append(target.resolve(strict=False))
    return targets
def validate_manifest_payload(data:object,source:Path)->dict:
    if not isinstance(data,dict): raise ManifestValidationError(f'invalid install manifest at {source}: expected a JSON object')
    raw_targets=data.get('managed_paths')
    _validated_absolute_paths(raw_targets,source,'install manifest')
    return data
def load_manifest_data(codex_home:Path)->dict:
    manifest=manifest_path(codex_home)
    if not manifest.exists(): return {}
    try: data=json.loads(manifest.read_text(encoding='utf-8'))
    except (json.JSONDecodeError,OSError) as exc: raise ManifestValidationError(f'invalid install manifest at {manifest}: {exc}') from exc
    return validate_manifest_payload(data,manifest)
def load_manifest_targets(codex_home:Path)->list[Path]:
    manifest=manifest_path(codex_home); data=load_manifest_data(codex_home)
    if not data: return []
    return _validated_absolute_paths(data['managed_paths'],manifest,'install manifest')
def build_manifest_payload(codex_home:Path,agents_file:Path,agents_home:Path,targets:list[Path],log_root:Path,custom_skill_dirs_enabled:bool,config_merge:dict|None=None,system_prompt:dict|None=None)->dict:
    skills_root=agents_home/'skills'
    skill_dirs=[str(skills_root/path.name) for path in repo_skill_dirs(Path(__file__).resolve().parents[1])]
    payload={'name':APP_NAME,'version':APP_VERSION,'manifest_schema_version':2,'installed_at':datetime.now().isoformat(timespec='seconds'),'managed_paths':[str(path) for path in targets],'merged_files':[str(agents_file),str(codex_home/'hooks.json'),str(codex_home/'config.toml')],'skills_paths':{'skills_root':str(skills_root),'skill_dirs':skill_dirs},'custom_skill_dirs_enabled':bool(custom_skill_dirs_enabled),'log_root':str(log_root),'config_merge':config_merge or {'path':str((codex_home/'config.toml').resolve(strict=False)),'existed_before':True,'added_values':[],'added_tables':[]}}
    if system_prompt: payload['system_prompt']=dict(system_prompt)
    return payload
def atomic_write_json(path:Path,payload:dict)->None:
    temporary=path.with_name(f'{path.name}.tmp')
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(temporary,path)
def validate_transaction_payload(data:object,source:Path)->dict:
    if not isinstance(data,dict): raise ManifestValidationError(f'invalid install transaction at {source}: expected a JSON object')
    if data.get('transaction_schema_version')!=1: raise ManifestValidationError(f'invalid install transaction at {source}: unsupported transaction_schema_version')
    if data.get('state') not in {'prepared','deployed','validation_failed','deployment_failed'}: raise ManifestValidationError(f'invalid install transaction at {source}: invalid state')
    previous=data.get('previous_manifest')
    if previous is not None: validate_manifest_payload(previous,source)
    validate_manifest_payload(data.get('candidate_manifest'),source)
    _validated_absolute_paths(data.get('previous_targets'),source,'install transaction','previous_targets')
    _validated_absolute_paths(data.get('candidate_targets'),source,'install transaction','candidate_targets')
    return data
def load_transaction_data(codex_home:Path)->dict:
    transaction=transaction_path(codex_home)
    if not transaction.exists(): return {}
    try: data=json.loads(transaction.read_text(encoding='utf-8'))
    except (json.JSONDecodeError,OSError) as exc: raise ManifestValidationError(f'invalid install transaction at {transaction}: {exc}') from exc
    return validate_transaction_payload(data,transaction)
def transaction_targets(codex_home:Path)->list[Path]:
    transaction=transaction_path(codex_home); data=load_transaction_data(codex_home)
    if not data: return []
    targets=[]
    targets.extend(_validated_absolute_paths(data['previous_targets'],transaction,'install transaction','previous_targets'))
    targets.extend(_validated_absolute_paths(data['candidate_targets'],transaction,'install transaction','candidate_targets'))
    return _unique_cleanup_targets(targets)
def begin_transaction(codex_home:Path,agents_home:Path,previous_manifest:dict,candidate_manifest:dict,previous_targets:list[Path],candidate_targets:list[Path],dry_run:bool)->None:
    if dry_run: return
    now=datetime.now().isoformat(timespec='seconds')
    payload={
        'name':APP_NAME,
        'transaction_schema_version':1,
        'state':'prepared',
        'started_at':now,
        'updated_at':now,
        'codex_home':str(codex_home),
        'agents_home':str(agents_home),
        'previous_manifest':previous_manifest or None,
        'candidate_manifest':candidate_manifest,
        'previous_targets':[str(path) for path in previous_targets],
        'candidate_targets':[str(path) for path in candidate_targets],
    }
    info(f'write pending install transaction {transaction_path(codex_home)}'); atomic_write_json(transaction_path(codex_home),payload)
def update_transaction(codex_home:Path,state:str,error:BaseException|None=None,dry_run:bool=False)->None:
    if dry_run: return
    transaction=transaction_path(codex_home); data=load_transaction_data(codex_home)
    if not data: return
    data['state']=state; data['updated_at']=datetime.now().isoformat(timespec='seconds')
    if error is not None: data['error']=f'{error.__class__.__name__}: {error}'
    elif 'error' in data: del data['error']
    atomic_write_json(transaction,data)
def remove_transaction(codex_home:Path,dry_run:bool)->None: remove_path(transaction_path(codex_home),dry_run)
def prepare_manifest_payload(codex_home:Path,payload:dict,dry_run:bool)->tuple[Path,Path]|None:
    manifest=manifest_path(codex_home); candidate=manifest.with_name(f'{manifest.name}.tmp'); info(f'prepare manifest {candidate}')
    if dry_run: return None
    manifest.parent.mkdir(parents=True,exist_ok=True); candidate.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest,candidate
def prepare_manifest(codex_home:Path,agents_file:Path,agents_home:Path,targets:list[Path],log_root:Path,custom_skill_dirs_enabled:bool,dry_run:bool,config_merge:dict|None=None,system_prompt:dict|None=None)->tuple[Path,Path]|None:
    payload=build_manifest_payload(codex_home,agents_file,agents_home,targets,log_root,custom_skill_dirs_enabled,config_merge,system_prompt)
    return prepare_manifest_payload(codex_home,payload,dry_run)
def commit_manifest(plan:tuple[Path,Path]|None,dry_run:bool)->None:
    if dry_run or plan is None: return
    manifest,candidate=plan; info(f'commit manifest {manifest}'); os.replace(candidate,manifest)
def discard_manifest(plan:tuple[Path,Path]|None)->None:
    if plan is None: return
    candidate=plan[1]
    if candidate.exists(): candidate.unlink()
def write_manifest(codex_home:Path,agents_file:Path,agents_home:Path,targets:list[Path],log_root:Path,custom_skill_dirs_enabled:bool,dry_run:bool,config_merge:dict|None=None,system_prompt:dict|None=None)->None:
    plan=prepare_manifest(codex_home,agents_file,agents_home,targets,log_root,custom_skill_dirs_enabled,dry_run,config_merge,system_prompt); commit_manifest(plan,dry_run)
def prepare_upgrade_cleanup(codex_home:Path,agents_home:Path,agents_file:Path,default_targets:list[Path],pending_targets:list[Path]|None=None)->list[Path]:
    previous_targets=load_manifest_targets(codex_home); recorded_targets=_unique_cleanup_targets(previous_targets + list(pending_targets or [])); cleanup_targets=recorded_targets or default_targets; protected={str(agents_file), str(codex_home/'AGENTS.md'), str(codex_home/'hooks.json'), str(codex_home/'config.toml')}
    cleanup_targets=_unique_cleanup_targets(cleanup_targets + legacy_cleanup_targets(codex_home,agents_home),protected)
    preflight_cleanup_targets(cleanup_targets,'upgrade cleanup')
    return cleanup_targets
def apply_upgrade_cleanup(cleanup_targets:list[Path],dry_run:bool)->None:
    for target in cleanup_targets: remove_path(target,dry_run)
def upgrade_cleanup(codex_home:Path,agents_home:Path,agents_file:Path,default_targets:list[Path],dry_run:bool)->None:
    apply_upgrade_cleanup(prepare_upgrade_cleanup(codex_home,agents_home,agents_file,default_targets,transaction_targets(codex_home)),dry_run)
def uninstall(repo_root:Path,codex_home:Path,agents_home:Path,agents_file:Path,dry_run:bool)->None:
    manifest_data=load_manifest_data(codex_home); pending_data=load_transaction_data(codex_home); ownership_data=pending_data.get('candidate_manifest') if pending_data else manifest_data
    config_plan=prepare_config_removal(codex_home,ownership_data or manifest_data)
    hooks_plan=prepare_hooks_removal(codex_home)
    recorded_targets=_unique_cleanup_targets(load_manifest_targets(codex_home) + transaction_targets(codex_home)); targets=_unique_cleanup_targets((recorded_targets or managed_targets(repo_root,codex_home,agents_home)) + legacy_cleanup_targets(codex_home,agents_home))
    if config_plan[3]:
        rendered=config_plan[2] or ''
        referenced=_configured_instruction_path(tomlkit.parse(rendered) if rendered.strip() else tomlkit.document(),config_plan[0])
        if referenced is not None:
            targets=[target for target in targets if target.resolve(strict=False)!=referenced]
            warn(f'preserve managed instruction file because config.toml still references it: {referenced}')
    preflight_cleanup_targets(targets,'uninstall')
    info(f'apply managed config removal -> {config_plan[0]}'); apply_config_removal(config_plan,dry_run)
    for target in targets: remove_path(target,dry_run)
    remove_agents_block(agents_file,dry_run)
    if agents_file != codex_home/'AGENTS.md': remove_agents_block(codex_home/'AGENTS.md',dry_run)
    info(f'apply managed hook removal -> {hooks_plan[0]}'); apply_hooks_plan(hooks_plan,dry_run); remove_path(manifest_path(codex_home),dry_run); remove_transaction(codex_home,dry_run)
def main()->None:
    parser=argparse.ArgumentParser(description='Install codex-redteam-optin-mode into a Codex Home or project.'); parser.add_argument('--codex-home', help='Codex Home/profile directory. AGENTS.md here is global guidance; use --project-home for project AGENTS.md.'); parser.add_argument('--agents-home', help='Skill installation destination. For a custom runtime directory, also use --enable-custom-skill-dirs.'); parser.add_argument('--project-home', help='Project root. Installs Codex files under PATH/.codex, skills under PATH/.agents by default, and AGENTS.md at PATH/AGENTS.md.'); parser.add_argument('--log-root', help='Automation log root recorded in the install manifest.'); parser.add_argument('--model', help='Active model used to select the system-layer Jailbreak profile. Falls back to CODEX_MODEL, target config, previous manifest, then source config.'); parser.add_argument('--enable-custom-skill-dirs', action='store_true', help='Prioritize the manifest-recorded custom skill directory at runtime.'); parser.add_argument('--dry-run', action='store_true', help='Preview operations without writing files.'); parser.add_argument('--uninstall', action='store_true', help='Remove managed files, hooks, and AGENTS.md blocks.'); args=parser.parse_args()
    if args.project_home and args.codex_home: parser.error('--project-home cannot be combined with --codex-home')
    repo_root=Path(__file__).resolve().parents[1]; codex_home,agents_home,agents_file=resolve_install_paths(args.project_home,args.codex_home,args.agents_home)
    log_root=resolve_log_root(codex_home,args.log_root)
    _SAFE_ROOTS.extend([codex_home, agents_home, repo_root])
    if args.project_home: _SAFE_ROOTS.append(agents_file.parent)
    info(f'platform: {platform.system()}'); info(f'codex home: {codex_home}'); info(f'agents home: {agents_home}')
    info(f'AGENTS.md: {agents_file}')
    info(f'log root: {log_root}')
    if args.agents_home and not args.enable_custom_skill_dirs and not args.uninstall:
        warn('custom --agents-home installs skill cards there, but runtime may prefer project or user defaults; use --enable-custom-skill-dirs to prioritize it')
    if args.uninstall:
        uninstall(repo_root,codex_home,agents_home,agents_file,args.dry_run)
        info('runtime session state and memory are preserved after uninstall; possible locations:')
        for location in runtime_state_locations(): info(f'  {location}')
        good('uninstall complete'); return
    preflight_deployment_sources(repo_root)
    current_targets=managed_targets(repo_root,codex_home,agents_home)
    info(f"preflight config merge {repo_root/'config.toml'} -> {codex_home/'config.toml'}")
    previous_manifest=load_manifest_data(codex_home); pending_data=load_transaction_data(codex_home); ownership_data=pending_data.get('candidate_manifest') if pending_data else previous_manifest
    user_reference=original_model_instructions_reference(codex_home,ownership_data or {}); system_model,system_model_source=resolve_install_model(repo_root,codex_home,args.model,ownership_data.get('system_prompt') if ownership_data else None)
    config_plan=prepare_config_merge(repo_root/'config.toml', codex_home/'config.toml',ownership_data.get('config_merge') if ownership_data else None,{('model_instructions_file',):SYSTEM_INSTRUCTIONS_CONFIG_VALUE})
    hooks_plan=prepare_hooks_merge(repo_root,codex_home)
    pending_targets=transaction_targets(codex_home); previous_targets=_unique_cleanup_targets(load_manifest_targets(codex_home)+pending_targets)
    system_instructions,system_prompt=build_system_instructions(repo_root,codex_home,system_model,system_model_source,user_reference,previous_targets); info(f"system prompt: model={system_model}; profile={system_prompt['profile']}; file={system_prompt['profile_file']}; user_base={user_reference or 'none'}")
    current_targets.extend(managed_prompt_targets(repo_root,codex_home,previous_targets))
    cleanup_targets=prepare_upgrade_cleanup(codex_home,agents_home,agents_file,current_targets,pending_targets)
    candidate_manifest=build_manifest_payload(codex_home,agents_file,agents_home,current_targets,log_root,args.enable_custom_skill_dirs,config_plan[3],system_prompt)
    begin_transaction(codex_home,agents_home,previous_manifest,candidate_manifest,previous_targets,current_targets,args.dry_run)
    manifest_plan=None; deployed=False
    try:
        apply_upgrade_cleanup(cleanup_targets,args.dry_run)
        if agents_file != codex_home/'AGENTS.md': remove_agents_block(codex_home/'AGENTS.md',args.dry_run)
        write_system_instructions(codex_home/'redteam-mode'/'system-instructions.md',system_instructions,args.dry_run); copy_file(repo_root/'codex'/'launcher.py',codex_home/'redteam-mode'/'launcher.py',args.dry_run); write_launcher_scripts(codex_home,args.dry_run); info(f"merge {repo_root/'config.toml'} -> {codex_home/'config.toml'}"); apply_config_merge(config_plan,args.dry_run); seed_prompt_files(repo_root,codex_home,args.dry_run); upsert_agents_file(repo_root,agents_file,args.dry_run)
        copy_file(repo_root/'codex'/'hooks'/'session-start-context.py', codex_home/'hooks'/'session-start-context.py', args.dry_run)
        copy_file(repo_root/'codex'/'hooks'/'hook-security-context-hook.py', codex_home/'hooks'/'hook-security-context-hook.py', args.dry_run)
        copy_file(repo_root/'codex'/'hooks'/'redteam_state.py', codex_home/'hooks'/'redteam_state.py', args.dry_run)
        copy_tree(repo_root/'codex'/'hooks'/'core', codex_home/'hooks'/'core', args.dry_run)
        copy_tree(repo_root/'codex'/'router', codex_home/'router', args.dry_run)
        copy_tree(repo_root/'codex'/'orchestrator', codex_home/'orchestrator', args.dry_run)
        copy_tree(repo_root/'codex'/'automation', codex_home/'automation', args.dry_run)
        copy_tree(repo_root/'codex'/'session_patcher', codex_home/'session_patcher', args.dry_run)
        for skill_dir in repo_skill_dirs(repo_root): copy_skill_md(skill_dir, agents_home/'skills'/skill_dir.name, args.dry_run)
        info(f'apply hooks merge -> {hooks_plan[0]}'); apply_hooks_plan(hooks_plan,args.dry_run)
        deployed=True; update_transaction(codex_home,'deployed',dry_run=args.dry_run)
        manifest_plan=prepare_manifest_payload(codex_home,candidate_manifest,args.dry_run)
        run_validate(repo_root,codex_home,args.dry_run,manifest_plan[1] if manifest_plan else None)
        commit_manifest(manifest_plan,args.dry_run); remove_transaction(codex_home,args.dry_run); good('install complete')
    except BaseException as exc:
        discard_manifest(manifest_plan)
        try: update_transaction(codex_home,'validation_failed' if deployed else 'deployment_failed',error=exc,dry_run=args.dry_run)
        except Exception as transaction_exc: warn(f'could not update pending transaction: {transaction_exc}')
        raise
if __name__=='__main__':
    configure_stdio()
    try: main()
    except (ManifestValidationError,InstallPreflightError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr); raise SystemExit(2)
