"""Parse JLCPCB CPL (pick-and-place) CSV → JSON keyed by designator."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import click


def parse_cpl(csv_path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        # Build a lower-cased fieldname map so we tolerate minor header variants.
        fmap = {k.strip().lower(): k for k in reader.fieldnames or []}

        def col(*names: str) -> str:
            for n in names:
                if n in fmap:
                    return fmap[n]
            raise KeyError(f"none of {names} present in {list(fmap)}")

        c_des = col("designator")
        c_x   = col("mid x", "midx", "x")
        c_y   = col("mid y", "midy", "y")
        c_lay = col("layer")
        c_rot = col("rotation")

        for row in reader:
            des = row[c_des].strip()
            try:
                out[des] = {
                    "x": float(row[c_x]),
                    "y": float(row[c_y]),
                    "layer": row[c_lay].strip().lower(),
                    "rotation": float(row[c_rot]),
                }
            except ValueError:
                continue  # skip malformed rows
    return out


@click.command()
@click.argument("csv_path", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "out_dir", type=click.Path(path_type=Path),
              default=Path("data"), show_default=True)
def main(csv_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = parse_cpl(csv_path)
    (out_dir / "components.json").write_text(json.dumps(data, indent=2, sort_keys=True))
    click.echo(f"components: {len(data)}")


if __name__ == "__main__":
    main()
