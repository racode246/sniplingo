"""Unit tests for OCR image preprocessing.

Pure Pillow transforms — no Windows / network / Qt, so this stays a fast unit test.
"""

from PIL import Image, ImageDraw

from sniplingo.adapters.image_preprocess import MAX_OCR_DIMENSION, preprocess_for_ocr


def test_upscales_by_integer_factor():
    out = preprocess_for_ocr(Image.new("RGB", (40, 20), (0, 0, 0)), scale=3, margin=0)
    assert out.size == (120, 60)


def test_scale_one_keeps_size():
    out = preprocess_for_ocr(Image.new("RGB", (50, 25), (0, 0, 0)), scale=1, margin=0)
    assert out.size == (50, 25)


def test_converts_to_grayscale():
    # Color text (e.g. red on dark) is flattened to luminance so OCR isn't thrown by hue.
    out = preprocess_for_ocr(Image.new("RGB", (10, 10), (200, 30, 30)), scale=1, margin=0)
    assert out.mode == "L"


def test_low_contrast_input_is_stretched_to_full_range():
    # Pixels confined to a narrow band -> autocontrast expands them to 0..255 so faint,
    # low-contrast text (colored-on-dark) becomes crisp for the engine.
    img = Image.new("L", (4, 1))
    img.putdata([100, 102, 104, 106])
    out = preprocess_for_ocr(img, scale=1, margin=0)
    assert out.getextrema() == (0, 255)


def test_non_positive_scale_is_treated_as_one():
    out = preprocess_for_ocr(Image.new("RGB", (30, 12), (0, 0, 0)), scale=0, margin=0)
    assert out.size == (30, 12)


def test_caps_dimension_to_engine_limit():
    # Windows OCR rejects images past max_image_dimension; scaling must not exceed it.
    out = preprocess_for_ocr(Image.new("RGB", (6000, 100), (0, 0, 0)), scale=4, margin=0)
    assert max(out.size) <= MAX_OCR_DIMENSION


def test_margin_adds_a_quiet_zone_around_the_image():
    # The engine drops glyphs that touch the image edge; a synthetic border restores the
    # margin a tight selection lacks, independent of how much screen was captured.
    out = preprocess_for_ocr(Image.new("RGB", (40, 20), (0, 0, 0)), scale=1, margin=10)
    assert out.size == (60, 40)  # +10px on every side


def test_margin_is_filled_with_the_background_level_not_the_text():
    # Dark surround with a bright blob in the middle: the added border must match the
    # background (stretched to 0), never the text, so we don't fence the text in.
    img = Image.new("L", (20, 20), color=50)
    ImageDraw.Draw(img).rectangle((6, 6, 13, 13), fill=200)
    out = preprocess_for_ocr(img, scale=1, margin=5)
    assert out.size == (30, 30)
    assert out.getpixel((0, 0)) == 0  # autocontrast maps the dark background to 0
