"""BRep and exported-mesh manifold checks for the monolithic case."""
from __future__ import annotations

import struct
from pathlib import Path

import pytest
from build123d import Part, export_stl

from tests.shared_builds import build_case_half


def _read_stl_triangles(path: Path) -> list[tuple[tuple[float, float, float], ...]]:
    """Read binary STL (or simple ASCII STL) without a mesh dependency."""
    data = path.read_bytes()
    if len(data) >= 84:
        triangle_count = struct.unpack_from("<I", data, 80)[0]
        expected_size = 84 + 50 * triangle_count
        if expected_size == len(data):
            triangles = []
            for index in range(triangle_count):
                record = 84 + 50 * index
                triangles.append(tuple(
                    struct.unpack_from("<3f", data, record + 12 + 12 * vertex)
                    for vertex in range(3)
                ))
            return triangles

    # The project exporter currently emits binary STL. Keeping this small fallback
    # makes the topology assertion independent of that representation detail.
    vertices = []
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path} is not a complete STL") from exc
    for line in text.splitlines():
        fields = line.strip().split()
        if len(fields) == 4 and fields[0].lower() == "vertex":
            vertices.append(tuple(float(value) for value in fields[1:]))
    if not vertices or len(vertices) % 3:
        raise ValueError(f"{path} contains no complete STL triangles")
    return [tuple(vertices[index:index + 3]) for index in range(0, len(vertices), 3)]


def _mesh_topology(triangles: list[tuple[tuple[float, float, float], ...]]):
    """Return undirected edge multiplicities and connected triangle components."""
    if not triangles:
        raise AssertionError("STL contains no triangles")

    # STL stores each shared vertex more than once. Quantization merges only the
    # export's float-rounding noise, while remaining far below any design feature.
    quantum = 1e-5

    def vertex_key(vertex):
        return tuple(round(coordinate / quantum) for coordinate in vertex)

    parent = list(range(len(triangles)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first, second):
        first, second = find(first), find(second)
        if first != second:
            parent[second] = first

    edge_counts = {}
    edge_owner = {}
    for triangle_index, triangle in enumerate(triangles):
        vertices = tuple(vertex_key(vertex) for vertex in triangle)
        assert len(set(vertices)) == 3, "STL contains a degenerate triangle"
        for first, second in zip(vertices, vertices[1:] + vertices[:1]):
            edge = tuple(sorted((first, second)))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
            if edge in edge_owner:
                union(triangle_index, edge_owner[edge])
            else:
                edge_owner[edge] = triangle_index
    return edge_counts, {find(index) for index in range(len(triangles))}


def test_left_is_valid():
    p = build_case_half("left")
    assert p.is_valid, "left half failed BRepCheck"


def test_right_is_valid():
    p = build_case_half("right")
    assert p.is_valid, "right half failed BRepCheck"


@pytest.mark.parametrize("side", ["left", "right"])
def test_exported_stl_is_nonempty_watertight_and_connected(tmp_path: Path, side: str):
    """The delivered mesh has two incident facets per edge and one body."""
    case = build_case_half(side)
    assert isinstance(case, Part)
    stl = tmp_path / f"sofle_case_{side}.stl"
    export_stl(case, str(stl), tolerance=1e-3, angular_tolerance=0.05)

    assert stl.is_file()
    assert stl.stat().st_size > 1000
    triangles = _read_stl_triangles(stl)
    edge_counts, components = _mesh_topology(triangles)
    assert all(count == 2 for count in edge_counts.values()), (
        "exported STL has an open, duplicated, or non-manifold edge"
    )
    assert len(components) == 1, "exported STL contains multiple disconnected bodies"
