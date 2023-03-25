import os
import tomllib
from typing import NamedTuple
import importlib.metadata
from pathlib import Path


class Version(NamedTuple):
    major: int
    minor: int
    patch: int
    trail: str = None

    def __repr__(self):
        if self.trail:
            return f"{self.major}.{self.minor}.{self.patch}-{self.trail}"
        return f"{self.major}.{self.minor}.{self.patch}"

    def __str__(self):
        return self.__repr__()

    @classmethod
    def parse(cls, inp: str) -> "Version":
        if inp is None or inp == "":
            return None
        trail = None
        major, minor, patch = inp.split(".")
        major = major[1:] if major[0].lower() == "v" else major
        assert major.isdigit()
        assert minor.isdigit()
        if "-" in patch:
            patch, trail = patch.split("-", 1)
            assert patch.isdigit()
        return cls(major=int(major), minor=int(minor), patch=int(patch), trail=trail)


def get_version() -> Version:
    try:
        return Version.parse(importlib.metadata.version(__package__ or __name__))
    except importlib.metadata.PackageNotFoundError:
        try:
            with open(
                (Path(__file__) / "../../pyproject.toml").resolve(),
                "rb",
            ) as fl:
                data = tomllib.load(fl)
            return Version.parse(data["tool"]["poetry"]["version"])
        except FileNotFoundError:
            return None


class Const(NamedTuple):
    expected_version: Version = Version.parse(
        os.environ.get("EXPECTED_JAYPORECI_VERSION")
    )
    version: Version = get_version()


const = Const()
