def test_slide_switch_slot_is_a_solid():
    from sofle_case.tray import _slide_switch_slot
    slot = _slide_switch_slot()
    assert slot.volume > 0, "slide-switch slot cutter is empty"
