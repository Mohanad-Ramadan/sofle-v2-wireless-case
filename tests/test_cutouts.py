def test_slide_scoop_is_a_solid():
    from sofle_case.case import _slide_scoop
    scoop = _slide_scoop()
    assert scoop.volume > 0, "slide-switch scoop cutter is empty"
    assert len(scoop.solids()) == 1, "slide-switch scoop cutter is not one solid"
