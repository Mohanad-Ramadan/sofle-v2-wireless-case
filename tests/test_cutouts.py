from build123d import Part


def test_neg_x_wall_cutter_plus_y_returns_part():
    from sofle_case.tray import _neg_x_wall_cutter_plus_y
    assert isinstance(_neg_x_wall_cutter_plus_y(), Part)


def test_neg_x_wall_cutter_minus_y_returns_part():
    from sofle_case.tray import _neg_x_wall_cutter_minus_y
    assert isinstance(_neg_x_wall_cutter_minus_y(), Part)
