#!/usr/bin/env python3
"""Read-only image checks. Dependency: Pillow. Limits must come from the caller."""
import argparse
import json
from pathlib import Path
from PIL import Image


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('path', type=Path)
    ap.add_argument('--width', type=int)
    ap.add_argument('--height', type=int)
    ap.add_argument('--max-bytes', type=int)
    ap.add_argument('--require-animation', action='store_true')
    ap.add_argument('--require-transparent', action='store_true')
    args = ap.parse_args()
    files = sorted(p for p in args.path.rglob('*') if p.suffix.lower() in {'.png','.jpg','.jpeg','.gif','.webp'}) if args.path.is_dir() else [args.path]
    results = []
    for path in files:
        row = {'file': str(path), 'errors': []}
        try:
            with Image.open(path) as im:
                frames = getattr(im, 'n_frames', 1)
                row.update(width=im.width, height=im.height, format=im.format,
                           bytes=path.stat().st_size, frames=frames, loop=im.info.get('loop'))
                durations, transparency = [], []
                for i in range(frames):
                    im.seek(i)
                    im.load()
                    durations.append(im.info.get('duration', 0))
                    transparency.append(im.convert('RGBA').getchannel('A').getextrema()[0] < 255)
                row.update(duration_ms=sum(durations), transparent_frames=sum(transparency))
                for key in ('width','height'):
                    expected=getattr(args,key)
                    if expected is not None and row[key] != expected:
                        row['errors'].append(f'{key}: expected {expected}, got {row[key]}')
                if args.max_bytes is not None and row['bytes'] > args.max_bytes:
                    row['errors'].append('file exceeds byte limit')
                if args.require_animation and (frames < 2 or row['loop'] != 0 or any(d <= 0 for d in durations)):
                    row['errors'].append('expected multiple timed frames and infinite loop')
                if args.require_transparent and not all(transparency):
                    row['errors'].append('one or more frames have no transparent pixels')
        except Exception as exc:
            row['errors'].append(str(exc))
        results.append(row)
    print(json.dumps({'files': results, 'note': 'Metadata check only; visual inspection still required.'}, ensure_ascii=False, indent=2))
    return 1 if not results or any(r['errors'] for r in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
