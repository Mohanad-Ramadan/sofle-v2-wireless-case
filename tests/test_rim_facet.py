"""Protected south facet geometry."""
from build123d import GeomType, Solid

from sofle_case import constants as C
from sofle_case.tray import _front_slash_crossings, _rim_facet_frustum, build_tray


def test_south_facet_datums_are_pinned():
    assert C.SOUTH_WALL_EXTRA == 3.0
    assert C.FRONT_FACET_RUN == 6.0
    assert C.FRONT_FACET_DROP == 8.8
    assert C.FRONT_FACET_Y_MASK == 22.0
    east_rim, east_toe, west_rim, west_toe = _front_slash_crossings(C.MAIN_RIM_Z)
    assert east_rim[2] == C.PLATE_TOP_Z
    assert east_toe[2] == C.PLATE_TOP_Z - C.FRONT_FACET_DROP
    assert west_rim[2] == C.PLATE_TOP_Z
    assert west_toe[2] == C.PLATE_TOP_Z - C.FRONT_FACET_DROP
    assert east_rim[0] < east_toe[0]
    assert west_rim[0] > west_toe[0]

    # These are the protected crossings on the straightened thumb/E4 ramp.  Pin
    # the final coordinates as well as the construction helper so a mask retune
    # cannot silently move either crease while preserving its mirrored run.
    expected = (
        (114.841097, 22.0, 15.7),
        (138.417356, 22.0, 6.9),
        (49.261390, 18.109419, 15.7),
        (25.685131, -0.958780, 6.9),
    )
    for actual, target in zip((east_rim, east_toe, west_rim, west_toe), expected):
        assert all(abs(value - wanted) < 1e-4 for value, wanted in zip(actual, target))


def test_south_facet_is_cut_but_floor_remains_closed():
    tray = build_tray()
    x = C.OUTER_WIDTH - 9.0
    assert (tray & Solid.make_box(0.2, 0.2, 0.2).translate(
        (x, C.FRONT_FACET_Y_MASK + 3.0, C.MAIN_RIM_Z - 0.2))).volume < 1e-6
    assert (tray & Solid.make_box(0.2, 0.2, 0.2).translate(
        (x, C.FRONT_FACET_Y_MASK + 3.0,
         C.PLATE_TOP_Z - C.FRONT_FACET_DROP - 1.0))).volume > 0


def test_south_facet_uses_only_exact_planes_and_cones():
    facet = _rim_facet_frustum(C.FRONT_FACET_DROP, C.FRONT_FACET_RUN, C.MAIN_RIM_Z)
    assert len(facet.solids()) == 1
    assert facet.volume > 0.0
    assert all(face.geom_type in (GeomType.PLANE, GeomType.CONE)
               for face in facet.faces())
    assert all(face.area > 1e-6 for face in facet.faces())


def test_south_creases_are_mirrored_and_leave_wall_margin():
    east_rim, east_toe, west_rim, west_toe = _front_slash_crossings()
    east_run = abs(east_toe[0] - east_rim[0])
    west_run = abs(west_rim[0] - west_toe[0])
    assert abs(east_run - west_run) < 1e-6
    assert C.WALL_THICKNESS + C.PCB_XY_CLEARANCE + C.SOUTH_WALL_EXTRA - C.FRONT_FACET_RUN >= 1.5


def test_final_tray_retains_exact_drafted_faces_and_toe():
    tray = build_tray()
    expected_toe = C.MAIN_RIM_Z - C.FRONT_FACET_DROP
    assert len(tray.solids()) == 1
    assert any(abs(vertex.Z - expected_toe) < 1e-5 for vertex in tray.vertices())
    assert all(face.area > 1e-6 for face in tray.faces())
    expected_normal_z = C.FRONT_FACET_RUN / (
        C.FRONT_FACET_RUN**2 + C.FRONT_FACET_DROP**2
    ) ** 0.5
    sloped = []
    for face in tray.faces():
        bounds = face.bounding_box()
        normal = face.normal_at(face.center())
        if abs(bounds.min.Z - expected_toe) > 1e-5 or abs(bounds.max.Z - C.MAIN_RIM_Z) > 1e-5:
            continue
        assert face.geom_type in (GeomType.PLANE, GeomType.CONE)
        if abs(normal.Z - expected_normal_z) < 1e-6:
            sloped.append(face)
    assert len(sloped) == 5, "final tray lost or fragmented a protected south drafted face"


def test_final_mask_boundaries_and_tangent_junctions_are_preserved():
    tray = build_tray()
    east_rim, _east_toe, west_rim, west_toe = _front_slash_crossings()

    # The final boolean must retain each intentional crease endpoint as a vertex.
    for point in (east_rim, _east_toe, west_rim, west_toe):
        assert any(all(abs(getattr(vertex, axis) - value) < 1e-5
                       for axis, value in zip(("X", "Y", "Z"), point))
                   for vertex in tray.vertices())

    # Just south of the east cap and just east of the west slash are deep-cut air;
    # the opposite sides retain the shallower wall. These probes interrogate the
    # final booleaned tray rather than the mask construction helper.
    probe_z = C.MAIN_RIM_Z - C.FRONT_FACET_DROP / 2
    east_x = (east_rim[0] + _east_toe[0]) / 2
    for y, expected in ((C.FRONT_FACET_Y_MASK - 0.2, 0.0),
                        (C.FRONT_FACET_Y_MASK + 0.2, 1.0)):
        probe = Solid.make_box(0.1, 0.1, 0.1).translate(
            (east_x - 0.05, y - 0.05, probe_z - 0.05))
        assert ((tray & probe).volume > 1e-6) is bool(expected)

    y_mid = (west_rim[1] + west_toe[1]) / 2
    west_x = west_toe[0] + (west_rim[0] - west_toe[0]) * (
        (y_mid - west_toe[1]) / (west_rim[1] - west_toe[1]))
    for x, expected in ((west_x - 0.2, 1.0), (west_x + 0.2, 0.0)):
        probe = Solid.make_box(0.1, 0.1, 0.1).translate(
            (x - 0.05, y_mid - 0.05, probe_z - 0.05))
        assert ((tray & probe).volume > 1e-6) is bool(expected)

    # Cone/plane joins along the retained facet are tangent away from the
    # intentional creases. No approximate BSpline or zero-area sliver may enter.
    facet_faces = []
    expected_normal_z = C.FRONT_FACET_RUN / (
        C.FRONT_FACET_RUN**2 + C.FRONT_FACET_DROP**2
    ) ** 0.5
    for face in tray.faces():
        if face.geom_type not in (GeomType.PLANE, GeomType.CONE):
            continue
        center = face.center()
        normal = face.normal_at(center)
        if abs(normal.Z - expected_normal_z) < 1e-6 and 7.0 < center.Y < 23.0:
            facet_faces.append(face)
    for index, face in enumerate(facet_faces):
        for other in facet_faces[index + 1:]:
            for edge in face.edges():
                for shared in other.edges():
                    if not edge.is_same(shared) or shared.length < 1.0:
                        continue
                    normal_a = face.normal_at(shared.center())
                    normal_b = other.normal_at(shared.center())
                    assert (normal_a - normal_b).length < 1e-6
