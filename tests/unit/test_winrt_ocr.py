from sniplingo.adapters.winrt_ocr import _to_ocr_result
from sniplingo.domain.models import OcrWord


class _Rect:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.width, self.height = x, y, w, h


class _Word:
    def __init__(self, text, rect):
        self.text = text
        self.bounding_rect = rect


class _Line:
    def __init__(self, text, words):
        self.text = text
        self.words = words


class _Result:
    def __init__(self, lines):
        self.lines = lines


def test_to_ocr_result_maps_lines_words_and_truncates_float_rects():
    winrt_result = _Result(
        [
            _Line(
                "Save your",
                [
                    _Word("Save", _Rect(13.0, 46.0, 123.0, 42.0)),
                    _Word("your", _Rect(150.0, 46.0, 90.0, 42.0)),
                ],
            ),
            _Line("progress?", [_Word("progress?", _Rect(18.9, 98.0, 243.0, 62.0))]),
        ]
    )

    result = _to_ocr_result(winrt_result)

    assert result.line_texts == ["Save your", "progress?"]
    assert result.lines[0].words[0] == OcrWord("Save", 13, 46, 123, 42)
    assert result.lines[1].words[0].left == 18  # 18.9 truncated to int


def test_to_ocr_result_empty():
    assert _to_ocr_result(_Result([])).is_empty
