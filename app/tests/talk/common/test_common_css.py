from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from reportlab.pdfbase.ttfonts import TTFontFile

from eventyay.common.text.css import validate_css


@pytest.fixture
def valid_css():
    return """
body {
  background-color: #000;
  display: none;
}
.some-descriptor {
  /* Dotted borders are IN! */
  border-style: dotted dashed solid double;  /* more commenting */
  BORDER-color: red green blue yellow;
  object-fit: cover;
}
#best-descriptor {
  border: 5px solid red;
}
@media print {
  #best-descriptor {
    border: 5px solid blue;
  }
}
"""


@pytest.fixture
def invalid_css(valid_css):
    return (
        valid_css
        + """
a.other-descriptor {
    content: url("https://malicious.site.com");
}
"""
    )


def test_valid_css(valid_css):
    assert validate_css(valid_css) == valid_css


def test_invalid_css(invalid_css):
    with pytest.raises(ValidationError):
        validate_css(invalid_css)


def test_open_sans_font_assets_exist_and_contain_eastern_european_glyphs():
    fonts_dir = Path(__file__).resolve().parents[3] / 'eventyay' / 'static' / 'fonts'
    font_files = [
        'OpenSans-Regular.ttf',
        'OpenSans-Bold.ttf',
        'OpenSans-Italic.ttf',
        'OpenSans-BoldItalic.ttf',
    ]
    # Central/Eastern European characters:
    # Ą, ą, Č, č, Ę, ę, Ł, ł, Ń, ń, Š, š, Ž, ž
    required_codepoints = [
        0x0104,
        0x0105,
        0x010C,
        0x010D,
        0x0118,
        0x0119,
        0x0141,
        0x0142,
        0x0143,
        0x0144,
        0x0160,
        0x0161,
        0x017D,
        0x017E,
    ]

    for fname in font_files:
        font_path = fonts_dir / fname
        assert font_path.is_file(), f'Font file {font_path} does not exist'
        ttfont = TTFontFile(str(font_path))
        assert ttfont.numGlyphs > 500, f'{fname} has only {ttfont.numGlyphs} glyphs'
        for cp in required_codepoints:
            assert cp in ttfont.charToGlyph, f'Character U+{cp:04X} ({chr(cp)}) missing in {fname}'


def test_open_sans_css_declarations():
    static_dir = Path(__file__).resolve().parents[3] / 'eventyay' / 'static'
    open_sans_css = (static_dir / 'common' / 'css' / 'open_sans.css').read_text(encoding='utf-8')
    fonts_css = (static_dir / 'common' / 'css' / '_fonts.css').read_text(encoding='utf-8')

    for content, filename in [(open_sans_css, 'open_sans.css'), (fonts_css, '_fonts.css')]:
        assert 'opensans_regular_macroman' not in content, f'{filename} still references macroman subset'
        assert 'opensans_bold_macroman' not in content, f'{filename} still references macroman subset'
        assert '../../fonts/OpenSans-Regular.ttf' in content
        assert '../../fonts/OpenSans-Bold.ttf' in content
        assert '../../fonts/OpenSans-Italic.ttf' in content
        assert '../../fonts/OpenSans-BoldItalic.ttf' in content
        assert 'font-display: swap' in content


def test_open_sans_stylesheet_included_in_templates():
    eventyay_dir = Path(__file__).resolve().parents[3] / 'eventyay'
    templates = [
        eventyay_dir / 'presale' / 'templates' / 'pretixpresale' / 'base.html',
        eventyay_dir / 'control' / 'templates' / 'pretixcontrol' / 'base.html',
        eventyay_dir / 'eventyay_common' / 'templates' / 'eventyay_common' / 'base.html',
    ]

    for tpl in templates:
        assert tpl.is_file(), f'Template {tpl} does not exist'
        content = tpl.read_text(encoding='utf-8')
        assert 'common/css/open_sans.css' in content, f'open_sans.css not included in {tpl.name}'
