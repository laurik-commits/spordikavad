"""Mängu OG-pilt (jagamise eelvaade): 1200×630 PNG, tekstipõhine, ühtne kujundus, ilma logodeta.

Pealkiri (mäng), aeg, koht ja liiga värvilise ala märgi kõrval. Kasutab Pillow'd ja kaasaantud DejaVu fonti
(site/fonts, vaba litsents). Kui Pillow või font puudub, annab `render` None ja leht kasutab üldist og.png-d:
ehitus ei tohi pildi pärast katki minna.
"""

from __future__ import annotations

import functools
import io
import logging
from pathlib import Path

log = logging.getLogger("ogimage")

FONTS = Path(__file__).resolve().parent / "site" / "fonts"
W, H = 1200, 630
BG = (20, 69, 122)          # lehe päise sinine (#14457a)
FG = (255, 255, 255)
SOFT = (200, 218, 240)      # teisene tekst: valgel sinisel kontrast ≥ 7:1
MARGIN = 72
MAX_LINES = 3
TITLE_TOP, TITLE_HEIGHT = 150, 250     # pealkirja ala: 3 rida mahub alati ja jätab ruumi alumisele plokile
DETAIL_TOP = 436


@functools.lru_cache(maxsize=None)   # sama suurusega font laetakse ühe korra (sadu pilte ühes ehituses)
def _load(path: str, size: int):
    from PIL import ImageFont
    return ImageFont.truetype(path, size)


def _fonts():
    bold, regular = FONTS / "DejaVuSans-Bold.ttf", FONTS / "DejaVuSans.ttf"
    if not (bold.exists() and regular.exists()):
        raise FileNotFoundError(f"font puudub kaustas {FONTS}")
    return (lambda size: _load(str(bold), size)), (lambda size: _load(str(regular), size))


def _wrap(draw, text: str, font, width: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _fit(draw, text: str, bold, width: int) -> tuple[list[str], int]:
    """Suurim kirjasuurus (84 → 44), mille juures pealkiri mahub kuni 3 reale ja ette nähtud kõrgusse;
    muidu lõigatakse kolmas rida."""
    for size in range(84, 43, -4):
        font = bold(size)
        lines = _wrap(draw, text, font, width)
        if (len(lines) <= MAX_LINES and all(draw.textlength(x, font=font) <= width for x in lines)
                and len(lines) * size * 1.18 <= TITLE_HEIGHT):
            return lines, size
    font = bold(44)
    lines = _wrap(draw, text, font, width)[:MAX_LINES]
    while draw.textlength(lines[-1] + "…", font=font) > width and len(lines[-1]) > 1:
        lines[-1] = lines[-1][:-1].rstrip()
    lines[-1] += "…"
    return lines, 44


def render(title: str, when: str, place: str, league: str, sport: str, color: str) -> bytes | None:
    """PNG baiti või None (Pillow/font puudub). `color` = ala värv „#rrggbb“."""
    try:
        from PIL import Image, ImageDraw
        bold, regular = _fonts()
    except Exception as exc:  # noqa: BLE001 - pilt on mugavus, mitte kohustus
        log.warning("OG-pilti ei tehta (%s: %s), kasutan üldist pilti", type(exc).__name__, exc)
        return None
    rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 28, H], fill=rgb)                                  # ala värvi riba vasakul
    # ülaosa: ala märk ja leht
    chip_font = bold(34)
    chip_w = int(d.textlength(sport.upper(), font=chip_font)) + 44
    d.rounded_rectangle([MARGIN, 56, MARGIN + chip_w, 56 + 58], radius=29, fill=rgb)
    d.text((MARGIN + 22, 56 + 29), sport.upper(), font=chip_font, fill=FG, anchor="lm")
    d.text((W - MARGIN, 56 + 29), "Elan kaasa", font=bold(34), fill=SOFT, anchor="rm")
    # pealkiri
    lines, size = _fit(d, title, bold, W - 2 * MARGIN)
    font = bold(size)
    y = TITLE_TOP
    for line in lines:
        d.text((MARGIN, y), line, font=font, fill=FG)
        y += int(size * 1.18)
    # aeg, koht, liiga all
    small = regular(38)
    y = DETAIL_TOP
    for text, f, fill in ((when, bold(40), FG), (place, small, SOFT), (league, small, SOFT)):
        if text:
            d.text((MARGIN, y), _clip(d, text, f, W - 2 * MARGIN), font=f, fill=fill)
            y += 54
    d.text((W - MARGIN, H - 44), "elakaasa.ee", font=regular(30), fill=SOFT, anchor="rm")
    buf = io.BytesIO()
    # värvipalett: tekst ja sile taust, pilt on ~3× väiksem. Palett tehakse ala värvi kohta üks kord (iga pildi
    # oma paletiarvutus oleks ehituse kõige aeglasem samm)
    img.quantize(palette=_palette(color, img), dither=Image.Dither.NONE).save(buf, "PNG")
    return buf.getvalue()


_PALETTES: dict[str, object] = {}


def _palette(color: str, img):
    """Ala värvi palett: esimesest sama värvi pildist (taust, valge, teisene tekst, ala värv ja nende vahetoonid)."""
    from PIL import Image
    if color not in _PALETTES:
        _PALETTES[color] = img.quantize(colors=32, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    return _PALETTES[color]


def _clip(draw, text: str, font, width: int) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + "…", font=font) > width:
        text = text[:-1]
    return text.rstrip() + "…"
