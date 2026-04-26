"""ENVI Task Engine discovery and execution helpers."""

from __future__ import annotations

import concurrent.futures
import importlib
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

logger = logging.getLogger(__name__)

SAR_KEYWORDS: tuple[str, ...] = (
    "sar",
    "sarscape",
    "insar",
    "interfer",
    "sentinel",
    "radar",
    "slc",
)

DEFAULT_SHORTCUT_PATHS: tuple[Path, ...] = (
    Path.home() / "Desktop" / "ENVI 5.6 (64-bit).lnk",
)


class ENVIEngineError(Exception):
    """Raised when ENVI Task Engine cannot be imported, located, or started."""


@dataclass(frozen=True)
class EngineDiscoveryResult:
    """JSON-friendly result for taskengine.exe discovery."""

    path: Optional[Path]
    source: Optional[str]
    exists: bool
    attempted: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path) if self.path else None,
            "source": self.source,
            "exists": self.exists,
            "attempted": list(self.attempted),
        }


class ENVIEngineManager:
    """Manage ENVI Task Engine discovery, startup, task inspection, and runs."""

    def __init__(
        self,
        engine_path: Optional[Union[str, Path]] = None,
        shortcut_paths: Sequence[Union[str, Path]] = DEFAULT_SHORTCUT_PATHS,
    ) -> None:
        self._engine_path = Path(engine_path) if engine_path else None
        self._shortcut_paths = tuple(Path(path) for path in shortcut_paths)
        self._discovery_result: Optional[EngineDiscoveryResult] = None
        self._engine: Optional[Any] = None

    def discover_taskengine(self, refresh: bool = False) -> EngineDiscoveryResult:
        """Find taskengine.exe, honoring ENVI_ENGINE before other sources."""

        if self._discovery_result and not refresh:
            return self._discovery_result

        attempted: list[str] = []
        candidate_sources: tuple[tuple[str, Iterable[Path]], ...] = (
            ("ENVI_ENGINE", self._env_engine_candidates()),
            ("constructor", self._constructor_candidates()),
            ("common_paths", self._common_path_candidates()),
            ("registry", self._registry_candidates()),
            ("shortcut", self._shortcut_candidates()),
            ("PATH", self._path_candidates()),
        )

        for source, candidates in candidate_sources:
            for candidate in candidates:
                attempted.append(f"{source}: {candidate}")
                taskengine = self._resolve_taskengine_candidate(candidate)
                if taskengine:
                    self._discovery_result = EngineDiscoveryResult(
                        path=taskengine,
                        source=source,
                        exists=taskengine.exists(),
                        attempted=tuple(attempted),
                    )
                    return self._discovery_result

        self._discovery_result = EngineDiscoveryResult(
            path=None,
            source=None,
            exists=False,
            attempted=tuple(attempted),
        )
        return self._discovery_result

    def configure_environment(self) -> EngineDiscoveryResult:
        """Set process environment hints expected by envipyengine when possible."""

        discovery = self.discover_taskengine()
        if not discovery.path:
            return discovery

        os.environ.setdefault("ENVI_ENGINE", str(discovery.path))
        taskengine_dir = str(discovery.path.parent)
        path_parts = tuple(os.environ.get("PATH", "").split(os.pathsep))
        if taskengine_dir not in path_parts:
            os.environ["PATH"] = os.pathsep.join((taskengine_dir, *path_parts))
        return discovery

    def get_engine(self) -> Any:
        """Return a cached envipyengine Engine("ENVI") instance."""

        if self._engine is not None:
            return self._engine

        self.configure_environment()
        try:
            envipyengine = importlib.import_module("envipyengine")
        except ImportError as exc:
            raise ENVIEngineError(
                "Could not import envipyengine. Run this with the ENVI Task Engine "
                "Python environment, or make envipyengine importable."
            ) from exc

        engine_factory = getattr(envipyengine, "Engine", None)
        if engine_factory is None:
            raise ENVIEngineError("envipyengine does not expose Engine.")

        try:
            self._engine = engine_factory("ENVI")
        except Exception as exc:
            raise ENVIEngineError(f"Could not start Engine('ENVI'): {exc}") from exc
        return self._engine

    def list_tasks(self, filter_str: str = "") -> list[str]:
        """List ENVI tasks, optionally filtering case-insensitively."""

        task_names = self._normalise_task_names(self._get_task_collection(self.get_engine()))
        if not filter_str:
            return sorted(task_names)

        needle = filter_str.casefold()
        return sorted(name for name in task_names if needle in name.casefold())

    def task_info(self, task_name: str) -> dict[str, Any]:
        """Return best-effort metadata for an ENVI task."""

        task = self._create_task(task_name)
        info: dict[str, Any] = {"name": task_name}
        for attr_name in (
            "display_name",
            "description",
            "revision",
            "parameters",
            "input_parameters",
            "output_parameters",
            "parameter_info",
            "tags",
        ):
            value = getattr(task, attr_name, None)
            if value is None:
                continue
            if callable(value):
                try:
                    value = value()
                except TypeError:
                    continue
            info[attr_name] = to_jsonable(value)
        return info

    def find_task(
        self,
        candidate_names: Sequence[str] = (),
        keywords: Sequence[str] = (),
    ) -> Optional[str]:
        """Find the first installed task matching candidate names or keywords."""

        installed = self.list_tasks()
        installed_by_casefold = {task.casefold(): task for task in installed}

        for candidate_name in candidate_names:
            exact = installed_by_casefold.get(candidate_name.casefold())
            if exact:
                return exact

        compact_installed = {
            _compact_task_name(task): task
            for task in installed
        }
        for candidate_name in candidate_names:
            compact_candidate = _compact_task_name(candidate_name)
            if compact_candidate in compact_installed:
                return compact_installed[compact_candidate]
            for compact_task, task in compact_installed.items():
                if compact_candidate and compact_candidate in compact_task:
                    return task

        keyword_tuple = tuple(keyword.casefold() for keyword in keywords if keyword)
        if keyword_tuple:
            for task in installed:
                haystack = task.casefold()
                if all(keyword in haystack for keyword in keyword_tuple):
                    return task
        return None

    def run_first_available_task(
        self,
        candidate_names: Sequence[str],
        keywords: Sequence[str],
        params: Mapping[str, Any],
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Run the first installed task matching a logical tool definition."""

        task_name = self.find_task(candidate_names, keywords)
        if not task_name:
            return {
                "success": False,
                "error": "No matching ENVI/SARScape task was found.",
                "candidate_names": list(candidate_names),
                "keywords": list(keywords),
            }
        return self.run_task(task_name, params, timeout=timeout)

    def run_task(
        self,
        task_name: str,
        params: Mapping[str, Any],
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Execute an ENVI task and return a JSON-friendly status dict."""

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._execute_task, task_name, dict(params))
        try:
            task_result = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            executor.shutdown(wait=False, cancel_futures=True)
            return {
                "success": False,
                "task_name": task_name,
                "error": f"Task timed out after {timeout} seconds.",
            }
        except Exception as exc:
            executor.shutdown(wait=True, cancel_futures=True)
            logger.exception("ENVI task failed: %s", task_name)
            return {
                "success": False,
                "task_name": task_name,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            }
        executor.shutdown(wait=True, cancel_futures=True)
        return {
            "success": True,
            "task_name": task_name,
            **task_result,
        }

    def connectivity_check(self) -> dict[str, Any]:
        """Run the local ENVI/SARScape acceptance check."""

        report: dict[str, Any] = {
            "python": {
                "version": sys.version,
                "executable": sys.executable,
                "platform": platform.platform(),
            },
            "envipyengine_importable": False,
            "taskengine": self.discover_taskengine(refresh=True).to_dict(),
            "envi_started": False,
            "task_count": 0,
            "sar_task_count": 0,
            "sar_task_examples": [],
            "success": False,
            "errors": [],
            "suggestions": [],
        }

        try:
            importlib.import_module("envipyengine")
            report["envipyengine_importable"] = True
        except ImportError as exc:
            report["errors"].append(f"envipyengine import failed: {exc}")
            report["suggestions"].append(
                "Run with the Python environment installed by ENVI Task Engine, "
                "or add envipyengine to PYTHONPATH."
            )

        if report["taskengine"]["path"] is None:
            report["suggestions"].append(
                "Set ENVI_ENGINE to the full taskengine.exe path if auto-discovery misses it."
            )

        try:
            tasks = self.list_tasks()
            sar_tasks = [task for task in tasks if _is_sar_task(task)]
            report = {
                **report,
                "envi_started": True,
                "task_count": len(tasks),
                "sar_task_count": len(sar_tasks),
                "sar_task_examples": sar_tasks[:20],
            }
        except Exception as exc:
            report["errors"].append(f"ENVI startup or task listing failed: {exc}")
            report["suggestions"].append(
                "Check that ENVI/SARScape licensing is available and taskengine.exe is usable."
            )

        report["success"] = bool(
            report["envipyengine_importable"]
            and report["envi_started"]
            and report["task_count"] > 0
            and report["sar_task_count"] > 0
        )
        return report

    def _execute_task(self, task_name: str, params: Mapping[str, Any]) -> dict[str, Any]:
        task = self._create_task(task_name)
        self._apply_parameters(task, params)
        execute = getattr(task, "execute", None)
        if callable(execute):
            result = execute()
        else:
            engine_run_task = getattr(self.get_engine(), "run_task", None)
            if not callable(engine_run_task):
                raise ENVIEngineError(f"Task {task_name} is not executable.")
            result = engine_run_task(task_name, **dict(params))
        return {
            "result": to_jsonable(result),
            "outputs": self._collect_outputs(task),
        }

    def _create_task(self, task_name: str) -> Any:
        engine = self.get_engine()
        for attr_name in ("task", "get_task", "create_task"):
            attr = getattr(engine, attr_name, None)
            if callable(attr):
                return attr(task_name)
        try:
            return engine[task_name]
        except (KeyError, TypeError, AttributeError) as exc:
            raise ENVIEngineError(f"Could not create task {task_name}.") from exc

    def _get_task_collection(self, engine: Any) -> Any:
        for attr_name in ("task_names", "list_tasks", "tasks"):
            attr = getattr(engine, attr_name, None)
            if attr is None:
                continue
            if callable(attr):
                return attr()
            return attr
        raise ENVIEngineError("Could not list tasks from envipyengine Engine.")

    @staticmethod
    def _normalise_task_names(task_collection: Any) -> tuple[str, ...]:
        if isinstance(task_collection, str):
            return (task_collection,)
        if isinstance(task_collection, Mapping):
            return tuple(str(key) for key in task_collection.keys())
        if isinstance(task_collection, Iterable):
            names: list[str] = []
            for item in task_collection:
                name = getattr(item, "name", item)
                names.append(str(name))
            return tuple(names)
        raise ENVIEngineError("ENVI task collection is not iterable.")

    @staticmethod
    def _apply_parameters(task: Any, params: Mapping[str, Any]) -> None:
        task_parameters = getattr(task, "parameters", None)
        if isinstance(task_parameters, dict):
            task_parameters.update(dict(params))
        for key, value in params.items():
            setter = getattr(task, "set_parameter", None)
            if callable(setter):
                setter(key, value)
                continue
            try:
                setattr(task, key, value)
            except (AttributeError, TypeError):
                logger.debug("Could not set task parameter %s via attribute", key)

    @staticmethod
    def _collect_outputs(task: Any) -> dict[str, Any]:
        outputs: dict[str, Any] = {}
        for attr_name in ("outputs", "output_parameters", "output", "result"):
            value = getattr(task, attr_name, None)
            if value is None:
                continue
            if callable(value):
                try:
                    value = value()
                except TypeError:
                    continue
            outputs[attr_name] = to_jsonable(value)
        return outputs

    def _env_engine_candidates(self) -> tuple[Path, ...]:
        value = os.environ.get("ENVI_ENGINE")
        return (Path(value),) if value else ()

    def _constructor_candidates(self) -> tuple[Path, ...]:
        return (self._engine_path,) if self._engine_path else ()

    @staticmethod
    def _common_path_candidates() -> tuple[Path, ...]:
        roots = tuple(
            Path(value)
            for value in (
                os.environ.get("ProgramFiles"),
                os.environ.get("ProgramFiles(x86)"),
                "C:/Program Files",
                "C:/Program Files (x86)",
            )
            if value
        )
        vendors = ("Harris", "NV5", "Exelis", "ITT")
        versions = ("ENVI60", "ENVI56", "ENVI55", "ENVI54", "IDL90", "IDL89", "IDL88")
        candidates: list[Path] = []
        for root in roots:
            for vendor in vendors:
                vendor_root = root / vendor
                candidates.append(vendor_root)
                for version in versions:
                    candidates.extend(
                        (
                            vendor_root / version,
                            vendor_root / version / version,
                            vendor_root / version / "bin",
                            vendor_root / version / "bin" / "bin.x86_64",
                            vendor_root / version / version / "bin" / "bin.x86_64",
                        )
                    )
        return tuple(dict.fromkeys(candidates))

    @staticmethod
    def _registry_candidates() -> tuple[Path, ...]:
        if platform.system() != "Windows":
            return ()
        try:
            import winreg
        except ImportError:
            return ()

        uninstall_paths = (
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        )
        roots = (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER)
        candidates: list[Path] = []
        for root in roots:
            for uninstall_path in uninstall_paths:
                try:
                    with winreg.OpenKey(root, uninstall_path) as uninstall_key:
                        subkey_count = winreg.QueryInfoKey(uninstall_key)[0]
                        for index in range(subkey_count):
                            try:
                                subkey_name = winreg.EnumKey(uninstall_key, index)
                                with winreg.OpenKey(uninstall_key, subkey_name) as app_key:
                                    display_name = _query_registry_value(winreg, app_key, "DisplayName")
                                    install_location = _query_registry_value(winreg, app_key, "InstallLocation")
                            except OSError:
                                continue
                            if not display_name or not _looks_like_envi_install(display_name):
                                continue
                            if install_location:
                                candidates.append(Path(install_location))
                except OSError:
                    continue
        return tuple(dict.fromkeys(candidates))

    def _shortcut_candidates(self) -> tuple[Path, ...]:
        if platform.system() != "Windows":
            return ()
        candidates: list[Path] = []
        for shortcut_path in self._shortcut_paths:
            if not shortcut_path.exists():
                continue
            target = _resolve_windows_shortcut(shortcut_path)
            if not target:
                continue
            candidates.append(target)
            candidates.extend(target.parents)
        return tuple(dict.fromkeys(candidates))

    @staticmethod
    def _path_candidates() -> tuple[Path, ...]:
        candidates: list[Path] = []
        taskengine = shutil.which("taskengine.exe")
        if taskengine:
            candidates.append(Path(taskengine))
        for part in os.environ.get("PATH", "").split(os.pathsep):
            if part:
                candidates.append(Path(part))
        return tuple(dict.fromkeys(candidates))

    @staticmethod
    def _resolve_taskengine_candidate(candidate: Path) -> Optional[Path]:
        candidate = candidate.expanduser()
        if candidate.name.casefold() == "taskengine.exe":
            return candidate
        if candidate.is_file():
            return candidate if candidate.name.casefold() == "taskengine.exe" else None
        if not candidate.exists() or not candidate.is_dir():
            return None

        direct_candidates = (
            candidate / "taskengine.exe",
            candidate / "bin" / "taskengine.exe",
            candidate / "bin" / "bin.x86_64" / "taskengine.exe",
        )
        for direct_candidate in direct_candidates:
            if direct_candidate.exists():
                return direct_candidate

        if _looks_like_envi_install(str(candidate)):
            try:
                found_candidates = sorted(candidate.rglob("taskengine.exe"), key=_taskengine_preference_key)
                if found_candidates:
                    return found_candidates[0]
            except OSError:
                return None
        return None


def get_default_manager() -> ENVIEngineManager:
    """Return the module-level ENVI engine manager."""

    return _DEFAULT_MANAGER


def to_jsonable(value: Any) -> Any:
    """Convert arbitrary envipyengine objects into JSON-friendly values."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return to_jsonable(model_dump())
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(item) for item in value]
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _compact_task_name(name: str) -> str:
    return "".join(character for character in name.casefold() if character.isalnum())


def _is_sar_task(task_name: str) -> bool:
    haystack = task_name.casefold()
    return any(keyword in haystack for keyword in SAR_KEYWORDS)


def _looks_like_envi_install(value: str) -> bool:
    haystack = value.casefold()
    return any(token in haystack for token in ("envi", "idl", "sarscape", "harris", "nv5", "exelis"))


def _taskengine_preference_key(path: Path) -> tuple[int, int, str]:
    text = str(path).casefold()
    if "x86_64" in text or "x64" in text or "64" in text:
        architecture_rank = 0
    elif "x86" in text:
        architecture_rank = 1
    else:
        architecture_rank = 2
    return (architecture_rank, len(text), text)


def _query_registry_value(winreg: Any, key: Any, name: str) -> Optional[str]:
    try:
        value, _ = winreg.QueryValueEx(key, name)
    except OSError:
        return None
    return str(value) if value else None


def _resolve_windows_shortcut(shortcut_path: Path) -> Optional[Path]:
    quoted_shortcut = str(shortcut_path).replace("'", "''")
    command = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut('{quoted_shortcut}'); "
        "$shortcut.TargetPath"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("Could not resolve shortcut %s: %s", shortcut_path, exc)
        return None
    target = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""
    return Path(target) if target else None


_DEFAULT_MANAGER = ENVIEngineManager()