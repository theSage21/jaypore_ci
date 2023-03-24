from jaypore_ci import jci

with jci.Pipeline() as p:
    p.job("Docker", f"docker build -t myimage .")
    p.job("PyTest", "python3 -m pytest tests/", image="myimage", depends_on=["Docker"])
