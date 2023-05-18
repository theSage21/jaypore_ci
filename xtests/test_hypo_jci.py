from hypothesis import given, strategies as st, settings, HealthCheck

from jaypore_ci.clean import allowed_alphabet
from .conftest import ok


@given(st.text(alphabet=allowed_alphabet, min_size=1))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=500)
def test_hypo_jobs(pipeline, name):
    pipeline = pipeline()
    with pipeline as p:
        p.job(name, ok())
