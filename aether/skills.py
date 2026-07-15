"""Skill system for Aether.

Mirrors Hermes skills: each skill is a directory with SKILL.md (YAML frontmatter
+ markdown body) and optional reference files. Users can create/update skills via
`aether skills create` / from chat. The agent can load a skill's content into
context when the task matches.

We copy the user's existing Hermes skills into Aether's skills dir on first run
so all the capabilities the user already has carry over.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from . import config


def _skill_dirs() -> List[Path]:
    dirs = []
    for d in config.load_config()["skills"]["dirs"]:
        p = Path(d).expanduser()
        if not p.is_absolute():
            p = config.AETHER_HOME / p
        if p.exists():
            dirs.append(p)
    return dirs


def discover() -> Dict[str, Path]:
    """Return {skill_name: skill_dir} for all discovered skills."""
    found: Dict[str, Path] = {}
    for base in _skill_dirs():
        for child in base.iterdir():
            if child.is_dir() and (child / "SKILL.md").exists():
                found[child.name] = child
    return found


def load_skill(name: str) -> Optional[str]:
    sk = discover().get(name)
    if not sk:
        return None
    return (sk / "SKILL.md").read_text(encoding="utf-8")


def find_relevant(query: str) -> List[str]:
    """Heuristic: return skill names whose description/name appears in the query."""
    q = query.lower()
    out = []
    for name, d in discover().items():
        text = (d / "SKILL.md").read_text(encoding="utf-8", errors="ignore").lower()
        if name.lower() in q or any(w in text for w in q.split() if len(w) > 4):
            out.append(name)
    return out[:3]


def copy_user_skills() -> int:
    """Copy the user's Hermes skills into Aether's skills dir (first run).

    Scans candidate Hermes skill locations recursively for any directory that
    contains a SKILL.md (skills may be nested under category folders).
    """
    candidates = [
        Path.home() / ".hermes" / "skills",
        Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "skills" if os.environ.get("LOCALAPPDATA") else None,
        Path(os.environ.get("APPDATA", "")) / "hermes" / "skills" if os.environ.get("APPDATA") else None,
    ]
    dst = config.AETHER_HOME / "skills"
    dst.mkdir(parents=True, exist_ok=True)

    found = set()
    for base in candidates:
        if not base.exists():
            continue
        for sk in base.rglob("SKILL.md"):
            skill_dir = sk.parent
            found.add(skill_dir)

    n = 0
    for skill_dir in found:
        target = dst / skill_dir.name
        if not target.exists():
            try:
                shutil.copytree(skill_dir, target)
                n += 1
            except Exception as e:
                print(f"[warn] could not copy {skill_dir.name}: {e}")
    return n


def create_skill(name: str, content: str) -> str:
    dst = config.AETHER_HOME / "skills" / name
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "SKILL.md").write_text(content, encoding="utf-8")
    return str(dst)


def delete_skill(name: str) -> bool:
    """Delete a skill directory. Returns True if removed."""
    found = discover().get(name)
    if not found:
        return False
    try:
        shutil.rmtree(found)
        return True
    except Exception as e:
        print(f"[warn] could not delete skill {name}: {e}")
        return False


def get_skill_body(name: str) -> str:
    return load_skill(name) or ""


def set_skill_body(name: str, content: str) -> str:
    """Create or overwrite a skill's SKILL.md; returns the skill dir."""
    return create_skill(name, content)


def list_skills() -> List[Dict[str, object]]:
    """Return [{name, path, enabled, description}] for every discovered skill."""
    out = []
    for name, d in discover().items():
        desc = ""
        try:
            txt = (d / "SKILL.md").read_text(encoding="utf-8", errors="ignore")
            # pull the first non-empty markdown line after frontmatter as a hint
            for line in txt.splitlines():
                line = line.strip()
                if line and not line.startswith("---") and not line.startswith("#"):
                    desc = line[:120]
                    break
        except Exception:
            pass
        out.append({
            "name": name,
            "path": str(d),
            "enabled": config.item_enabled("skills", name, True),
            "description": desc,
        })
    return out
