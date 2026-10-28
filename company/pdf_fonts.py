import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_font_registered = False
_ufont = "Helvetica"
_ufont_bold = "Helvetica-Bold"


def _register_fonts():
    global _font_registered, _ufont, _ufont_bold
    if _font_registered:
        return
    _font_registered = True

    segoe = r"C:\Windows\Fonts\segoeui.ttf"
    segoe_bold = r"C:\Windows\Fonts\segoeuib.ttf"

    deja = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "DejaVuSans.ttf")
    deja_bold = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "DejaVuSans-Bold.ttf")

    try:
        if os.path.exists(segoe):
            pdfmetrics.registerFont(TTFont("SegoeUI", segoe))
            _ufont = "SegoeUI"
        elif os.path.exists(deja):
            pdfmetrics.registerFont(TTFont("SegoeUI", deja))
            _ufont = "SegoeUI"

        if os.path.exists(segoe_bold):
            pdfmetrics.registerFont(TTFont("SegoeUIBold", segoe_bold))
            _ufont_bold = "SegoeUIBold"
        elif os.path.exists(deja_bold):
            pdfmetrics.registerFont(TTFont("SegoeUIBold", deja_bold))
            _ufont_bold = "SegoeUIBold"
    except Exception:
        pass


def get_unicode_font():
    _register_fonts()
    return _ufont


def get_unicode_font_bold():
    _register_fonts()
    return _ufont_bold
