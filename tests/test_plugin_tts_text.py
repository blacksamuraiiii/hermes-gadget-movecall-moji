"""Spoken Chinese symbols (``textfmt.spoken_symbols``).

Hermes's TTS normaliser reads ``37%`` as "37 percent" and ``2~11℃`` as "2 about 11℃", and its
identifier filter drops the numbers in an ``11/1℃`` range. In a Chinese sentence those come out
of the speaker as English words, so the gadget adapter rewrites them before that normaliser runs.
"""

from __future__ import annotations

from hermes_gadget_plugin import textfmt


def test_a_percentage_is_read_in_chinese():
    assert textfmt.spoken_symbols("湿度37%") == "湿度百分之37"


def test_a_tilde_range_is_read_in_chinese():
    assert textfmt.spoken_symbols("2~11℃，微风") == "2到11℃，微风"


def test_a_slash_range_keeps_its_numbers():
    # Hermes reads "11/1" as a path and drops it ("少云 ℃"); spoken it is a range.
    assert textfmt.spoken_symbols("今天 少云 11/1℃") == "今天 少云 11到1℃"


def test_a_weather_line_survives_in_one_piece():
    line = "扬州 晴 10℃ 体感5℃ 西西北3级 湿度37%；今天 少云 11/1℃；明天 晴 12/2℃"
    assert textfmt.spoken_symbols(line) == (
        "扬州 晴 10℃ 体感5℃ 西西北3级 湿度百分之37；今天 少云 11到1℃；明天 晴 12到2℃"
    )


def test_plain_text_and_empty_input_are_untouched():
    assert textfmt.spoken_symbols("14 点 22 分") == "14 点 22 分"
    assert textfmt.spoken_symbols("") == ""


def test_symbols_a_chinese_tts_misreads_are_words():
    # Hermes turns → into "to" and ≈ into "about"; the rest are skipped or read as punctuation.
    assert textfmt.spoken_symbols("点击 → 下一步") == "点击 到 下一步"
    assert textfmt.spoken_symbols("价格 ≈ 100 元") == "价格 约 100 元"
    assert textfmt.spoken_symbols("误差 ±2") == "误差 正负2"
    assert textfmt.spoken_symbols("湿度 ≤60%") == "湿度 小于等于百分之60"
    assert textfmt.spoken_symbols("3×4 米") == "3乘4 米"
    assert textfmt.spoken_symbols("面积 12㎡") == "面积 12平方米"
