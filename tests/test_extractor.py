import pytest

import extractor


def test_read_image_uses_rotation_and_keeps_higher_confidence_text(monkeypatch):
    source_image = object()

    class FakeReader:
        def readtext(self, image, **options):
            if image == b"original":
                assert "rotation_info" not in options
                return [
                    ([[0, 20], [100, 20], [100, 40], [0, 40]], "Mango Juice", 0.8)
                ]
            assert options["rotation_info"] == [90, 270]
            return [
                ([[0, 20], [100, 20], [100, 40], [0, 40]], "Mango Juice 1L", 0.95)
            ]

    monkeypatch.setattr(extractor, "_get_reader", lambda: FakeReader())
    monkeypatch.setattr(
        extractor,
        "_prepare_image",
        lambda image: ["original", "enhanced"] if image is source_image else [],
    )
    monkeypatch.setattr(extractor, "_encode_image", lambda image: image.encode())

    assert extractor._read_image(source_image) == "Mango Juice 1L"


def test_read_image_skips_fallback_for_confident_text(monkeypatch):
    source_image = object()
    calls = []

    class FastReader:
        def readtext(self, image, **options):
            calls.append(options)
            return [
                ([[0, 20], [200, 20], [200, 40], [0, 40]], "Fresh Mango Juice 1L", 0.95)
            ]

    monkeypatch.setattr(extractor, "_get_reader", lambda: FastReader())
    monkeypatch.setattr(
        extractor,
        "_prepare_image",
        lambda image: ["original", "enhanced"] if image is source_image else [],
    )
    monkeypatch.setattr(extractor, "_encode_image", lambda image: image.encode())

    assert extractor._read_image(source_image) == "Fresh Mango Juice 1L"
    assert len(calls) == 1


def test_photo_without_detected_text_has_actionable_error(monkeypatch):
    source_image = object()

    def return_empty_text(image):
        assert image is source_image
        return ""

    monkeypatch.setattr(extractor, "_read_image", return_empty_text)

    with pytest.raises(ValueError, match="sharper, brighter, straight-on photo"):
        extractor._extract_image_text(source_image)


def test_extractor_rejects_unsupported_image_file():
    with pytest.raises(ValueError, match="Unsupported file format"):
        extractor.extract_text_from_file("vendor_menu.gif")
