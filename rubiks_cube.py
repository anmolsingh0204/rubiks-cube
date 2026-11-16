#!/usr/bin/env python3
"""
3D Rubik's Cube with Full Mechanics — Shuffle, Solve, Animate.

Features:
- Correct cubie colors for solved state
- N×N×N cubes (2–7+)
- Move notation: R, U, F, L, D, B + ' (prime) + 2 (double)
- Shuffle with configurable moves
- Animated solve (reverse of shuffle) with speed control
- Interactive HTML with shuffle/solve/speed controls
- STL/OBJ export
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from copy import deepcopy

import numpy as np
import plotly.graph_objects as go

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
# COLOR SCHEME — Standard Rubik's Cube
# ══════════════════════════════════════════════════════════════════════════════

FACE_COLORS = {
    'U': '#FFFFFF',  # White   (Up)
    'D': '#FFD500',  # Yellow  (Down)
    'F': '#C41E3A',  # Red     (Front)
    'B': '#FF5800',  # Orange  (Back)
    'R': '#009B48',  # Green   (Right)
    'L': '#0046AD',  # Blue    (Left)
}

FACE_COLORS_RGB = {
    'U': (255, 255, 255),
    'D': (255, 213, 0),
    'F': (196, 30, 58),
    'B': (255, 88, 0),
    'R': (0, 155, 72),
    'L': (0, 70, 173),
}

# Face indices for internal representation
FACE_IDX = {'U': 0, 'D': 1, 'F': 2, 'B': 3, 'R': 4, 'L': 5}
IDX_FACE = {v: k for k, v in FACE_IDX.items()}

# Standard color indices (matching FACE_COLORS order)
COLOR_IDX = {'U': 0, 'D': 1, 'F': 2, 'B': 3, 'R': 4, 'L': 5}

# Face normals
FACE_NORMALS = {
    'U': (0, 1, 0),   'D': (0, -1, 0),
    'F': (0, 0, 1),   'B': (0, 0, -1),
    'R': (1, 0, 0),   'L': (-1, 0, 0),
}

CUBE_SIZE = 1.0
GAP = 0.05
CUBIE_SIZE = CUBE_SIZE - GAP


# ══════════════════════════════════════════════════════════════════════════════
# CUBE STATE & MECHANICS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CubeState:
    """Complete state of an N×N×N Rubik's cube."""
    n: int
    # faces[f][y][x] = color_index (0-5)
    # Using standard layout: each face is n×n viewed from outside
    faces: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.faces:
            self.reset()

    def reset(self):
        """Reset to solved state."""
        self.faces = {
            'U': np.full((self.n, self.n), COLOR_IDX['U'], dtype=np.uint8),
            'D': np.full((self.n, self.n), COLOR_IDX['D'], dtype=np.uint8),
            'F': np.full((self.n, self.n), COLOR_IDX['F'], dtype=np.uint8),
            'B': np.full((self.n, self.n), COLOR_IDX['B'], dtype=np.uint8),
            'R': np.full((self.n, self.n), COLOR_IDX['R'], dtype=np.uint8),
            'L': np.full((self.n, self.n), COLOR_IDX['L'], dtype=np.uint8),
        }

    def copy(self) -> 'CubeState':
        new = CubeState(self.n)
        new.faces = {k: v.copy() for k, v in self.faces.items()}
        return new

    def get_face_colors(self, face: str) -> np.ndarray:
        """Get color indices for a face."""
        return self.faces[face].copy()

    def set_face_colors(self, face: str, colors: np.ndarray):
        """Set color indices for a face."""
        self.faces[face][:] = colors

    # ─── Rotation Helpers ────────────────────────────────────────────────

    @staticmethod
    def rotate_cw(matrix: np.ndarray) -> np.ndarray:
        """Rotate 2D matrix 90° clockwise."""
        return np.rot90(matrix, -1)

    @staticmethod
    def rotate_ccw(matrix: np.ndarray) -> np.ndarray:
        """Rotate 2D matrix 90° counter-clockwise."""
        return np.rot90(matrix, 1)

    @staticmethod
    def rotate_180(matrix: np.ndarray) -> np.ndarray:
        """Rotate 2D matrix 180°."""
        return np.rot90(matrix, 2)

    # ─── Face Rotations ────────────────────────────────────────────────

    def rotate_face(self, face: str, clockwise: bool = True):
        """Rotate a face 90° in place."""
        if clockwise:
            self.faces[face] = self.rotate_cw(self.faces[face])
        else:
            self.faces[face] = self.rotate_ccw(self.faces[face])

    # ─── Slice Rotations (the actual moves) ────────────────────────────

    def move_R(self, clockwise: bool = True, layer: int = 0):
        """Right face move (and slice if layer > 0)."""
        n = self.n
        layer = layer % n
        col_idx = n - 1 - layer

        # Save affected columns
        U_col = self.faces['U'][:, col_idx].copy()
        F_col = self.faces['F'][:, col_idx].copy()
        D_col = self.faces['D'][:, col_idx].copy()
        # B column is reversed (back face viewed from opposite side)
        B_col = self.faces['B'][:, n - 1 - col_idx].copy()[::-1]

        if clockwise:
            # U -> F -> D -> B -> U
            self.faces['F'][:, col_idx] = U_col
            self.faces['D'][:, col_idx] = F_col
            self.faces['B'][:, n - 1 - col_idx] = D_col[::-1]
            self.faces['U'][:, col_idx] = B_col[::-1]
        else:
            # U <- F <- D <- B <- U
            self.faces['U'][:, col_idx] = F_col
            self.faces['F'][:, col_idx] = D_col
            self.faces['D'][:, col_idx] = B_col[::-1]
            self.faces['B'][:, n - 1 - col_idx] = U_col[::-1]

        # Rotate R face if outer layer
        if layer == 0:
            self.rotate_face('R', clockwise)

    def move_L(self, clockwise: bool = True, layer: int = 0):
        """Left face move."""
        n = self.n
        layer = layer % n
        col_idx = layer

        U_col = self.faces['U'][:, col_idx].copy()
        F_col = self.faces['F'][:, col_idx].copy()
        D_col = self.faces['D'][:, col_idx].copy()
        B_col = self.faces['B'][:, n - 1 - col_idx].copy()[::-1]

        if clockwise:
            # U <- F <- D <- B <- U (opposite of R)
            self.faces['F'][:, col_idx] = D_col
            self.faces['D'][:, col_idx] = B_col[::-1]
            self.faces['B'][:, n - 1 - col_idx] = U_col[::-1]
            self.faces['U'][:, col_idx] = F_col
        else:
            self.faces['U'][:, col_idx] = B_col[::-1]
            self.faces['B'][:, n - 1 - col_idx] = D_col[::-1]
            self.faces['D'][:, col_idx] = F_col
            self.faces['F'][:, col_idx] = U_col

        if layer == 0:
            self.rotate_face('L', clockwise)

    def move_U(self, clockwise: bool = True, layer: int = 0):
        """Up face move."""
        n = self.n
        layer = layer % n
        row_idx = n - 1 - layer

        F_row = self.faces['F'][row_idx, :].copy()
        R_row = self.faces['R'][row_idx, :].copy()
        B_row = self.faces['B'][row_idx, :].copy()
        L_row = self.faces['L'][row_idx, :].copy()

        if clockwise:
            self.faces['R'][row_idx, :] = F_row
            self.faces['B'][row_idx, :] = R_row
            self.faces['L'][row_idx, :] = B_row
            self.faces['F'][row_idx, :] = L_row
        else:
            self.faces['F'][row_idx, :] = R_row
            self.faces['R'][row_idx, :] = B_row
            self.faces['B'][row_idx, :] = L_row
            self.faces['L'][row_idx, :] = F_row

        if layer == 0:
            self.rotate_face('U', clockwise)

    def move_D(self, clockwise: bool = True, layer: int = 0):
        """Down face move."""
        n = self.n
        layer = layer % n
        row_idx = layer

        F_row = self.faces['F'][row_idx, :].copy()
        R_row = self.faces['R'][row_idx, :].copy()
        B_row = self.faces['B'][row_idx, :].copy()
        L_row = self.faces['L'][row_idx, :].copy()

        if clockwise:
            self.faces['L'][row_idx, :] = F_row
            self.faces['F'][row_idx, :] = R_row
            self.faces['R'][row_idx, :] = B_row
            self.faces['B'][row_idx, :] = L_row
        else:
            self.faces['F'][row_idx, :] = L_row
            self.faces['R'][row_idx, :] = F_row
            self.faces['B'][row_idx, :] = R_row
            self.faces['L'][row_idx, :] = B_row

        if layer == 0:
            self.rotate_face('D', clockwise)

    def move_F(self, clockwise: bool = True, layer: int = 0):
        """Front face move."""
        n = self.n
        layer = layer % n
        row_idx = layer

        U_row = self.faces['U'][n - 1 - row_idx, :].copy()
        R_col = self.faces['R'][:, row_idx].copy()
        D_row = self.faces['D'][row_idx, :].copy()
        L_col = self.faces['L'][:, n - 1 - row_idx].copy()[::-1]

        if clockwise:
            # U -> L -> D -> R -> U (with rotations)
            self.faces['L'][:, n - 1 - row_idx] = U_row[::-1]
            self.faces['D'][row_idx, :] = L_col
            self.faces['R'][:, row_idx] = D_row[::-1]
            self.faces['U'][n - 1 - row_idx, :] = R_col[::-1]
        else:
            self.faces['U'][n - 1 - row_idx, :] = L_col
            self.faces['R'][:, row_idx] = U_row
            self.faces['D'][row_idx, :] = R_col[::-1]
            self.faces['L'][:, n - 1 - row_idx] = D_row

        if layer == 0:
            self.rotate_face('F', clockwise)

    def move_B(self, clockwise: bool = True, layer: int = 0):
        """Back face move."""
        n = self.n
        layer = layer % n
        row_idx = n - 1 - layer

        U_row = self.faces['U'][row_idx, :].copy()
        R_col = self.faces['R'][:, n - 1 - row_idx].copy()
        D_row = self.faces['D'][n - 1 - row_idx, :].copy()
        L_col = self.faces['L'][:, row_idx].copy()[::-1]

        if clockwise:
            self.faces['R'][:, n - 1 - row_idx] = U_row
            self.faces['D'][n - 1 - row_idx, :] = R_col[::-1]
            self.faces['L'][:, row_idx] = D_row
            self.faces['U'][row_idx, :] = L_col[::-1]
        else:
            self.faces['U'][row_idx, :] = R_col
            self.faces['L'][:, row_idx] = U_row[::-1]
            self.faces['D'][n - 1 - row_idx, :] = L_col[::-1]
            self.faces['R'][:, n - 1 - row_idx] = D_row

        if layer == 0:
            self.rotate_face('B', clockwise)

    # ─── Move Application ──────────────────────────────────────────────

    def apply_move(self, move: str):
        """Apply a move string like 'R', "R'", 'R2', 'U', etc."""
        move = move.strip()
        if not move:
            return

        face = move[0]
        clockwise = True
        times = 1

        if len(move) > 1:
            if move[1] == "'":
                clockwise = False
            elif move[1] == '2':
                times = 2

        move_func = getattr(self, f'move_{face}')
        for _ in range(times):
            move_func(clockwise)

    def apply_moves(self, moves: List[str]):
        """Apply a sequence of moves."""
        for move in moves:
            self.apply_move(move)

    def scramble(self, num_moves: int = 20, seed: Optional[int] = None) -> List[str]:
        """Generate and apply a random scramble. Returns the move list."""
        if seed is not None:
            np.random.seed(seed)

        # Standard move set
        base_moves = ['R', 'U', 'F', 'L', 'D', 'B']
        moves = []
        last_face = None

        for _ in range(num_moves):
            # Avoid consecutive moves on same face
            available = [m for m in base_moves if m != last_face]
            face = np.random.choice(available)
            last_face = face

            # Random modifier
            mod = np.random.choice(['', "'", '2'], p=[0.5, 0.25, 0.25])
            move = face + mod
            moves.append(move)
            self.apply_move(move)

        return moves

    def get_solution_moves(self, scramble_moves: List[str]) -> List[str]:
        """Get moves to solve (reverse of scramble with inverted moves)."""
        solution = []
        for move in reversed(scramble_moves):
            face = move[0]
            if len(move) == 1:
                solution.append(face + "'")
            elif move[1] == "'":
                solution.append(face)
            elif move[1] == '2':
                solution.append(face + '2')
        return solution

    # ─── Color Mapping for Rendering ──────────────────────────────────

    def get_cubie_face_colors(self, x: int, y: int, z: int) -> dict:
        """
        Get the color of each face of the cubie at (x, y, z).
        x: 0=left to n-1=right
        y: 0=down to n-1=up
        z: 0=back to n-1=front
        """
        n = self.n
        colors = {}

        # Left face (x=0) -> L color
        if x == 0:
            colors['L'] = IDX_FACE[self.faces['L'][n - 1 - y, z]]
        # Right face (x=n-1) -> R color
        if x == n - 1:
            colors['R'] = IDX_FACE[self.faces['R'][n - 1 - y, z]]
        # Down face (y=0) -> D color
        if y == 0:
            colors['D'] = IDX_FACE[self.faces['D'][z, x]]
        # Up face (y=n-1) -> U color
        if y == n - 1:
            colors['U'] = IDX_FACE[self.faces['U'][n - 1 - z, x]]
        # Back face (z=0) -> B color
        if z == 0:
            colors['B'] = IDX_FACE[self.faces['B'][n - 1 - y, n - 1 - x]]
        # Front face (z=n-1) -> F color
        if z == n - 1:
            colors['F'] = IDX_FACE[self.faces['F'][n - 1 - y, x]]

        return colors


# ══════════════════════════════════════════════════════════════════════════════
# GEOMETRY GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def create_cubie_mesh(center_x, center_y, center_z, size, face_colors, show_edges=True):
    """Create mesh for a single cubie with faces and optional edge lines."""
    half = size / 2
    cx, cy, cz = center_x, center_y, center_z

    vertices = np.array([
        [cx - half, cy - half, cz - half],  # 0
        [cx + half, cy - half, cz - half],  # 1
        [cx + half, cy + half, cz - half],  # 2
        [cx - half, cy + half, cz - half],  # 3
        [cx - half, cy - half, cz + half],  # 4
        [cx + half, cy - half, cz + half],  # 5
        [cx + half, cy + half, cz + half],  # 6
        [cx - half, cy + half, cz + half],  # 7
    ], dtype=np.float32)

    faces = [
        [0, 1, 2], [0, 2, 3],  # Back (-Z)
        [4, 7, 6], [4, 6, 5],  # Front (+Z)
        [0, 4, 5], [0, 5, 1],  # Bottom (-Y)
        [3, 2, 6], [3, 6, 7],  # Top (+Y)
        [0, 3, 7], [0, 7, 4],  # Left (-X)
        [1, 5, 6], [1, 6, 2],  # Right (+X)
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

    edge_data = None
    if show_edges:
        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],
            [4, 5], [5, 6], [6, 7], [7, 4],
            [0, 4], [1, 5], [2, 6], [3, 7],
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


def get_cubie_center(i, j, k, n, exploded=False, explode_factor=1.5):
    """Calculate center position of cubie (i,j,k) in n×n×n grid."""
    offset = (n - 1) * CUBE_SIZE / 2
    cx = i * CUBE_SIZE - offset
    cy = j * CUBE_SIZE - offset
    cz = k * CUBE_SIZE - offset

    if exploded:
        pos = np.array([cx, cy, cz])
        if np.linalg.norm(pos) > 0:
            direction = pos / np.linalg.norm(pos)
            pos = pos * explode_factor
            cx, cy, cz = pos

    return cx, cy, cz


def create_cube_mesh(state: CubeState, exploded=False, explode_factor=1.5, show_edges=True):
    """Create complete mesh from a CubeState."""
    n = state.n
    all_vertices = []
    all_faces = []
    all_colors = []
    all_edge_data = []

    for i in range(n):
        for j in range(n):
            for k in range(n):
                cx, cy, cz = get_cubie_center(i, j, k, n, exploded, explode_factor)
                cubie_colors = state.get_cubie_face_colors(i, j, k)

                if cubie_colors or exploded:
                    # For exploded view, show all faces with their colors
                    if exploded:
                        # Use the actual colors from the state
                        ext_faces = {}
                        for face_name in ['U', 'D', 'F', 'B', 'R', 'L']:
                            idx = state.get_cubie_face_colors(i, j, k).get(face_name)
                            if idx is not None:
                                ext_faces[face_name] = FACE_COLORS[idx]
                            else:
                                ext_faces[face_name] = FACE_COLORS[face_name]
                    else:
                        ext_faces = {k: FACE_COLORS[v] for k, v in cubie_colors.items()}

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


# ══════════════════════════════════════════════════════════════════════════════
# ANIMATION FRAME GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def interpolate_cube_positions(state_start: CubeState, state_end: CubeState,
                                move: str, steps: int) -> List[CubeState]:
    """
    Generate intermediate cube states for animating a single move.
    This is a simplified interpolation - for true smooth animation we'd need
    to rotate the actual geometry. For now, we'll do discrete steps.
    """
    states = []
    n = state_start.n

    # For a proper animation, we'd rotate the cubies in 3D space.
    # Here we'll just show the start and end states for each move.
    # A full implementation would require per-cubie transformation matrices.

    return [state_start, state_end]


def generate_animation_frames(scramble_moves: List[str], n: int, frames_per_move: int = 8) -> List[CubeState]:
    """
    Generate all frames for animating the solve (reverse of scramble).
    Returns list of CubeState objects for each frame.
    """
    # Start from scrambled state
    state = CubeState(n)
    state.apply_moves(scramble_moves)

    solution_moves = state.get_solution_moves(scramble_moves)
    frames = [state.copy()]

    for move in solution_moves:
        for step in range(frames_per_move):
            # Create intermediate state
            # For simplicity, we'll apply the move at the end of each frame group
            # A real implementation would interpolate geometry
            if step == frames_per_move - 1:
                state.apply_move(move)
            frames.append(state.copy())

    return frames


# ══════════════════════════════════════════════════════════════════════════════
# PLOTLY VISUALIZATION WITH ANIMATION
# ══════════════════════════════════════════════════════════════════════════════

def build_animated_figure(frames: List[CubeState], n: int, title: str):
    """Build a Plotly figure with animation frames."""
    # Pre-compute all frame data
    frame_data = []
    for frame_state in frames:
        verts, faces, colors, edges = create_cube_mesh(frame_state, show_edges=True)
        x, y, z = verts[:, 0], verts[:, 1], verts[:, 2]
        i, j, k = faces[:, 0], faces[:, 1], faces[:, 2]

        # Main mesh
        mesh = go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            facecolor=colors,
            flatshading=True,
            lighting=dict(ambient=0.4, diffuse=0.9, specular=0.6, roughness=0.3, fresnel=0.15),
            lightposition=dict(x=200, y=300, z=200),
            hoverinfo='none',
            showscale=False,
        )

        # Edges
        edge_traces = []
        for edge_x, edge_y, edge_z in edges:
            edge_traces.append(go.Scatter3d(
                x=edge_x, y=edge_y, z=edge_z,
                mode='lines',
                line=dict(color='#1a1a1a', width=2),
                hoverinfo='none',
                showlegend=False,
            ))

        frame_data.append((mesh, edge_traces))

    # Initial frame
    init_mesh, init_edges = frame_data[0]

    fig = go.Figure(
        data=[init_mesh] + init_edges,
        frames=[
            go.Frame(
                data=[fd[0]] + fd[1],
                name=str(idx)
            )
            for idx, fd in enumerate(frame_data)
        ]
    )

    # Animation controls
    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            font=dict(size=24, family='-apple-system, BlinkMacSystemFont, "SF Pro Display", Helvetica, Arial, sans-serif', color='#1d1d1f', weight=600)
        ),
        scene=dict(
            xaxis=dict(visible=False, showgrid=False, zeroline=False, showbackground=False),
            yaxis=dict(visible=False, showgrid=False, zeroline=False, showbackground=False),
            zaxis=dict(visible=False, showgrid=False, zeroline=False, showbackground=False),
            aspectmode='data',
            camera=dict(eye=dict(x=1.6, y=1.6, z=1.2), center=dict(x=0, y=0, z=0), up=dict(x=0, y=1, z=0)),
            dragmode='orbit',
            bgcolor='rgba(0,0,0,0)',
        ),
        margin=dict(l=0, r=0, t=80, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1d1d1f', family='-apple-system, BlinkMacSystemFont, "SF Pro Display", Helvetica, Arial, sans-serif'),
        showlegend=False,
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': '▶ Play',
                    'method': 'animate',
                    'args': [None, {
                        'frame': {'duration': 100, 'redraw': True},
                        'fromcurrent': True,
                        'mode': 'immediate'
                    }]
                },
                {
                    'label': '⏸ Pause',
                    'method': 'animate',
                    'args': [[None], {
                        'frame': {'duration': 0, 'redraw': False},
                        'mode': 'immediate'
                    }]
                }
            ],
            'x': 0.05,
            'y': 0.05,
            'xanchor': 'left',
            'yanchor': 'bottom'
        }],
        sliders=[{
            'steps': [
                {
                    'method': 'animate',
                    'label': str(i),
                    'args': [[str(i)], {
                        'frame': {'duration': 0, 'redraw': True},
                        'mode': 'immediate'
                    }]
                }
                for i in range(len(frame_data))
            ],
            'active': 0,
            'currentvalue': {'prefix': 'Frame: '},
            'x': 0.1,
            'y': 0,
            'len': 0.9
        }]
    )

    return fig


def build_static_figure(vertices, faces, colors, edge_data_list, title_suffix=""):
    """Build a static (non-animated) Plotly figure."""
    x, y, z = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    i, j, k = faces[:, 0], faces[:, 1], faces[:, 2]

    fig = go.Figure(data=[go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        facecolor=colors,
        flatshading=True,
        lighting=dict(ambient=0.4, diffuse=0.9, specular=0.6, roughness=0.3, fresnel=0.15),
        lightposition=dict(x=200, y=300, z=200),
        hoverinfo='none',
        showscale=False,
    )])

    for edge_x, edge_y, edge_z in edge_data_list:
        fig.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='#1a1a1a', width=2),
            hoverinfo='none',
            showlegend=False,
        ))

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
            camera=dict(eye=dict(x=1.6, y=1.6, z=1.2), center=dict(x=0, y=0, z=0), up=dict(x=0, y=1, z=0)),
            dragmode='orbit',
            bgcolor='rgba(0,0,0,0)',
        ),
        margin=dict(l=0, r=0, t=80, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1d1d1f', family='-apple-system, BlinkMacSystemFont, "SF Pro Display", Helvetica, Arial, sans-serif'),
        showlegend=False,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# STL/OBJ EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def export_stl(vertices, faces, colors, output_path, n):
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
    for name, hex_val in FACE_COLORS.items():
        if hex_val == hex_color:
            return name
    return 'unknown'


def export_obj(vertices, faces, colors, output_path):
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


# ══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE HTML GENERATION (with Shuffle/Solve/Speed controls)
# ══════════════════════════════════════════════════════════════════════════════

INTERACTIVE_HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}}</title>
    <style>
        :root {
            --bg: #f5f5f7;
            --glass: rgba(255, 255, 255, 0.72);
            --glass-border: rgba(255, 255, 255, 0.3);
            --text: #1d1d1f;
            --text-secondary: #6e6e73;
            --accent: #0071e3;
            --accent-hover: #0077ed;
            --danger: #ff3b30;
            --danger-hover: #ff453a;
            --success: #34c759;
            --warning: #ff9f0a;
            --shadow: 0 8px 32px rgba(0,0,0,0.08);
            --radius: 16px;
            --transition: 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --bg: #1d1d1f;
                --glass: rgba(29, 29, 31, 0.8);
                --glass-border: rgba(255,255,255,0.1);
                --text: #f5f5f7;
                --text-secondary: #86868b;
            }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            padding: 1.5rem;
            text-align: center;
            border-bottom: 1px solid var(--glass-border);
            background: var(--glass);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            position: sticky;
            top: 0;
            z-index: 10;
        }
        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
            letter-spacing: -0.02em;
        }
        .controls {
            padding: 1rem 1.5rem;
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
            background: var(--glass);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--glass-border);
        }
        .control-group {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            background: rgba(255,255,255,0.1);
            padding: 0.75rem 1rem;
            border-radius: var(--radius);
            border: 1px solid var(--glass-border);
        }
        .control-group label {
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .control-group select, .control-group input[type="range"] {
            background: var(--glass);
            border: 1px solid var(--glass-border);
            border-radius: 8px;
            color: var(--text);
            padding: 0.5rem 0.75rem;
            font-size: 0.85rem;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.25rem;
            border-radius: var(--radius);
            font-size: 0.9rem;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: var(--transition);
            white-space: nowrap;
        }
        .btn-primary {
            background: var(--accent);
            color: white;
            box-shadow: 0 4px 16px rgba(0, 113, 227, 0.3);
        }
        .btn-primary:hover:not(:disabled) {
            background: var(--accent-hover);
            transform: translateY(-2px);
        }
        .btn-danger {
            background: var(--danger);
            color: white;
            box-shadow: 0 4px 16px rgba(255, 59, 48, 0.3);
        }
        .btn-danger:hover:not(:disabled) {
            background: var(--danger-hover);
            transform: translateY(-2px);
        }
        .btn-success {
            background: var(--success);
            color: white;
            box-shadow: 0 4px 16px rgba(52, 199, 89, 0.3);
        }
        .btn-success:hover:not(:disabled) {
            transform: translateY(-2px);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }
        .speed-control {
            flex: 1;
            min-width: 200px;
        }
        .speed-control input[type="range"] {
            width: 100%;
            accent-color: var(--accent);
        }
        .speed-value {
            font-family: 'Space Grotesk', monospace;
            font-weight: 600;
            color: var(--accent);
            min-width: 3rem;
            text-align: right;
        }
        .status {
            padding: 0.5rem 1rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-align: center;
            min-height: 1.5rem;
        }
        .status.solving { color: var(--accent); }
        .status.shuffling { color: var(--warning); }
        .status.ready { color: var(--success); }
        #plotly-div {
            flex: 1;
            width: 100%;
            height: calc(100vh - 180px);
            min-height: 500px;
        }
        @media (max-width: 600px) {
            .controls { flex-direction: column; align-items: stretch; }
            .control-group { justify-content: space-between; }
            .speed-control { min-width: 0; }
        }
    </style>
</head>
<body>
    <header class="header">
        <h1>{{TITLE}}</h1>
    </header>
    <div class="controls">
        <div class="control-group">
            <label>Speed</label>
            <input type="range" id="speed-slider" min="0.5" max="2.0" step="0.1" value="1.0">
            <span class="speed-value" id="speed-value">1.0×</span>
        </div>
        <button class="btn btn-danger" id="shuffle-btn" onclick="shuffleCube()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="16 3 23 3 23 10"></polyline>
                <path d="M22 20v-6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v6"></path>
            </svg>
            Shuffle
        </button>
        <button class="btn btn-success" id="solve-btn" onclick="solveCube()" disabled>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                <path d="M2 17l10 5 10-5"></path>
            </svg>
            Solve
        </button>
        <button class="btn btn-primary" id="reset-btn" onclick="resetCube()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="1 4 1 10 7 10"></polyline>
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
            </svg>
            Reset
        </button>
    </div>
    <div class="status" id="status">Ready</div>
    <div id="plotly-div"></div>

    <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
    <script>
        // Configuration
        const CUBE_SIZE = {{N}};
        const SCRAMBLE_MOVES = {{SCRAMBLE_MOVES}};
        const FRAMES_PER_MOVE = {{FRAMES_PER_MOVE}};

        let currentFrame = 0;
        let totalFrames = 0;
        let isAnimating = false;
        let animationDirection = 1; // 1 = forward (solving), -1 = reverse (shuffling)
        let animationTimer = null;
        let baseFrameDuration = 100; // ms at 1.0x speed

        // Load the initial figure data
        const initialData = {{INITIAL_DATA | tojson }};
        const framesData = {{FRAMES_DATA | tojson }};

        // Initialize plot
        const plotDiv = document.getElementById('plotly-div');
        Plotly.newPlot(plotDiv, initialData.data, initialData.layout).then(() => {
            totalFrames = framesData.length;
            updateStatus('ready', 'Ready — Click Shuffle to scramble');
        });

        function updateStatus(type, message) {
            const el = document.getElementById('status');
            el.className = 'status ' + type;
            el.textContent = message;
        }

        function setButtons(shuffling, solving, animating) {
            document.getElementById('shuffle-btn').disabled = shuffling || animating;
            document.getElementById('solve-btn').disabled = solving || animating;
            document.getElementById('reset-btn').disabled = animating;
        }

        function getFrameDuration() {
            const speed = parseFloat(document.getElementById('speed-slider').value);
            return baseFrameDuration / speed;
        }

        function updateSpeedDisplay() {
            const speed = parseFloat(document.getElementById('speed-slider').value);
            document.getElementById('speed-value').textContent = speed.toFixed(1) + '×';
        }

        document.getElementById('speed-slider').addEventListener('input', updateSpeedDisplay);

        function animateToFrame(targetFrame) {
            if (isAnimating) return;
            isAnimating = true;
            setButtons(false, false, true);

            const direction = targetFrame > currentFrame ? 1 : -1;
            const duration = getFrameDuration();

            function step() {
                if (!isAnimating) return;

                currentFrame += direction;
                Plotly.react(plotDiv, framesData[currentFrame].data, initialData.layout);

                if (currentFrame === targetFrame) {
                    isAnimating = false;
                    animationTimer = null;
                    onAnimationComplete();
                    return;
                }

                animationTimer = setTimeout(step, duration);
            }

            step();
        }

        function onAnimationComplete() {
            if (animationDirection === 1) {
                // Finished solving
                updateStatus('ready', 'Solved!');
                setButtons(false, true, false);
            } else {
                // Finished shuffling
                updateStatus('ready', 'Scrambled — Click Solve to solve');
                setButtons(true, false, false);
            }
        }

        function shuffleCube() {
            if (isAnimating) return;
            animationDirection = -1;
            updateStatus('shuffling', 'Shuffling...');
            setButtons(true, true, true);

            // Animate from solved (frame 0) to scrambled (last frame)
            currentFrame = 0;
            animateToFrame(totalFrames - 1);
        }

        function solveCube() {
            if (isAnimating) return;
            animationDirection = 1;
            updateStatus('solving', 'Solving...');
            setButtons(true, true, true);

            // Animate from current to solved (frame 0)
            animateToFrame(0);
        }

        function resetCube() {
            if (isAnimating) return;
            if (animationTimer) clearTimeout(animationTimer);
            isAnimating = false;
            currentFrame = 0;
            Plotly.react(plotDiv, framesData[0].data, initialData.layout);
            updateStatus('ready', 'Ready — Click Shuffle to scramble');
            setButtons(false, true, false);
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === ' ') { e.preventDefault(); shuffleCube(); }
            if (e.key === 'Enter') { e.preventDefault(); solveCube(); }
            if (e.key === 'Escape') { resetCube(); }
            if (e.key === 'ArrowRight' && currentFrame < totalFrames - 1) {
                currentFrame++;
                Plotly.react(plotDiv, framesData[currentFrame].data, initialData.layout);
            }
            if (e.key === 'ArrowLeft' && currentFrame > 0) {
                currentFrame--;
                Plotly.react(plotDiv, framesData[currentFrame].data, initialData.layout);
            }
        });
    </script>
</body>
</html>
'''


def generate_interactive_html(state: CubeState, scramble_moves: List[str],
                               n: int, frames_per_move: int, output_path: Path):
    """Generate interactive HTML with shuffle/solve animation."""
    from jinja2 import Template

    # Generate all animation frames
    print(f"  Generating {len(scramble_moves) * frames_per_move + 1} animation frames...")
    frames = generate_animation_frames(scramble_moves, n, frames_per_move)

    # Build frame data for each frame
    frames_data = []
    for idx, frame_state in enumerate(frames):
        verts, faces, colors, edges = create_cube_mesh(frame_state, show_edges=True)
        x, y, z = verts[:, 0], verts[:, 1], verts[:, 2]
        i, j, k = faces[:, 0], faces[:, 1], faces[:, 2]

        mesh = {
            'type': 'mesh3d',
            'x': [float(v) for v in x], 'y': [float(v) for v in y], 'z': [float(v) for v in z],
            'i': [int(v) for v in i], 'j': [int(v) for v in j], 'k': [int(v) for v in k],
            'facecolor': colors,
            'flatshading': True,
            'lighting': {'ambient': 0.4, 'diffuse': 0.9, 'specular': 0.6, 'roughness': 0.3, 'fresnel': 0.15},
            'lightposition': {'x': 200, 'y': 300, 'z': 200},
            'hoverinfo': 'none',
            'showscale': False,
        }

        edge_traces = []
        for edge_x, edge_y, edge_z in edges:
            edge_traces.append({
                'type': 'scatter3d',
                'x': [float(v) if v is not None else None for v in edge_x],
                'y': [float(v) if v is not None else None for v in edge_y],
                'z': [float(v) if v is not None else None for v in edge_z],
                'mode': 'lines',
                'line': {'color': '#1a1a1a', 'width': 2},
                'hoverinfo': 'none',
                'showlegend': False,
            })

        frames_data.append({'data': [mesh] + edge_traces})

    # Initial figure layout
    initial_layout = {
        'title': {'text': f"Rubik's Cube {n}×{n}×{n} — Interactive", 'x': 0.5,
                  'font': {'size': 24, 'family': '-apple-system, BlinkMacSystemFont, "SF Pro Display", Helvetica, Arial, sans-serif', 'color': '#1d1d1f', 'weight': 600}},
        'scene': {
            'xaxis': {'visible': False, 'showgrid': False, 'zeroline': False, 'showbackground': False},
            'yaxis': {'visible': False, 'showgrid': False, 'zeroline': False, 'showbackground': False},
            'zaxis': {'visible': False, 'showgrid': False, 'zeroline': False, 'showbackground': False},
            'aspectmode': 'data',
            'camera': {'eye': {'x': 1.6, 'y': 1.6, 'z': 1.2}, 'center': {'x': 0, 'y': 0, 'z': 0}, 'up': {'x': 0, 'y': 1, 'z': 0}},
            'dragmode': 'orbit',
            'bgcolor': 'rgba(0,0,0,0)',
        },
        'margin': {'l': 0, 'r': 0, 't': 80, 'b': 0},
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'font': {'color': '#1d1d1f', 'family': '-apple-system, BlinkMacSystemFont, "SF Pro Display", Helvetica, Arial, sans-serif'},
        'showlegend': False,
    }

    # Convert initial data to JSON-serializable
    def convert_data(data):
        result = []
        for trace in data:
            if trace['type'] == 'mesh3d':
                result.append({
                    'type': 'mesh3d',
                    'x': [float(v) for v in trace['x']],
                    'y': [float(v) for v in trace['y']],
                    'z': [float(v) for v in trace['z']],
                    'i': [int(v) for v in trace['i']],
                    'j': [int(v) for v in trace['j']],
                    'k': [int(v) for v in trace['k']],
                    'facecolor': trace['facecolor'],
                    'flatshading': trace['flatshading'],
                    'lighting': trace['lighting'],
                    'lightposition': trace['lightposition'],
                    'hoverinfo': trace['hoverinfo'],
                    'showscale': trace['showscale'],
                })
            elif trace['type'] == 'scatter3d':
                result.append({
                    'type': 'scatter3d',
                    'x': [float(v) if v is not None else None for v in trace['x']],
                    'y': [float(v) if v is not None else None for v in trace['y']],
                    'z': [float(v) if v is not None else None for v in trace['z']],
                    'mode': trace['mode'],
                    'line': trace['line'],
                    'hoverinfo': trace['hoverinfo'],
                    'showlegend': trace['showlegend'],
                })
        return result

    initial_data = {'data': convert_data(frames_data[0]['data']), 'layout': initial_layout}
    frames_data = [{'data': convert_data(fd['data'])} for fd in frames_data]

    # Render template
    template = Template(INTERACTIVE_HTML_TEMPLATE)
    html = template.render(
        TITLE=f"Rubik's Cube {n}×{n}×{n} — Interactive",
        N=n,
        SCRAMBLE_MOVES=scramble_moves,
        FRAMES_PER_MOVE=frames_per_move,
        INITIAL_DATA=initial_data,
        FRAMES_DATA=frames_data,
    )

    output_path.write_text(html)
    print(f"✓ Saved interactive HTML: {output_path}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN / CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="3D Rubik's Cube with Shuffle/Solve Animation")
    parser.add_argument('--size', '-s', type=int, default=3, help='Cube size (N×N×N), default: 3')
    parser.add_argument('--exploded', '-e', action='store_true', help='Exploded view')
    parser.add_argument('--explode-factor', type=float, default=1.5, help='Explosion distance')
    parser.add_argument('--no-edges', action='store_true', help='Hide cubie edge lines')
    parser.add_argument('--scramble', type=int, default=15, help='Number of scramble moves (default: 15)')
    parser.add_argument('--seed', type=int, help='Random seed for reproducible scramble')
    parser.add_argument('--frames-per-move', type=int, default=6, help='Animation frames per move (default: 6)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Generate interactive HTML with shuffle/solve controls')
    parser.add_argument('--static', action='store_true', help='Generate static HTML (no animation)')
    parser.add_argument('--png', action='store_true', help='Export static PNG')
    parser.add_argument('--stl', action='store_true', help='Export STL for 3D printing')
    parser.add_argument('--obj', action='store_true', help='Export OBJ')
    parser.add_argument('--output', '-o', default='./output', help='Output directory')
    parser.add_argument('--title', default='', help='Custom title')

    args = parser.parse_args()

    if args.size < 2:
        print("Error: Minimum size is 2×2×2")
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create solved state
    state = CubeState(args.size)

    # Generate scramble
    scramble_moves = state.scramble(args.scramble, args.seed)
    print(f"Scramble ({len(scramble_moves)} moves): {' '.join(scramble_moves)}")

    # Apply scramble to get scrambled state
    scrambled_state = state.copy()
    scrambled_state.apply_moves(scramble_moves)

    title = args.title or f"{args.size}×{args.size}×{args.size}"
    if args.exploded:
        title += " Exploded"

    if args.interactive:
        print(f"Building interactive {args.size}×{args.size}×{args.size} cube with animation...")
        verts, faces, colors, edges = create_cube_mesh(scrambled_state, args.exploded, args.explode_factor, not args.no_edges)
        print(f"  Vertices: {len(verts)}, Triangles: {len(faces)}, Cubies: {len(edges)}")
        generate_interactive_html(
            scrambled_state, scramble_moves, args.size,
            args.frames_per_move,
            output_dir / f"rubiks_{args.size}x{args.size}x{args.size}{'_exploded' if args.exploded else ''}_interactive.html"
        )
    else:
        # Static view (scrambled state)
        print(f"Building static {args.size}×{args.size}×{args.size} cube...")
        verts, faces, colors, edges = create_cube_mesh(scrambled_state, args.exploded, args.explode_factor, not args.no_edges)
        print(f"  Vertices: {len(verts)}, Triangles: {len(faces)}, Cubies: {len(edges)}")
        fig = build_static_figure(verts, faces, colors, edges, title)

        if args.static or args.html:
            html_path = output_dir / f"rubiks_{args.size}x{args.size}x{args.size}{'_exploded' if args.exploded else ''}.html"
            fig.write_html(str(html_path), include_plotlyjs='cdn')
            print(f"✓ Saved static HTML: {html_path}")

        if args.png:
            png_path = output_dir / f"rubiks_{args.size}x{args.size}x{args.size}{'_exploded' if args.exploded else ''}.png"
            try:
                fig.write_image(str(png_path), width=1600, height=1600, scale=2)
                print(f"✓ Saved PNG: {png_path}")
            except Exception as e:
                print(f"⚠ PNG export failed: {e}")

    if args.stl:
        stl_path = output_dir / f"rubiks_{args.size}x{args.size}x{args.size}{'_exploded' if args.exploded else ''}.stl"
        try:
            export_stl(verts, faces, colors, stl_path, args.size)
        except Exception as e:
            print(f"⚠ STL export failed: {e}")

    if args.obj:
        obj_path = output_dir / f"rubiks_{args.size}x{args.size}x{args.size}{'_exploded' if args.exploded else ''}.obj"
        try:
            export_obj(verts, faces, colors, obj_path)
        except Exception as e:
            print(f"⚠ OBJ export failed: {e}")

    print("\nDone!")
    return 0


if __name__ == '__main__':
    sys.exit(main())