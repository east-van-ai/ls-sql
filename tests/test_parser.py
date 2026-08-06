# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

from lssql.parser import (
    build_file_path,
    parse_filename,
    should_skip,
    split_extension,
    split_filename_stem,
    split_path,
)

# round trip test to reconstruct the original filename


def test_round_trip_plain():
    original = "IMG_4520.jpg"
    parsed = parse_filename(original)
    reconstructed = parsed["original"] + parsed["ext"]
    assert reconstructed == original


def test_round_trip_harvested():
    original = (
        "IMG_4520^^^ls:fh=03754271b00a0e1c^ud:2006-london=1^^^nice-to-meet-you.jpg"
    )
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
        "IMG_4520^^^ls:fh=03754271b00a0e1c^ud:2006-london=1^^^nice-to-meet-you.jpg"
    )
    assert result["original"] == "IMG_4520"
    assert result["tags"]["ls:fh"] == "03754271b00a0e1c"
    assert result["tags"]["ud:2006-london"] == "1"
    assert result["comment"] == "nice-to-meet-you"
    assert result["harvested"] is True


def test_harvested_filename_no_head():
    result = parse_filename(
        "^^^ls:fh=03754271b00a0e1c^ud:2006-london=1^^^nice-to-meet-you.jpg"
    )
    assert result["original"] == ""
    assert result["tags"]["ls:fh"] == "03754271b00a0e1c"
    assert result["tags"]["ud:2006-london"] == "1"
    assert result["comment"] == "nice-to-meet-you"
    assert result["harvested"] is True


def test_harvested_filename_no_tail():
    result = parse_filename("IMG_4520^^^ls:fh=03754271b00a0e1c^ud:2006-london=1^^^.jpg")
    assert result["original"] == "IMG_4520"
    assert result["tags"]["ls:fh"] == "03754271b00a0e1c"
    assert result["tags"]["ud:2006-london"] == "1"
    assert result["comment"] == ""
    assert result["harvested"] is True


def test_harvested_filename_no_tail_hat():
    result = parse_filename("IMG_4520^^^ls:fh=03754271b00a0e1c^ud:2006-london=1.jpg")
    assert result["original"] == "IMG_4520"
    assert result["tags"]["ls:fh"] == "03754271b00a0e1c"
    assert result["tags"]["ud:2006-london"] == "1"
    assert result["comment"] == ""
    assert result["harvested"] is True


def test_harvested_filename_too_many():
    result = parse_filename(
        "IMG_4520^^^ls:fh=03754271b00a0e1c^ud:2006-london=1^^^nice-to-meet-you^^^.jpg"
    )
    assert (
        result["original"]
        == "IMG_4520^^^ls:fh=03754271b00a0e1c^ud:2006-london=1^^^nice-to-meet-you^^^"
    )
    assert result["tags"] == {}
    assert result["comment"] == ""
    assert result["harvested"] is False


# test split_filename_stem


SEPARATOR = "^^^"


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


# test split_path


def test_filepath_end_with_slash():
    result = split_path("DIRECTORY_NAME/")
    assert result == ("DIRECTORY_NAME", "")


def test_filepath_no_slash():
    result = split_path("FILE_NAME")
    assert result == ("", "FILE_NAME")


def test_filepath_hidden_file():
    result = split_path("/User/go/.hidden_file")
    assert result == ("/User/go", ".hidden_file")


def test_filepath_file_without_extension():
    result = split_path("/User/go/IMG_4520")
    assert result == ("/User/go", "IMG_4520")


def test_filepath_file_with_extension():
    result = split_path("/User/go/IMG_4520.jpg")
    assert result == ("/User/go", "IMG_4520.jpg")


def test_filepath_with_three_carets():
    result = split_path("/User/go^^^/IMG_4520.jpg")
    assert result == ("/User/go^^^", "IMG_4520.jpg")


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
    assert should_skip(None)  # type: ignore
    assert should_skip("")
    assert should_skip(".")
    assert should_skip("..")
    assert should_skip(".hidden-file")
    assert should_skip(".hidden-file.jpg")
    assert should_skip("filename-without-extension")
    assert should_skip("filename-without-extension.")

    assert not should_skip("ab.jpg")
    assert not should_skip("abc.mp3")


# test build_file_path


def test_build_file_path():
    assert (
        build_file_path({"path": "src/lib", "filename": "lib.py"}) == "src/lib/lib.py"
    )


def test_build_file_path_empty_path():
    assert build_file_path({"path": "", "filename": "cli.py"}) == "cli.py"


def test_build_file_path_None_path():
    assert build_file_path({"path": None, "filename": "cli.py"}) == "cli.py"
