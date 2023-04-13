from typing import List, Dict
import subprocess


def run(
    *,
    image: str,
    name: str,
    command: str,
    volumes: List[str] = None,
    environment: Dict[str, str] = None,
    workdir: str = None,
) -> str:
    """
    Perform docker run and return the output of that command.
    """
    volumes = [] if volumes is None else volumes
    assert all(isinstance(vol, str) for vol in volumes)
    environment = {} if environment is None else environment
    assert all(
        isinstance(key, str) and isinstance(val, str)
        for key, val in environment.items()
    )
    # ---
    cmd = ["docker", "run"]
    cmd += ["--name", f"'{name}'"]
    if workdir:
        cmd += ["--workdir", f"{workdir}"]
    cmd += [f"-v {vol}" for vol in volumes]
    cmd += [f"-e {key}={val}" for key, val in environment.items()]
    cmd += [image, command]

    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, shell=True
    )
    return proc.stdout.decode()


def build(*, tag: str, path: str = ".", dockerfile: str = None) -> str:
    "Perform docker build"
    cmd = ["docker", "build", "-t", tag]
    if dockerfile:
        cmd += ["-f", dockerfile]
    cmd += [path]
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, shell=True
    )
    return proc.stdout.decode()


def ps(*, f: Dict[str, str] = None):
    cmd = ["docker", "ps"]
    if f:
        cmd += [arg for key, value in f.items() for arg in ["-f", f"{key}={value}"]]
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, shell=True
    )
    return proc.stdout.decode()


def network_ls(*, f: Dict[str, List[str]] = None):
    cmd = ["docker", "network", "ls"]
    if f:
        for key, val in f.items():
            if isinstance(val, (list, tuple)):
                for v in val:
                    cmd += ["-f", f"{name}={v}"]
            else:
                cmd += ["-f", f"{name}={val}"]

    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, shell=True
    )
    return proc.stdout.decode()
