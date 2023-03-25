from jaypore_ci import jci

with jci.Pipeline() as p:
    p.job(
        "Pytest",
        "pytest",
        executor_kwargs={
            "extra_hosts": {
                # Access machines behind VPNs
                "machine.behind.vpn": "100.64.0.12",
                # Redirect localhost addresses to the docker gateway
                "dozzle.localhost": "172.0.0.1",
                # Replace production APIs with locally mocked APIs
                "api.myservice.com": "127.0.0.1",
            }
        },
    )
