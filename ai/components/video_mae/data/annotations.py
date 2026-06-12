"""
Temporal annotation loader for UCF-Crime test evaluation.

The annotation file format (one video per line):
    <video_name>  <class>  <start1>  <end1>  <start2>  <end2>
"""

import os


def load_annotations(anno_file: str) -> dict[str, list[tuple[int, int]]]:
    """
    Parse the UCF-Crime temporal annotation text file.

    Returns:
        Mapping from video stem (no extension) to a list of
        (start_frame, end_frame) anomaly segments.
    """
    annotations: dict[str, list[tuple[int, int]]] = {}

    if not os.path.exists(anno_file):
        print(f"WARNING: Annotation file not found at {anno_file}")
        return annotations

    with open(anno_file, "r") as fh:
        for line in fh:
            parts = line.strip().split()
            if len(parts) < 6:
                continue

            name = os.path.splitext(parts[0])[0]

            try:
                s1, e1 = int(parts[2]), int(parts[3])
                s2, e2 = int(parts[4]), int(parts[5])
            except ValueError:
                continue

            segments: list[tuple[int, int]] = []
            if s1 >= 0 and e1 > s1:
                segments.append((s1, e1))
            if s2 >= 0 and e2 > s2:
                segments.append((s2, e2))

            if segments:
                annotations[name] = segments

    print(f"Loaded annotations for {len(annotations)} videos")
    return annotations