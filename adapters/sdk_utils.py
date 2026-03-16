from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Optional


def is_sdk_repo(path: Optional[str]) -> bool:
    if not path:
        return False
    repo = Path(path).expanduser().resolve()
    return (repo / "unitree_sdk2py").is_dir()


def discover_sdk_repo(explicit: Optional[str] = None) -> Optional[Path]:
    candidates = [
        explicit,
        str(Path.home() / "robotic" / "repos" / "unitree_sdk2_python"),
        str(Path.home() / "unitree_sdk2_python"),
        str(Path.home() / "sonic" / "external_dependencies" / "unitree_sdk2_python"),
    ]
    for candidate in candidates:
        if is_sdk_repo(candidate):
            return Path(candidate).expanduser().resolve()

    try:
        for found in Path.home().glob("**/unitree_sdk2_python"):
            if is_sdk_repo(str(found)):
                return found.resolve()
    except Exception:
        pass
    return None


def inject_sdk_repo(repo: Optional[Path]) -> None:
    if repo is None:
        return
    repo_str = str(repo)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)


def sdk_import_origin() -> Optional[str]:
    spec = importlib.util.find_spec("unitree_sdk2py")
    if spec is None:
        return None
    if spec.submodule_search_locations:
        return str(list(spec.submodule_search_locations)[0])
    return spec.origin

