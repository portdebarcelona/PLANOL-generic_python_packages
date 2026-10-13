"""Interprete de Run Python File: python dentro del servicio Compose del repo.

Lo invoca el .cmd de cada carpeta. Traduce rutas del host al workdir del
contenedor y ejecuta ``docker compose run``. Un shell de login no vale:
tiene que ser el ``python`` del PATH de la imagen (el venv).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

_OPTIONS = ("--service", "--container-root", "--host-root", "--compose-file")
_DOCKER = os.environ.get(
    "PLANOL_DOCKER",
    r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
)
# El boton Run Python File usa un solo interprete (el ajuste es
# machine-overridable y, si la comprobacion falla, vuelve al conda del
# usuario). El servicio se elige por la ruta del fichero.
_REPOS = (
    {
        "host": r"C:\dev\python\PLANOL-apb-python-packages",
        "service": "python_planol_dev",
        "container": "/opt/project_apb",
        "compose": r"C:\dev\python\PLANOL-apb-python-packages\docker-compose.yml",
        "docker": ["--no-deps", "-w", "/opt/project_apb"],
    },
    {
        "host": r"C:\dev\python\PLANOL-django_api",
        "service": "planol_django",
        "container": "/planol_django",
        "compose": r"C:\dev\python\PLANOL-django_api\docker-compose.yaml",
        "docker": ["--no-deps", "-e", "WORK_ENV=local", "-w", "/planol_django"],
    },
    {
        "host": r"C:\dev\python\PLANOL-fastapi",
        "service": "planol_fastapi",
        "container": "/opt/project",
        "compose": r"C:\dev\python\PLANOL-fastapi\docker-compose.yml",
        "docker": ["--no-deps", "-w", "/opt/project", "-e", "PYTHONPATH=/opt/project"],
    },
    {
        "host": r"C:\dev\python\PLANOL-generic_python_packages",
        "service": "python_packages",
        "container": "/project",
        "compose": r"C:\dev\python\PLANOL-generic_python_packages\docker-compose.yml",
        "docker": ["--no-deps", "-w", "/project"],
    },
)
_QGIS_HOST = r"C:\dev\qgis\PLANOL-apb-qgis"
_QGIS_BAT = r"C:\dev\qgis\PLANOL-apb-qgis\config\python\python_qgis_DEV.bat"


def _parse(argv: list[str]) -> tuple[dict[str, str], list[str], list[str]]:
    opts: dict[str, str] = {}
    docker_args: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--":
            index += 1
            break
        if arg == "--docker-arg":
            if index + 1 >= len(argv):
                raise SystemExit("Falta el valor de --docker-arg")
            docker_args.append(argv[index + 1])
            index += 2
            continue
        if arg in _OPTIONS:
            if index + 1 >= len(argv):
                raise SystemExit(f"Falta el valor de {arg}")
            opts[arg] = argv[index + 1]
            index += 2
            continue
        break
    missing = [name for name in _OPTIONS if name not in opts]
    if missing:
        raise SystemExit("Faltan opciones: " + ", ".join(missing))
    return opts, docker_args, argv[index:]


def _to_container(
    arg: str,
    host_root: str,
    container_root: str,
    mounts: dict[str, tuple[str, str]],
) -> str:
    if arg.startswith("-"):
        return arg
    normalized = os.path.normpath(arg.replace("/", os.sep))
    if not os.path.isabs(normalized):
        joined = os.path.normpath(os.path.join(host_root, normalized))
        if os.path.exists(joined):
            normalized = joined
    host_key = os.path.normcase(host_root)
    path_key = os.path.normcase(normalized)
    if path_key == host_key or path_key.startswith(host_key + os.sep):
        relative = os.path.relpath(normalized, host_root)
        if relative == ".":
            return container_root
        return container_root.rstrip("/") + "/" + relative.replace("\\", "/")
    # La extension comprueba el interprete con scripts suyos (interpreterInfo.py).
    # Esas rutas no estan en el repo: hay que montarlas o python las busca
    # bajo el workdir y el .cmd deja de ser un interprete valido.
    if os.path.isfile(normalized):
        parent = os.path.dirname(normalized)
        parent_key = os.path.normcase(parent)
        mounted = mounts.get(parent_key)
        if mounted is None:
            mounted = (parent, f"/mnt/host{len(mounts)}")
            mounts[parent_key] = mounted
        return mounted[1] + "/" + os.path.basename(normalized)
    return arg.replace("\\", "/")


def _under(path: str, root: str) -> bool:
    key = os.path.normcase(os.path.normpath(path))
    root_key = os.path.normcase(os.path.normpath(root))
    return key == root_key or key.startswith(root_key + os.sep)


def _candidate_paths(python_args: list[str]) -> list[str]:
    paths: list[str] = []
    skip_code = False
    for arg in python_args:
        if skip_code:
            skip_code = False
            continue
        if arg == "-c":
            skip_code = True
            continue
        if arg.startswith("-"):
            continue
        normalized = os.path.normpath(arg.replace("/", os.sep))
        if not os.path.isabs(normalized):
            normalized = os.path.normpath(os.path.join(os.getcwd(), normalized))
        paths.append(normalized)
    paths.append(os.getcwd())
    return paths


def _repo_for(path: str) -> dict[str, object] | None:
    for repo in _REPOS:
        if _under(path, str(repo["host"])):
            return repo
    return None


def _run_qgis(python_args: list[str]) -> int:
    # CreateProcess no arranca un .bat (EINVAL). Tiene que ser cmd.exe.
    return subprocess.call(["cmd.exe", "/d", "/c", _QGIS_BAT, *python_args])


_HOST_TEST_PYTHON = (
    r"C:\Users\ARREDOER\AppData\Local\miniconda3\envs\PLANOL-apb_python_packages-DEV\python.exe"
)


def _is_vscode_test_adapter(python_args: list[str]) -> bool:
    # El descubridor de unittest habla con Cursor por un pipe del host.
    # No puede ejecutarse dentro del contenedor.
    for arg in python_args:
        normalized = arg.replace("/", "\\").lower()
        if normalized.endswith("\\unittestadapter\\discovery.py") or normalized.endswith(
            "\\unittestadapter\\execution.py"
        ):
            return True
    return False


def _auto(python_args: list[str]) -> int:
    if _is_vscode_test_adapter(python_args):
        if _under(os.getcwd(), _QGIS_HOST):
            return _run_qgis(python_args)
        python = _HOST_TEST_PYTHON if os.path.isfile(_HOST_TEST_PYTHON) else sys.executable
        return subprocess.call([python, *python_args])
    probe = any(arg.endswith("interpreterInfo.py") or arg.endswith("get_output_via_markers.py") for arg in python_args)
    for path in _candidate_paths(python_args):
        if not probe and _under(path, _QGIS_HOST):
            return _run_qgis(python_args)
        repo = _repo_for(path)
        if repo is not None:
            return _run_docker(repo, python_args)
    return _run_docker(_REPOS[0], python_args)


def _run_docker(repo: dict[str, object], python_args: list[str]) -> int:
    opts = {
        "--service": str(repo["service"]),
        "--container-root": str(repo["container"]),
        "--host-root": str(repo["host"]),
        "--compose-file": str(repo["compose"]),
    }
    return _execute(opts, list(repo["docker"]), python_args)


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] not in _OPTIONS and argv[0] != "--docker-arg":
        return _auto(argv)
    opts, docker_args, python_args = _parse(argv)
    return _execute(opts, docker_args, python_args)


def _execute(opts: dict[str, str], docker_args: list[str], python_args: list[str]) -> int:
    host_root = os.path.realpath(opts["--host-root"])
    container_root = opts["--container-root"]
    translated: list[str] = []
    mounts: dict[str, tuple[str, str]] = {}
    skip_code = False
    for arg in python_args:
        if skip_code:
            translated.append(arg)
            skip_code = False
            continue
        if arg == "-c":
            translated.append(arg)
            skip_code = True
            continue
        translated.append(_to_container(arg, host_root, container_root, mounts))
    for parent, container_dir in mounts.values():
        docker_args.extend(["-v", f"{parent}:{container_dir}:ro"])
    docker = _DOCKER if os.path.isfile(_DOCKER) else (shutil.which("docker") or "docker")
    if not docker_args:
        docker_args = ["--no-deps"]
    command = [
        docker,
        "compose",
        "--progress",
        "quiet",
        "-f",
        opts["--compose-file"],
        "--project-directory",
        host_root,
        "run",
        "--rm",
        *docker_args,
        opts["--service"],
        "python",
        *translated,
    ]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
