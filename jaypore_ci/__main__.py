from jaypore_ci import jci


def main():
    with jci.Pipeline(image=None, timeout=20 * 60) as p:
        # --- image names
        jci_image = "arjoonn/jaypore_ci:latest"
        rs_image = f"midpath_ph_rs_{p.remote.sha}"
        cloud_image = f"midpath_ph_cl_{p.remote.sha}"
        # Set py image as the default pipeline image
        p.image = py_image = f"midpath_ph_py_{p.remote.sha}"
        # --- check if we should run ci
        p.job("python3 cicd/should_run_pipelines.py", name="Switch", image=jci_image)
        # --- docker
        # --- ============================================
        p.job(
            f"docker build -t {rs_image} deskapp/rs",
            name="docker_rs",
            image=jci_image,
            depends_on=["Switch"],
        )
        p.job(
            f"docker build -t {py_image} api/py",
            name="docker_api",
            image=jci_image,
            depends_on=["Switch"],
        )
        p.job(
            f"docker build -t {cloud_image} deskapp/py",
            name="docker_cloud",
            image=jci_image,
            depends_on=["Switch"],
        )
        # --- linting
        # --- ============================================
        p.job("python3 -m black --check .", name="Black", depends_on=["docker_api"])
        p.job(
            "bash -c '(cd deskapp/py && export PYTHONPATH=$PWD && pylint tests/)'",
            image=cloud_image,
            name="lint_deskapp_tests",
            depends_on=["docker_cloud"],
        )
        p.job(
            "bash -c '(cd deskapp/py && export PYTHONPATH=$PWD && pylint cloud/)'",
            image=cloud_image,
            name="lint_cloud",
            depends_on=["docker_cloud"],
        )
        p.job(
            "bash -c '(cd testing/py && export PYTHONPATH=$PWD && pylint src/)'",
            name="lint_integration_src",
            depends_on=["docker_api"],
        )
        p.job(
            "bash -c '(cd testing/py && export PYTHONPATH=$PWD && pylint tests/)'",
            name="lint_integration_tests",
            depends_on=["docker_api"],
        )
        p.job(
            "bash -c '(cd api/py && export PYTHONPATH=$PWD && pylint --ignored-classes=SQLAlchemy,scoped_session api/)'",
            name="lint_api",
            depends_on=["docker_api"],
        )
        p.job(
            "bash -c '(cd deskapp/rs && cargo check && cargo clippy --no-deps -- -D warnings -A clippy::unnecessary_lazy_evaluations)'",
            name="lint_deskapp",
            image=rs_image,
            depends_on=["docker_rs"],
        )
        # --- testing
        # --- ============================================
        p.job(
            "bash -c '(cd deskapp/py && export PYTHONPATH=$PWD && python3 -m pytest tests)'",
            image=cloud_image,
            name="isotest_cloud",
            depends_on=["docker_cloud"],
        )
        p.job(
            "bash -c '(cd api/py && export PYTHONPATH=$PWD && python3 -m pytest tests)'",
            image=cloud_image,
            name="isotest_api",
            depends_on=["docker_api"],
        )
        p.job(
            "bash -c 'echo ok'",  # TODO: This should be better
            image=cloud_image,
            name="isotest_deskapp",
            depends_on=["docker_api"],
        )
        for env in p.env_matrix(
            BROWSER=["firefox", "chromium", "webkit"],
            MP_ONLINE=["online", "offline"],
        ):
            name = "_".join(
                map(str, [i for pair in sorted(tuple(env.items())) for i in pair])
            )
            p.job(
                "bash -c '(cd testing/py && python3 -m pytest tests)'",
                name=f"integ_{name}",
                image=py_image,
                env=env,
                depends_on=["isotest_cloud", "isotest_api", "isotest_deskapp"],
            )
        print(p.render_graph())


main()
