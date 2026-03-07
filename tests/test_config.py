from app.core.config import Settings


def test_comma_separated_configuration_values_are_parsed() -> None:
    settings = Settings(
        cors_origins="https://app.example.com,https://admin.example.com",
        trusted_hosts="api.example.com,app.example.com",
        ingest_allowed_extensions="pdf,txt,md",
        _env_file=None,
    )

    assert settings.cors_origins == ["https://app.example.com", "https://admin.example.com"]
    assert settings.trusted_hosts == ["api.example.com", "app.example.com"]
    assert settings.ingest_allowed_extensions == ["pdf", "txt", "md"]


def test_output_policy_patterns_support_delimiter_and_json_formats() -> None:
    delimited = Settings(
        output_policy_block_patterns=r"AKIA[0-9A-Z]{16}||ASIA[0-9A-Z]{16}",
        _env_file=None,
    )
    assert delimited.output_policy_block_patterns == [r"AKIA[0-9A-Z]{16}", r"ASIA[0-9A-Z]{16}"]

    json_format = Settings(
        output_policy_block_patterns='["AKIA[0-9A-Z]{16}", "ASIA[0-9A-Z]{16}"]',
        _env_file=None,
    )
    assert json_format.output_policy_block_patterns == [r"AKIA[0-9A-Z]{16}", r"ASIA[0-9A-Z]{16}"]


def test_empty_policy_patterns_string() -> None:
    s = Settings(output_policy_block_patterns="", _env_file=None)
    assert s.output_policy_block_patterns == []


def test_invalid_json_falls_back_to_single_pattern() -> None:
    s = Settings(output_policy_block_patterns='[invalid json', _env_file=None)
    assert s.output_policy_block_patterns == ["[invalid json"]


def test_single_pattern_string_without_delimiter() -> None:
    s = Settings(output_policy_block_patterns=r"AKIA[0-9A-Z]{16}", _env_file=None)
    assert s.output_policy_block_patterns == [r"AKIA[0-9A-Z]{16}"]


def test_json_with_non_list_result() -> None:
    s = Settings(output_policy_block_patterns='{"key": "val"}', _env_file=None)
    # JSON parses but is not a list, should fallback to single pattern
    assert s.output_policy_block_patterns == ['{"key": "val"}']


def test_list_values_passed_directly() -> None:
    s = Settings(output_policy_block_patterns=["a", "b"], _env_file=None)
    assert s.output_policy_block_patterns == ["a", "b"]


def test_comma_separated_already_list() -> None:
    s = Settings(cors_origins=["http://a", "http://b"], _env_file=None)
    assert s.cors_origins == ["http://a", "http://b"]
