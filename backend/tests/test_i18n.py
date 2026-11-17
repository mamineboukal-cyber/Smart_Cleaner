import pytest

from app.i18n import MESSAGES, t, ui_labels


def test_t_formats_placeholders():
    MESSAGES["test.key"] = "Skewness {skew} > 1"
    assert t("test.key", skew=2.5) == "Skewness 2.5 > 1"


def test_missing_key_raises():
    with pytest.raises(KeyError):
        t("does.not.exist")


def test_ui_labels_only_ui_keys():
    labels = ui_labels()
    assert labels and all(k.startswith("ui.") for k in labels)
