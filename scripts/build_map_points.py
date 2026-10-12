"""Build a small nzsegment-to-map-point lookup from the NIWA shape files."""

import argparse
import csv
from pathlib import Path

import fiona
from shapely.geometry import shape


def write_points(writer, path: Path, kind: str) -> int:
    count = 0
    with fiona.open(path) as features:
        if features.crs.to_epsg() != 4326:
            raise ValueError(f"Expected WGS84 coordinates in {path}, got {features.crs}")
        for feature in features:
            geometry = feature["geometry"]
            if geometry is None:
                continue
            point = shape(geometry).representative_point()
            if point.is_empty:
                continue
            writer.writerow(
                (kind, feature["properties"]["nzsegment"], round(point.y, 6), round(point.x, 6))
            )
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shapes-dir", type=Path, default=Path("InputShapes"))
    parser.add_argument("--output", type=Path, default=Path("InputData/NzsegmentMapPoints.csv"))
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(("kind", "nzsegment", "lat", "lng"))
        stream_count = write_points(writer, args.shapes_dir / "SubCatchWGS84.shp", "stream")
        coastal_count = write_points(writer, args.shapes_dir / "TerminalsWGS84.shp", "coastal")

    print(f"Wrote {stream_count:,} stream and {coastal_count:,} coastal map points to {args.output}")


if __name__ == "__main__":
    main()
