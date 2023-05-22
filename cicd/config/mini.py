from jayporeci.shortcuts import run

with run() as sch:
    sch.job("lint", "black --check .")
    sch.job("pyre", "pyre --strict")
