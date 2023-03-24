from jaypore_ci import jci

pipeline = jci.Pipeline(poll_interval=0)
with pipeline as p:
    for name in "pq":
        p.job(name, name)
    p.job("x", "x")
    p.job("y", "y", depends_on=["x"])
    p.job("z", "z", depends_on=["y"])
    for name in "ab":
        p.job(name, name)

order = pipeline.executor.get_execution_order()
# assert order["x"] < order["y"] < order["z"]
