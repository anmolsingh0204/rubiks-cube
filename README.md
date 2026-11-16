# 3D Rubik's Cube Generator

A Python tool to generate interactive 3D Rubik's cubes of any size (N×N×N) with multiple export formats.

## Features

| Feature | Description |
|---------|-------------|
| **N×N×N cubes** | 2×2×2 (Pocket Cube) through 7×7×7 and beyond |
| **Standard view** | Only exterior faces colored (solved state) |
| **Exploded view** | All 6 faces of every cubie visible, separated |
| **Interactive HTML** | Rotate, zoom, pan in browser (Plotly) |
| **Static PNG** | High-res images (requires Chrome) |
| **STL export** | 3D-printable, colored meshes (requires `trimesh`) |
| **OBJ export** | Universal 3D format with material groups |
| **Solver framework** | `CubeState` class for future animation/solving |

## Quick Start

```bash
cd /home/dell/rubiks-cube

# Create virtual environment (one-time)
python3 -m venv .venv
.venv/bin/pip install plotly kaleido numpy trimesh

# Generate a standard 3×3×3
.venv/bin/python rubiks_cube.py --size 3 --html --stl --obj

# Generate 4×4×4 exploded view
.venv/bin/python rubiks_cube.py --size 4 --exploded --html --stl --obj

# Generate 2×2×2 (Pocket Cube)
.venv/bin/python rubiks_cube.py --size 2 --html
```

## Command Reference

```bash
.venv/bin/python rubiks_cube.py [OPTIONS]

Options:
  -s, --size N           Cube size N×N×N (default: 3, min: 2)
  -e, --exploded         Exploded view (all faces visible)
  --explode-factor F     Separation distance (default: 1.5)
  --html / --no-html     Export interactive HTML (default: on)
  --png                  Export static PNG (needs Chrome)
  --stl                  Export STL for 3D printing (needs trimesh)
  --obj                  Export OBJ (no extra deps)
  -o, --output DIR       Output directory (default: ./output)
  --title TEXT           Custom title for HTML
  -h, --help             Show help
```

## Output Files

```
output/
├── rubiks_2x2x2.html          # Interactive 2×2×2
├── rubiks_2x2x2.obj           # OBJ format
├── rubiks_3x3x3.html          # Interactive 3×3×3
├── rubiks_3x3x3.stl           # 3D printable STL
├── rubiks_3x3x3.obj           # OBJ format
├── rubiks_4x4x4_exploded.html # Interactive 4×4×4 exploded
├── rubiks_4x4x4_exploded.stl  # 3D printable exploded
├── rubiks_4x4x4_exploded.obj  # OBJ format
└── rubiks_5x5x5.html          # Interactive 5×5×5
    ...
```

## Viewing the HTML

**Option 1: Direct file**
```bash
# Linux/WSL
xdg-open output/rubiks_3x3x3.html

# macOS
open output/rubiks_3x3x3.html

# Windows
start output/rubiks_3x3x3.html
```

**Option 2: Local server (recommended for WSL2)**
```bash
.venv/bin/python -m http.server -d output 8080
# Open http://localhost:8080/rubiks_3x3x3.html
```

**Controls:**
- **Left drag** — Rotate
- **Right drag** — Pan
- **Scroll** — Zoom
- **Double-click** — Reset view

## 3D Printing (STL)

The STL export creates a multi-color mesh suitable for:
- **Multi-material printers** (Bambu Lab AMS, Prusa MMU, etc.)
- **Single-material + painting** (each face is a separate mesh group)
- **Resin printing** (hollow with drainage holes recommended)

```bash
# Standard cube (only exterior faces)
.venv/bin/python rubiks_cube.py --size 3 --stl

# Exploded view (all faces printable separately)
.venv/bin/python rubiks_cube.py --size 3 --exploded --stl
```

## Color Scheme (Standard)

| Face | Color | Hex | RGB |
|------|-------|-----|-----|
| **U** (Up) | White | `#FFFFFF` | (255, 255, 255) |
| **D** (Down) | Yellow | `#FFD500` | (255, 213, 0) |
| **F** (Front) | Red | `#C41E3A` | (196, 30, 58) |
| **B** (Back) | Orange | `#FF5800` | (255, 88, 0) |
| **R** (Right) | Green | `#009B48` | (0, 155, 72) |
| **L** (Left) | Blue | `#0046AD` | (0, 70, 173) |

## Solver Animation (Framework)

The `CubeState` class in `rubiks_cube.py` provides a foundation for:
- Representing cube state (facelet colors)
- Applying moves (R, U, F, etc.)
- Scrambling
- Converting to visualization colors

```python
from rubiks_cube import CubeState

cube = CubeState(3)
cube.scramble(20)
# TODO: Animate solution steps
```

## Requirements

- Python 3.10+
- `plotly` — interactive 3D
- `kaleido` — static PNG export
- `numpy` — numerical operations
- `trimesh` — STL export (optional)

## License

MIT — Use freely for any purpose.