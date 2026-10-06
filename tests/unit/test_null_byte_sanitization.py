from apps.api.src.services.ingestion_service import _clean_dict_null, _clean_null


def test_clean_null_string():
    assert _clean_null(None) is None
    assert _clean_null("") == ""
    assert _clean_null("hello\x00world") == "helloworld"
    assert _clean_null("clean text") == "clean text"
    assert _clean_null("\x00\x00leading\x00middle\x00trailing\x00") == "leadingmiddletrailing"


def test_clean_dict_null():
    assert _clean_dict_null(None) is None
    assert _clean_dict_null({}) == {}

    data = {
        "key\x00with_null": "value\x00with_null",
        "clean_key": "clean_value",
        "nested_dict": {"inner\x00": "val\x00"},
        "list_items": ["item\x001", "item2", 42],
        "number": 100,
    }

    cleaned = _clean_dict_null(data)
    assert cleaned is not None
    assert "keywith_null" in cleaned
    assert cleaned["keywith_null"] == "valuewith_null"
    assert cleaned["clean_key"] == "clean_value"
    assert cleaned["nested_dict"] == {"inner": "val"}
    assert cleaned["list_items"] == ["item1", "item2", 42]
    assert cleaned["number"] == 100
