def test_slide_switch_bowl_is_a_solid():
    from sofle_case.tray import _slide_switch_bowl
    bowl = _slide_switch_bowl()
    assert bowl.volume > 0, "slide-switch bowl cutter is empty"
