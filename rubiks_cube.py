#!/usr/bin/env python3
"""
3D Rubik's Cube Visualization & Export Tool.

Features:
- N×N×N cubes (2×2, 3×3, 4×4, 5×5, etc.)
- Standard or exploded/cutaway views
- Interactive HTML (Plotly) + static PNG
- 3D-printable STL/OBJ export
- Solver animation framework (for future use)

Usage:
    python rubiks_cube.py --size 3              # Standard 3×3×3
    python rubiks_cube.py --size 4 --exploded   # 4×4×4 exploded view
    python rubiks_cube.py --size 3 --stl        # Export STL for 3D printing
    python rubiks_cube.py --size 2 --png        # 2×2×2 with PNG export
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import plotly.graph_objects as go

# Optional: for STL export
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False


# ─── Standard Rubik's Color Scheme ──────────────────────────────────────────
# U=Up (White), D=Down (Yellow), F=Front (Red), B=Back (Orange), R=Right (Green), L=Left (Blue)
FACE_COLORS = {
    'U': '#FFFFFF',  # White
    'D': '#FFD500',  # Yellow
    'F': '#C41E3A',  # Red
    'B': '#FF5800',  # Orange
    'R': '#009B48',  # Green
    'L': '#0046AD',  # Blue
}

# For STL export: RGB tuples (0-255)
FACE_COLORS_RGB = {
    'U': (255, 255, 255),
    'D': (255, 213, 0),
    'F': (196, 30, 58),
    'B': (255, 88, 0),
    'R': (0, 155, 72),
    'L': (0, 70, 173),
}

# Darker edge colors for cubie boundaries
EDGE_COLORS = {
    'U': '#CCCCCC',
    'D': '#CCAA00',
    'F': '#99182E',
    'B': '#CC4600',
    'R': '#007B3A',
    'L': '#00388A',
}

FACE_NORMALS = {
    'U': (0, 1, 0),   # +Y
    'D': (0, -1, 0),  # -Y
    'F': (0, 0, 1),   # +Z
    'B': (0, 0, -1),  # -Z
    'R': (1, 0, 0),   # +X
    'L': (-1, 0, 0),  # -X
}

CUBE_SIZE = 1.0
GAP = 0.05  # Increased gap for visible cubie separation
CUBIE_SIZE = CUBE_SIZE - GAP


# ─── Geometry Generation ────────────────────────────────────────────────────

def create_cubie_mesh(center_x, center_y, center_z, size, face_colors, show_edges=True):
    """Create mesh for a single cubie with faces and optional edge lines."""
    half = size / 2
    cx, cy, cz = center_x, center_y, center_z

    vertices = np.array([
        [cx - half, cy - half, cz - half],  # 0: bottom-left-back
        [cx + half, cy - half, cz - half],  # 1: bottom-right-back
        [cx + half, cy + half, cz - half],  # 2: top-right-back
        [cx - half, cy + half, cz - half],  # 3: top-left-back
        [cx - half, cy - half, cz + half],  # 4: bottom-left-front
        [cx + half, cy - half, cz + half],  # 5: bottom-right-front
        [cx + half, cy + half, cz + half],  # 6: top-right-front
        [cx - half, cy + half, cz + half],  # 7: top-left-front
    ], dtype=np.float32)

    # 6 faces, each as 2 triangles (12 triangles total)
    faces = [
        # Back face (-Z)
        [0, 1, 2], [0, 2, 3],
        # Front face (+Z)
        [4, 7, 6], [4, 6, 5],
        # Bottom face (-Y)
        [0, 4, 5], [0, 5, 1],
        # Top face (+Y)
        [3, 2, 6], [3, 6, 7],
        # Left face (-X)
        [0, 3, 7], [0, 7, 4],
        # Right face (+X)
        [1, 5, 6], [1, 6, 2],
    ]
    face_indices = ['B', 'F', 'D', 'U', 'L', 'R']

    mesh_vertices = []
    mesh_faces = []
    face_colors_list = []

    for i, (tri1, tri2) in enumerate(zip(faces[::2], faces[1::2])):
        face_name = face_indices[i]
        if face_name in face_colors:
            color = face_colors[face_name]
            for tri in (tri1, tri2):
                mesh_faces.append([len(mesh_vertices) + j for j in range(3)])
                mesh_vertices.extend(vertices[tri])
                face_colors_list.extend([color] * 3)

    # Create edge lines for cubie boundaries
    edge_data = None
    if show_edges:
        # 12 edges of a cube
        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # back face
            [4, 5], [5, 6], [6, 7], [7, 4],  # front face
            [0, 4], [1, 5], [2, 6], [3, 7],  # connecting edges
        ]
        edge_x, edge_y, edge_z = [], [], []
        for e in edges:
            edge_x.extend([vertices[e[0], 0], vertices[e[1], 0], None])
            edge_y.extend([vertices[e[0], 1], vertices[e[1], 1], None])
            edge_z.extend([vertices[e[0], 2], vertices[e[1], 2], None])
        edge_data = (np.array(edge_x), np.array(edge_y), np.array(edge_z))

    return (np.array(mesh_vertices, dtype=np.float32),
            np.array(mesh_faces, dtype=np.int32),
            face_colors_list,
            edge_data)


def get_exterior_faces(x, y, z, n, exploded=False, explode_factor=1.5):
    """
    Determine exterior faces for a cubie at (x,y,z).
    If exploded, all 6 faces get colors (for visualization).
    """
    faces = {}
    is_exterior = {
        'L': (x == 0),
        'R': (x == n - 1),
        'D': (y == 0),
        'U': (y == n - 1),
        'B': (z == 0),
        'F': (z == n - 1),
    }

    for face_name, is_ext in is_exterior.items():
        if is_ext or exploded:
            faces[face_name] = FACE_COLORS[face_name]

    return faces


def get_cubie_center(i, j, k, n, exploded=False, explode_factor=1.5):
    """Calculate center position of cubie (i,j,k) in n×n×n grid."""
    offset = (n - 1) * CUBE_SIZE / 2
    cx = i * CUBE_SIZE - offset
    cy = j * CUBE_SIZE - offset
    cz = k * CUBE_SIZE - offset

    if exploded:
        # Push cubies outward from center
        center = np.array([0.0, 0.0, 0.0])
        pos = np.array([cx, cy, cz])
        if np.linalg.norm(pos) > 0:
            direction = pos / np.linalg.norm(pos)
            pos = pos * explode_factor
            cx, cy, cz = pos

    return cx, cy, cz


def create_rubiks_cube(n=3, exploded=False, explode_factor=1.5, show_edges=True):
    """Create complete N×N×N Rubik's cube mesh with individual cubies."""
    all_vertices = []
    all_faces = []
    all_colors = []
    all_edge_data = []

    for i in range(n):
        for j in range(n):
            for k in range(n):
                cx, cy, cz = get_cubie_center(i, j, k, n, exploded, explode_factor)
                ext_faces = get_exterior_faces(i, j, k, n, exploded)

                if ext_faces:
                    verts, faces, colors, edge_data = create_cubie_mesh(
                        cx, cy, cz, CUBIE_SIZE, ext_faces, show_edges
                    )
                    if len(verts) > 0:
                        faces_adjusted = faces + len(all_vertices) // 3
                        all_vertices.extend(verts)
                        all_faces.extend(faces_adjusted)
                        all_colors.extend(colors)
                        if edge_data is not None:
                            all_edge_data.append(edge_data)

    return (np.array(all_vertices, dtype=np.float32),
            np.array(all_faces, dtype=np.int32),
            all_colors,
            all_edge_data)


# ─── Plotly Visualization ───────────────────────────────────────────────────

def build_figure(vertices, faces, colors, edge_data_list, title_suffix=""):
    x, y, z = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    i, j, k = faces[:, 0], faces[:, 1], faces[:, 2]

    # Main cubie mesh
    fig = go.Figure(data=[go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        facecolor=colors,
        flatshading=True,
        lighting=dict(
            ambient=0.4,
            diffuse=0.9,
            specular=0.6,
            roughness=0.3,
            fresnel=0.15
        ),
        lightposition=dict(x=200, y=300, z=200),
        hoverinfo='none',
        showscale=False,
    )])

    # Add edge lines for each cubie
    for edge_x, edge_y, edge_z in edge_data_list:
        fig.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='#1a1a1a', width=2),
            hoverinfo='none',
            showlegend=False,
        ))

    # Apple-style camera and scene
    fig.update_layout(
        title=dict(
            text=f"Rubik's Cube {title_suffix}",
            x=0.5,
            font=dict(size=24, family='-apple-system, BlinkMacSystemFont, "SF Pro Display", Helvetica, Arial, sans-serif', color='#1d1d1f', weight=600)
        ),
        scene=dict(
            xaxis=dict(visible=False, showgrid=False, zeroline=False, showbackground=False),
            yaxis=dict(visible=False, showgrid=False, zeroline=False, showbackground=False),
            zaxis=dict(visible=False, showgrid=False, zeroline=False, showbackground=False),
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.6, y=1.6, z=1.2),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=1, z=0),
            ),
            dragmode='orbit',
            bgcolor='rgba(0,0,0,0)',
        ),
        margin=dict(l=0, r=0, t=80, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1d1d1f', family='-apple-system, BlinkMacSystemFont, "SF Pro Display", Helvetica, Arial, sans-serif'),
        showlegend=False,
    )

    return fig


# ─── STL Export (for 3D printing) ───────────────────────────────────────────

def export_stl(vertices, faces, colors, output_path, n):
    """Export as STL with per-face colors (using trimesh)."""
    if not TRIMESH_AVAILABLE:
        raise RuntimeError("trimesh not installed. Run: pip install trimesh")

    meshes = []
    color_to_indices = {}

    for idx, (face, color) in enumerate(zip(faces, colors)):
        color_to_indices.setdefault(color, []).append(idx)

    for color, face_indices in color_to_indices.items():
        face_verts = vertices[faces[face_indices]].reshape(-1, 3)
        unique_verts, inverse = np.unique(face_verts, axis=0, return_inverse=True)
        face_tris = inverse.reshape(-1, 3)

        mesh = trimesh.Trimesh(vertices=unique_verts, faces=face_tris, process=False)
        mesh.visual.face_colors = [(*FACE_COLORS_RGB.get(color_name(color), (128, 128, 128)), 255)
                                    for _ in range(len(face_tris))]
        meshes.append(mesh)

    combined = trimesh.util.concatenate(meshes)
    combined.export(str(output_path))
    print(f"✓ Saved STL: {output_path}")


def color_name(hex_color):
    """Map hex color back to face name."""
    for name, hex_val in FACE_COLORS.items():
        if hex_val == hex_color:
            return name
    return 'unknown'


def export_obj(vertices, faces, colors, output_path):
    """Export as OBJ with material groups per color."""
    with open(output_path, 'w') as f:
        f.write("# Rubik's Cube OBJ Export\n")
        f.write(f"# Vertices: {len(vertices)}, Faces: {len(faces)}\n\n")

        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

        color_groups = {}
        for idx, (face, color) in enumerate(zip(faces, colors)):
            color_groups.setdefault(color, []).append(face)

        for color, face_list in color_groups.items():
            face_name = color_name(color)
            f.write(f"\ng {face_name}\n")
            f.write(f"usemtl {face_name}\n")
            for face in face_list:
                f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")

    print(f"✓ Saved OBJ: {output_path}")


# ─── Solver Animation Framework ─────────────────────────────────────────────

class CubeState:
    """Represents the state of an N×N×N Rubik's cube for animation/solving."""
    FACE_NAMES = ['U', 'D', 'F', 'B', 'R', 'L']

    def __init__(self, n=3):
        self.n = n
        self.faces = {
            'U': np.zeros((n, n), dtype=int),
            'D': np.ones((n, n), dtype=int),
            'F': np.full((n, n), 2, dtype=int),
            'B': np.full((n, n), 3, dtype=int),
            'R': np.full((n, n), 4, dtype=int),
            'L': np.full((n, n), 5, dtype=int),
        }

    def rotate_face(self, face, clockwise=True, layer=0):
        pass

    def scramble(self, moves=20):
        import random
        moves_list = ["U", "U'", "D", "D'", "F", "F'", "B", "B'", "R", "R'", "L", "L'"]
        for _ in range(moves):
            move = random.choice(moves_list)
        return self

    def to_mesh_colors(self):
        pass


# ─── Main / CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="3D Rubik's Cube Generator")
    parser.add_argument('--size', '-s', type=int, default=3, help='Cube size (N×N×N), default: 3')
    parser.add_argument('--exploded', '-e', action='store_true', help='Exploded view (all faces visible)')
    parser.add_argument('--explode-factor', type=float, default=1.5, help='Explosion distance factor')
    parser.add_argument('--no-edges', action='store_true', help='Hide cubie edge lines')
    parser.add_argument('--html', action='store_true', default=True, help='Export interactive HTML (default: on)')
    parser.add_argument('--no-html', dest='html', action='store_false', help='Skip HTML export')
    parser.add_argument('--png', action='store_true', help='Export static PNG (requires Chrome/kaleido)')
    parser.add_argument('--stl', action='store_true', help='Export STL for 3D printing (requires trimesh)')
    parser.add_argument('--obj', action='store_true', help='Export OBJ (no extra deps)')
    parser.add_argument('--output', '-o', default='./output', help='Output directory')
    parser.add_argument('--title', default='', help='Custom title suffix')

    args = parser.parse_args()

    if args.size < 2:
        print("Error: Minimum size is 2×2×2")
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building {args.size}×{args.size}×{args.size} Rubik's cube"
          f"{' (exploded)' if args.exploded else ''}...")

    vertices, faces, colors, edge_data = create_rubiks_cube(
        args.size, args.exploded, args.explode_factor, show_edges=not args.no_edges
    )
    print(f"  Vertices: {len(vertices)}")
    print(f"  Triangles: {len(faces)}")
    print(f"  Cubies rendered: {len(edge_data)}")
    print(f"  Edge lines: {len(edge_data) * 12}")

    title = args.title or f"{args.size}×{args.size}×{args.size}"
    if args.exploded:
        title += " Exploded"
    fig = build_figure(vertices, faces, colors, edge_data, title)

    if args.html:
        html_path = output_dir / f"rubiks_{args.size}x{args.size}x{args.size}{'_exploded' if args.exploded else ''}.html"
        fig.write_html(str(html_path), include_plotlyjs='cdn', full_html=True)
        print(f"✓ Saved interactive HTML: {html_path}")

    if args.png:
        png_path = output_dir / f"rubiks_{args.size}x{args.size}x{args.size}{'_exploded' if args.exploded else ''}.png"
        try:
            fig.write_image(str(png_path), width=1600, height=1600, scale=2)
            print(f"✓ Saved PNG: {png_path}")
        except Exception as e:
            print(f"⚠ PNG export failed (need Chrome): {e}")
            print("  Install with: plotly_get_chrome")

    if args.stl:
        stl_path = output_dir / f"rubiks_{args.size}x{args.size}x{args.size}{'_exploded' if args.exploded else ''}.stl"
        try:
            export_stl(vertices, faces, colors, stl_path, args.size)
        except Exception as e:
            print(f"⚠ STL export failed: {e}")
            print("  Install with: pip install trimesh")

    if args.obj:
        obj_path = output_dir / f"rubiks_{args.size}x{args.size}x{args.size}{'_exploded' if args.exploded else ''}.obj"
        try:
            export_obj(vertices, faces, colors, obj_path)
        except Exception as e:
            print(f"⚠ OBJ export failed: {e}")

    print("\nDone!")
    return 0


if __name__ == '__main__':
    sys.exit(main())