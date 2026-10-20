"""PHANTOM of the 0.91" 128x32 I2C OLED over the MCU, plus the AC7 fit report.

Never printed and never fused: it shows what the cover's display window frames. The module is a
plain slab over ``C.oled_module_xy`` whose TOP is the user-measured ``C.oled_top_z`` (datum: the
main PCB's bottom face); ``OLED_PHANTOM_THK`` is display only, so the module's underside is not
modelled and every module-bottom clearance is reported as UNCHECKED.

J3's palindromic header puts CS at opposite ends on the two halves, so the 4-pin module seats one
pad further east (canonical) on the flipped half: the halves are not mirror images. Geometry is
canonical (right-hand, pre-mirror) like every other phantom; the CLI mirrors the left one.
"""
from __future__ import annotations

from typing import cast

from build123d import Part, Solid

from . import constants as C
from . import mcu_encoder_cover as Cover
from . import tray as Tray


def build_oled_phantom(side: str, oled: C.OledMode) -> Part:
    """The module slab, canonical frame; ``oled`` must be ``long`` or ``short``."""
    x0, x1, y0, y1 = C.oled_module_xy(side)
    top = C.oled_top_z(oled)
    slab = Solid.make_box(x1 - x0, y1 - y0, C.OLED_PHANTOM_THK).translate(
        (x0, y0, top - C.OLED_PHANTOM_THK))
    part = cast(Part, Part(children=[slab]))
    part.label = "oled"
    return part


def _phys_x(side: str, x: float) -> float:
    return C.OUTER_WIDTH - x if side == "left" else x


def _phys_span(side: str, x0: float, x1: float) -> tuple[float, float]:
    a, b = _phys_x(side, x0), _phys_x(side, x1)
    return min(a, b), max(a, b)


def _span(a: tuple[float, float]) -> str:
    return f"{a[0]:.3f}..{a[1]:.3f}"


def oled_fit_report(side: str, oled: C.OledMode) -> str:
    """Plan §4 AC7 report. All X in the physical (assembled, post-mirror) frame, mm, %.3f."""
    if oled == "none":
        raise ValueError("the OLED fit report needs oled 'long' or 'short'")
    p = Cover.profile(cast(Cover.Side, side), oled)
    assert p.module_xy is not None and p.window_xy is not None
    mx0, mx1, my0, my1 = p.module_xy
    wx0, wx1, wy0, wy1 = p.window_xy
    top = C.oled_top_z(oled)
    nets = C.j3_nets(side)
    pads = C.oled_pads(side)
    pad_x = " ".join(f"{_phys_x(side, C.pcb_to_case(*xy)[0]):.3f}" for xy in C.J3_PADS_PCB)
    mcu_top = C.mcu_pcb_top_z(oled)
    tail_top = mcu_top + C.MCU_HEADER_TAIL_H
    mcu_x = C.pcb_to_case(*C.MCU_POS)[0]
    tray_north = Tray.outline(oled).north_run(mcu_x) + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    roof_under = p.ridge - C.COVER_TOP_THICKNESS

    jack_face = C.MCU_BODY_N_Y + C.USB_JACK_Y_PROTRUDE
    none_north = Cover.profile(p.side, "none").north_y
    notch_lo = C.usb_port_z(side, oled)[0]
    if notch_lo < C.MAIN_RIM_Z:
        notch = f"{notch_lo:.3f}..{C.MAIN_RIM_Z:.3f} (open-top slot to the rim)"
        # The rim facet slopes the outer face from the cover line at the rim out to the full
        # wall RIM_FACET_DROP lower, so the slot's depth grows down the port band.
        def outer_y(z: float) -> float:
            return min(tray_north, p.north_y + C.RIM_FACET_RUN * (C.MAIN_RIM_Z - z)
                       / C.RIM_FACET_DROP)
        tray_inner = C.TRAY_NORTH_LOW_Y + C.PCB_XY_CLEARANCE
        jack_lo = C.usb_jack_z(side, oled)[0]
        depth = (f"{outer_y(C.MAIN_RIM_Z) - tray_inner:.3f}..{outer_y(notch_lo) - tray_inner:.3f}"
                 f" (tray outer face to jack face {outer_y(jack_lo) - jack_face:.3f}"
                 f" at jack bottom z {jack_lo:.3f})")
    else:
        notch = "none"
        depth = "n/a (port above the rim)"

    lines = [
        f"OLED fit report: side={side} mode={oled} (physical frame, mm)",
        f"  height datum (PCB bottom Z): {C.PCB_SEAT_Z:.3f}",
        f"  J3 pad x: {pad_x}",
        (f"  chosen pads: {','.join(str(i) for i in pads)} "
         f"(nets {' '.join(nets[i] for i in pads)})"),
        (f"  module x: {_span(_phys_span(side, mx0, mx1))}  y: {my0:.3f}..{my1:.3f}"
         f"  top z: {top:.3f}"),
        f"  window x: {_span(_phys_span(side, wx0, wx1))}  y: {wy0:.3f}..{wy1:.3f}",
        f"  window minY - MCU minY: {wy0 - C.MCU_BODY_S_Y:.3f}   (MCU minY {C.MCU_BODY_S_Y:.3f})",
        f"  MCU board top z: {mcu_top:.3f}   header-tail top z: {tail_top:.3f}",
        (f"  USB jack z: {_span(C.usb_jack_z(side, oled))}"
         f"   cover USB port z: {_span(p.usb_port_z)}"),
        f"  tray USB notch z: {notch}",
        (f"  ridge z: {p.ridge:.3f}   ramp top y: {p.ramp_top_y:.3f}"
         f"   roof clearance over module: {roof_under - top:.3f}"),
        (f"  cover north y: {p.north_y:.3f}   tray outer north y: {tray_north:.3f}"
         f"   north wall extra: {C.north_wall_extra(oled)[14]:.3f}"),
        "  module bottom vs jack/header-tail: UNCHECKED (measured top Z is authoritative)",
        (f"  WARNING plug reach: cover face to jack face {p.north_y - jack_face:.3f}"
         f" (none: {none_north - jack_face:.3f}); tray wall depth at port {depth}"),
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    from ocp_vscode import show
    print(oled_fit_report("right", "long"))
    show(build_oled_phantom("right", "long"), names=["oled"])
