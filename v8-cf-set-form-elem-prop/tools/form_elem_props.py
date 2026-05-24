"""Geometric property definitions for ordinary 1C form elements.

Source file: CatalogForm.elem.json
Element entry: data["Страница1/ИмяЭлемента"]["raw"]

Geometry block structure (raw[3]):
    raw[3] = ['8', x, y, w, h, '1',
               anchor_L,   # [6]  left-edge anchor
               anchor_T,   # [7]  top-edge anchor
               anchor_R,   # [8]  right-edge anchor
               anchor_W,   # [9]  width / right-boundary anchor
               anchor_H5,  # [10] height anchor slot 1
               anchor_H6,  # [11] height anchor slot 2
               ...]

Each anchor: ['0', ['2', ref_idx, side, offset], ['2', '-1', '6', '0']]
    ref_idx = '-1'         → inactive (no anchor)
    ref_idx = '0'          → form/page root
    ref_idx = str(elem_idx)→ self-reference (element anchored to itself)
    side    = '0'          → top edge of reference
    side    = '2'          → right edge of reference
    side    = '3'          → right edge of form/page
    side    = '6'          → null side (used with ref='-1')

Verification status of anchor update rules:
    width  — VERIFIED from steps 0040-0043 (Код 384→135, Наименование 384→237)
    height — ref=-1 for both known elements; only scalar updated
    left   — self-ref → anchor_W delta = -delta_x (off = w - x, x changes)
              form-ref → anchor_W delta = +delta_x (off = right - form_right)
    top    — anchor_T self-ref off=19 ≠ absolute y; not updated (scalar only)
"""

# ---------------------------------------------------------------------------
# Index constants in raw[3]
# ---------------------------------------------------------------------------

GEO_IDX_LEFT   = 1   # x coordinate
GEO_IDX_TOP    = 2   # y coordinate
GEO_IDX_WIDTH  = 3   # width in pixels   (VERIFIED)
GEO_IDX_HEIGHT = 4   # height in pixels

GEO_ANCHOR_L   = 6   # left-edge anchor
GEO_ANCHOR_T   = 7   # top-edge anchor
GEO_ANCHOR_R   = 8   # right-edge anchor
GEO_ANCHOR_W   = 9   # width / right-boundary anchor  (VERIFIED with width)
GEO_ANCHOR_H5  = 10  # height anchor slot 1
GEO_ANCHOR_H6  = 11  # height anchor slot 2

REF_NONE = '-1'   # inactive anchor sentinel


# ---------------------------------------------------------------------------
# Alias → canonical property name
# ---------------------------------------------------------------------------

PROP_ALIASES = {
    # canonical (pass-through)
    'width':  'width',
    'height': 'height',
    'left':   'left',
    'top':    'top',
    # short aliases
    'w': 'width',
    'h': 'height',
    'x': 'left',
    'y': 'top',
    # Russian
    'ширина':  'width',
    'высота':  'height',
    'лево':    'left',
    'верх':    'top',
}

# Canonical property metadata (for help / documentation)
PROP_INFO = {
    'width':  {'label_ru': 'Ширина',  'geo_idx': GEO_IDX_WIDTH,  'verified': True},
    'height': {'label_ru': 'Высота',  'geo_idx': GEO_IDX_HEIGHT, 'verified': False},
    'left':   {'label_ru': 'Лево',    'geo_idx': GEO_IDX_LEFT,   'verified': False},
    'top':    {'label_ru': 'Верх',    'geo_idx': GEO_IDX_TOP,    'verified': False},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_prop(name):
    """Return canonical property name for *name*, or None if unknown."""
    return PROP_ALIASES.get(name.lower())


def get_prop(raw, prop):
    """Return current integer value of *prop* for the element described by *raw*.

    *prop* may be a canonical name or any alias.
    Raises ValueError for unknown property names.
    """
    canon = resolve_prop(prop)
    if canon is None:
        raise ValueError('Unknown property %r' % prop)
    return int(raw[3][PROP_INFO[canon]['geo_idx']])


def get_geometry(raw):
    """Return (x, y, w, h) tuple for the element."""
    geo = raw[3]
    return int(geo[GEO_IDX_LEFT]), int(geo[GEO_IDX_TOP]), \
           int(geo[GEO_IDX_WIDTH]), int(geo[GEO_IDX_HEIGHT])


def apply_prop(raw, prop, new_val):
    """Apply a single geometric property change to *raw* in place.

    Returns (old_val, new_val).

    raw    — element's raw array (data[key]["raw"])
    prop   — property name or alias
    new_val — new integer value in pixels

    Modifies raw[3] (geometry block) according to the rules documented in
    this module. Also updates any active anchors whose offsets must change
    to keep the stored layout consistent.
    """
    canon = resolve_prop(prop)
    if canon is None:
        raise ValueError(
            'Unknown property %r. Supported: %s' %
            (prop, ', '.join(PROP_INFO))
        )

    geo = raw[3]
    elem_idx = raw[1]          # element's own index in the form (str)
    geo_idx = PROP_INFO[canon]['geo_idx']

    old_val = int(geo[geo_idx])
    delta = new_val - old_val

    if delta == 0:
        return old_val, new_val

    # Update the scalar value
    geo[geo_idx] = str(new_val)

    # Update anchors based on which property changed
    _ANCHOR_UPDATERS[canon](geo, elem_idx, delta)

    return old_val, new_val


# ---------------------------------------------------------------------------
# Internal anchor-update helpers
# ---------------------------------------------------------------------------

def _anchor_active(anchor):
    return anchor[1][1] != REF_NONE


def _shift_anchor(anchor, delta):
    anchor[1][3] = str(int(anchor[1][3]) + delta)


def _update_width(geo, elem_idx, delta):
    """Width += delta → anchor_W += delta  (VERIFIED)."""
    anc = geo[GEO_ANCHOR_W]
    if _anchor_active(anc):
        _shift_anchor(anc, delta)


def _update_height(geo, elem_idx, delta):
    """Height += delta → anchor_H5/H6 += delta if active (by analogy)."""
    for idx in (GEO_ANCHOR_H5, GEO_ANCHOR_H6):
        anc = geo[idx]
        if _anchor_active(anc):
            _shift_anchor(anc, delta)


def _update_left(geo, elem_idx, delta):
    """Left (x) += delta.

    anchor_L: shift by +delta if active.
    anchor_W: shift depends on anchor type —
        self-ref (ref == elem_idx): off = w - x  →  delta_off = -delta_x
        form-ref (ref == '0'):      off = right - form_right  →  delta_off = +delta_x
        other active ref:           delta_off = +delta_x  (right edge tracks movement)
    """
    anc_l = geo[GEO_ANCHOR_L]
    if _anchor_active(anc_l):
        _shift_anchor(anc_l, delta)

    anc_w = geo[GEO_ANCHOR_W]
    if _anchor_active(anc_w):
        ref = anc_w[1][1]
        if ref == str(elem_idx):
            # Self-reference: off encodes (w - x); moving element changes x,
            # so off decreases by the same delta.
            _shift_anchor(anc_w, -delta)
        else:
            # Form-ref or other: right edge moves with the element.
            _shift_anchor(anc_w, delta)


def _update_top(geo, elem_idx, delta):
    """Top (y) += delta.

    anchor_T for standard manually-placed elements carries a self-reference
    with a fixed offset (e.g. 19) that does NOT encode the absolute y
    position — the same offset appears for elements at different y values.
    Therefore anchor_T is not modified here; only raw[3][2] is updated.
    """
    pass   # anchor_T self-ref off ≠ absolute y; do not touch


_ANCHOR_UPDATERS = {
    'width':  _update_width,
    'height': _update_height,
    'left':   _update_left,
    'top':    _update_top,
}
