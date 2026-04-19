from lssql.parser import (
    parse_filename,
    split_filename_stem,
    split_extension,
    should_skip,
)

# round trip test to reconstruct the original filename


def test_round_trip_plain():
    original = "IMG_4520.jpg"
    parsed = parse_filename(original)
    reconstructed = parsed["original"] + parsed["ext"]
    assert reconstructed == original


def test_round_trip_harvested():
    original = "IMG_4520^^^ls:fh=9b1d4e72ac^ud:2006-london=1^^^nice-to-meet-you.jpg"
    parsed = parse_filename(original)
    reconstructed = (
        parsed["original"]
        + "^^^"
        + "^".join(f"{k}={v}" for k, v in parsed["tags"].items())
        + "^^^"
        + parsed["comment"]
        + parsed["ext"]
    )
    assert reconstructed == original


def test_round_trip_no_comment():
    original = "0002-2345678901^^^ud:test=hello.jpg"
    parsed = parse_filename(original)
    reconstructed = (
        parsed["original"]
        + "^^^"
        + "^".join(f"{k}={v}" for k, v in parsed["tags"].items())
        + parsed["ext"]
    )
    assert reconstructed == original


# test parse_filename


def test_plain_filename():
    result = parse_filename("IMG_4520.jpg")
    assert result["original"] == "IMG_4520"
    assert result["ext"] == ".jpg"
    assert result["tags"] == {}
    assert result["comment"] == ""
    assert result["harvested"] is False


def test_harvested_filename():
    result = parse_filename(
        "IMG_4520^^^ls:fh=9b1d4e72ac^ud:2006-london=1^^^nice-to-meet-you.jpg"
    )
    assert result["original"] == "IMG_4520"
    assert result["tags"]["ls:fh"] == "9b1d4e72ac"
    assert result["tags"]["ud:2006-london"] == "1"
    assert result["comment"] == "nice-to-meet-you"
    assert result["harvested"] is True


def test_harvested_filename_no_head():
    result = parse_filename(
        "^^^ls:fh=9b1d4e72ac^ud:2006-london=1^^^nice-to-meet-you.jpg"
    )
    assert result["original"] == ""
    assert result["tags"]["ls:fh"] == "9b1d4e72ac"
    assert result["tags"]["ud:2006-london"] == "1"
    assert result["comment"] == "nice-to-meet-you"
    assert result["harvested"] is True


def test_harvested_filename_no_tail():
    result = parse_filename("IMG_4520^^^ls:fh=9b1d4e72ac^ud:2006-london=1^^^.jpg")
    assert result["original"] == "IMG_4520"
    assert result["tags"]["ls:fh"] == "9b1d4e72ac"
    assert result["tags"]["ud:2006-london"] == "1"
    assert result["comment"] == ""
    assert result["harvested"] is True


def test_harvested_filename_no_tail_hat():
    result = parse_filename("IMG_4520^^^ls:fh=9b1d4e72ac^ud:2006-london=1.jpg")
    assert result["original"] == "IMG_4520"
    assert result["tags"]["ls:fh"] == "9b1d4e72ac"
    assert result["tags"]["ud:2006-london"] == "1"
    assert result["comment"] == ""
    assert result["harvested"] is True


def test_harvested_filename_too_many():
    result = parse_filename(
        "IMG_4520^^^ls:fh=9b1d4e72ac^ud:2006-london=1^^^nice-to-meet-you^^^.jpg"
    )
    assert (
        result["original"]
        == "IMG_4520^^^ls:fh=9b1d4e72ac^ud:2006-london=1^^^nice-to-meet-you^^^"
    )
    assert result["tags"] == {}
    assert result["comment"] == ""
    assert result["harvested"] is False


# test split_filename_stem


SEPARATOR = "^^^"


def test_none_stem():
    stem = None
    original, raw_tags, comment = split_filename_stem(stem, SEPARATOR)
    assert original == None
    assert raw_tags == None
    assert comment == None


def test_empty_stem():
    stem = ""
    original, raw_tags, comment = split_filename_stem(stem, SEPARATOR)
    assert original == None
    assert raw_tags == None
    assert comment == None


def test_dot_stem():
    stem = "."
    original, raw_tags, comment = split_filename_stem(stem, SEPARATOR)
    assert original == None
    assert raw_tags == None
    assert comment == None


def test_dot_dot_stem():
    stem = ".."
    original, raw_tags, comment = split_filename_stem(stem, SEPARATOR)
    assert original == None
    assert raw_tags == None
    assert comment == None


def test_stem_no_separator():
    stem = "0001-01234"
    original, raw_tags, comment = split_filename_stem(stem, SEPARATOR)
    assert original == "0001-01234"
    assert raw_tags == ""
    assert comment == ""


def test_stem_one_separator():
    stem = "0001-01234^^^ud:colour=blue"
    original, raw_tags, comment = split_filename_stem(stem, SEPARATOR)
    assert original == "0001-01234"
    assert raw_tags == "ud:colour=blue"
    assert comment == ""


def test_stem_two_separator():
    stem = "0001-01234^^^ud:colour=blue^^^it-is-blue"
    original, raw_tags, comment = split_filename_stem(stem, SEPARATOR)
    assert original == "0001-01234"
    assert raw_tags == "ud:colour=blue"
    assert comment == "it-is-blue"


def test_stem_three_separator():
    stem = "0001-01234^^^ud:colour=blue^^^it-is-blue^^^yes-blue-it-is"
    original, raw_tags, comment = split_filename_stem(stem, SEPARATOR)
    assert original == "0001-01234^^^ud:colour=blue^^^it-is-blue^^^yes-blue-it-is"
    assert raw_tags == ""
    assert comment == ""


# test split_extension


def test_extension_no_period():
    result = split_extension("IMG_4520")
    assert result == ("IMG_4520", "")


def test_extension_one_period():
    result = split_extension("IMG_4520.jpg")
    assert result == ("IMG_4520", ".jpg")


def test_extension_two_period():
    result = split_extension("IMG_4520.foo.jpg")
    assert result == ("IMG_4520.foo", ".jpg")


# test should_skip


def test_should_skip():
    assert should_skip(None)
    assert should_skip("")
    assert should_skip(".")
    assert should_skip("..")

    assert not should_skip("ab")
    assert not should_skip("abc")
