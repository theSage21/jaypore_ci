from jaypore_ci.jci import Pipeline


def test_doc_examples(doc_example_filepath):
    with open(doc_example_filepath, "r", encoding="utf-8") as fl:
        code = fl.read()
    Pipeline.__run_on_exit__ = False
    exec(code)  # pylint: disable=exec-used
    Pipeline.__run_on_exit__ = True
