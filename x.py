from jayporeci.shortcuts import run

with run() as p:
    p = p.job("lint", "black --check .")
    p = p.job("test", "pytest .", after="lint")
