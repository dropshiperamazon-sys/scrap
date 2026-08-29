from utils.config_loader import build_app_config, load_config


def test_load_config_returns_defaults_when_file_missing(tmp_path):
    config = load_config(str(tmp_path / "does_not_exist.yaml"))
    assert config["batch_size"] == 5
    assert config["require_website"] is True


def test_load_config_merges_file_over_defaults(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("batch_size: 10\nkeywords:\n  - dentist\n")
    config = load_config(str(config_path))
    assert config["batch_size"] == 10
    assert config["keywords"] == ["dentist"]
    assert config["require_website"] is True  # untouched default survives the merge


def test_build_app_config_applies_overrides():
    raw = load_config("does_not_exist.yaml")
    app_config = build_app_config(raw, {"headless": True, "keywords": ["dentist"], "locations": ["Houston, TX"]})
    assert app_config.headless is True
    assert app_config.keywords == ["dentist"]
    assert app_config.locations == ["Houston, TX"]


def test_combinations_is_location_major_keyword_minor():
    raw = load_config("does_not_exist.yaml")
    app_config = build_app_config(raw, {"keywords": ["a", "b"], "locations": ["X", "Y"]})
    assert app_config.combinations() == [("a", "X"), ("b", "X"), ("a", "Y"), ("b", "Y")]
