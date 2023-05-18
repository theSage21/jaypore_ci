def test_configs_can_be_generated(config):
    config.run()
    assert str(config.pipeline) == ""
