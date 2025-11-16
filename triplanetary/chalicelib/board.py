"""
hex_engine.py

Pure-Python hex-board game engine which outputs SVG snapshots for a sequence of turns.

Usage example at bottom.
"""

import math
import os
from typing import Dict, Tuple, List, Optional

# ---- Helpers: hex math (axial coords) ----
SQRT3 = math.sqrt(3.0)

def hex_to_pixel(q: int, r: int, size: float) -> Tuple[float, float]:
    """
    Convert axial hex coords (q, r) to pixel coordinates (x, y).
    Assumes pointy-top hexagons.
    """
    x = size * (SQRT3 * q + (SQRT3 / 2.0) * r)
    y = size * (1.5 * r)
    return x, y

def hex_corners(cx: float, cy: float, size: float) -> List[Tuple[float, float]]:
    """
    Return the 6 corners (x,y) of a pointy-top hex centered at (cx,cy).
    Angles start at 30 degrees (pi/6) and go around.
    """
    corners = []
    for i in range(6):
        angle = math.pi/3.0 * i + math.pi/6.0
        px = cx + size * math.cos(angle)
        py = cy + size * math.sin(angle)
        corners.append((px, py))
    return corners

def points_str(points: List[Tuple[float, float]]) -> str:
    return " ".join(f"{x:.3f},{y:.3f}" for x, y in points)

# ---- Engine ----
class Piece:
    def __init__(self, pid: str, q: int, r: int, color: str = "red", label: Optional[str]=None):
        self.id = pid
        self.q = q
        self.r = r
        self.color = color
        self.label = label or pid

    def pos(self) -> Tuple[int, int]:
        return self.q, self.r

class Turn:
    """
    A turn is a dictionary-like structure describing actions.
    Supported actions:
      - {"type":"place", "id":"p1", "q":0, "r":0, "color":"red"}
      - {"type":"move", "id":"p1", "to": (q,r)}
      - {"type":"remove", "id":"p1"}
      - {"type":"arrow", "from": (q1,r1), "to": (q2,r2), "color":"black"}
    """
    def __init__(self, actions: List[Dict]):
        self.actions = actions

class HexGame:
    def __init__(self, hex_size: float = 40.0, padding: float = 20.0):
        self.hex_size = float(hex_size)
        self.padding = float(padding)
        self.pieces: Dict[str, Piece] = {}
        # Keep historical positions if needed for arrow drawing between turns
        self.history: List[Dict[str, Tuple[int,int]]] = []
        # arrows per snapshot (list of lists)
        self.snap_arrows: List[List[Dict]] = []

    # State management
    def place_piece(self, pid: str, q: int, r: int, color: str = "red"):
        self.pieces[pid] = Piece(pid, q, r, color)

    def move_piece(self, pid: str, q: int, r: int):
        if pid not in self.pieces:
            raise KeyError(f"Piece {pid} not found")
        self.pieces[pid].q = q
        self.pieces[pid].r = r

    def remove_piece(self, pid: str):
        if pid in self.pieces:
            del self.pieces[pid]

    # Apply one turn (a list of actions)
    def apply_turn(self, turn: Turn):
        # snapshot pre-turn positions for arrows that want "from previous pos"
        pre_positions = {pid: (p.q, p.r) for pid, p in self.pieces.items()}
        self.history.append(pre_positions)

        arrows_this_turn = []
        for action in turn.actions:
            typ = action.get("type")
            if typ == "place":
                self.place_piece(action["id"], action["q"], action["r"], action.get("color", "red"))
            elif typ == "move":
                pid = action["id"]
                # optionally record arrow from previous to new
                from_pos = action.get("from")  # can be absolute (q,r) or omitted
                if from_pos is None and pid in pre_positions:
                    from_pos = pre_positions[pid]
                to_q, to_r = action["to"]
                # perform move
                self.move_piece(pid, to_q, to_r)
                if from_pos is not None:
                    arrows_this_turn.append({
                        "from": from_pos,
                        "to": (to_q, to_r),
                        "color": action.get("color", "black")
                    })
            elif typ == "remove":
                self.remove_piece(action["id"])
            elif typ == "arrow":
                arrows_this_turn.append({
                    "from": action["from"],
                    "to": action["to"],
                    "color": action.get("color", "black")
                })
            else:
                raise ValueError(f"Unknown action type: {typ}")
        self.snap_arrows.append(arrows_this_turn)

    def apply_turns(self, turns: List[Turn]):
        for t in turns:
            self.apply_turn(t)

    # ---- Rendering ----
    def _compute_bounds(self) -> Tuple[float,float,float,float]:
        """
        Compute bounding box (minx, miny, maxx, maxy) for all hex centers
        currently in the board (based on pieces). If no pieces, return default box.
        We'll expand bounds to include hex corners and padding.
        """
        if not self.pieces:
            return -200.0, -200.0, 200.0, 200.0

        xs, ys = [], []
        for p in self.pieces.values():
            x, y = hex_to_pixel(p.q, p.r, self.hex_size)
            xs.append(x)
            ys.append(y)

        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)

        # expand by hex radius (size) so entire hex fits
        minx -= self.hex_size + self.padding
        maxx += self.hex_size + self.padding
        miny -= self.hex_size + self.padding
        maxy += self.hex_size + self.padding
        return minx, miny, maxx, maxy

    def render_svg(self, include_grid: bool = True, show_coords: bool = False) -> str:
        """
        Render the current state to an SVG string.
        Includes all pieces and arrows produced in the last applied turn.
        """
        minx, miny, maxx, maxy = self._compute_bounds()
        width = maxx - minx
        height = maxy - miny

        # header
        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{minx:.3f} {miny:.3f} {width:.3f} {height:.3f}" '
            f'width="{width:.0f}" height="{height:.0f}" preserveAspectRatio="xMidYMid meet">'
        ]

        # defs (arrow marker, basic styles)
        svg_lines.append("""
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="black"/>
    </marker>
    <style>
      .hex { fill:#f7f7f7; stroke:#bbb; stroke-width:1; }
      .piece-label { font-family: Arial, sans-serif; font-size: 12px; text-anchor:middle; dominant-baseline:central; fill:white; pointer-events:none; }
    </style>
  </defs>
""")

        # optional grid: draw hexes around current piece extents
        if include_grid:
            # choose reasonable range by expanding extents
            # derive axial range from pixel bounds by reversing hex_to_pixel roughly
            # simple approach: iterate q,r in range around pieces
            qs = [p.q for p in self.pieces.values()]
            rs = [p.r for p in self.pieces.values()]
            if qs and rs:
                qmin, qmax = min(qs)-3, max(qs)+3
                rmin, rmax = min(rs)-3, max(rs)+3
            else:
                qmin, qmax, rmin, rmax = -5, 5, -5, 5

            for q in range(qmin, qmax+1):
                for r in range(rmin, rmax+1):
                    cx, cy = hex_to_pixel(q, r, self.hex_size)
                    corners = hex_corners(cx, cy, self.hex_size)
                    svg_lines.append(f'<polygon class="hex" points="{points_str(corners)}" />')
                    if show_coords:
                        svg_lines.append(f'<text x="{cx:.3f}" y="{cy:.3f}" font-size="9" text-anchor="middle" fill="#444">{q},{r}</text>')

        # pieces
        for p in self.pieces.values():
            cx, cy = hex_to_pixel(p.q, p.r, self.hex_size)
            # larger circle for piece; drop shadow via simple stroke
            svg_lines.append(
                f'<g id="piece-{p.id}">'
                f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{self.hex_size*0.45:.3f}" fill="{p.color}" stroke="#333" stroke-width="1" />'
                f'<text class="piece-label" x="{cx:.3f}" y="{cy:.3f}">{p.label}</text>'
                f'</g>'
            )

        # arrows: use the last appended snap_arrows if any
        if self.snap_arrows:
            arrows = self.snap_arrows[-1]  # arrows created in the most recent applied turn
            for a in arrows:
                (fq, fr) = a["from"]
                (tq, tr) = a["to"]
                fx, fy = hex_to_pixel(fq, fr, self.hex_size)
                tx, ty = hex_to_pixel(tq, tr, self.hex_size)
                # shorten the arrow so it doesn't overlap piece centers: compute vector and shrink by piece radius
                dx = tx - fx
                dy = ty - fy
                dist = math.hypot(dx, dy) if (dx or dy) else 0.0001
                shrink = self.hex_size * 0.5  # shrink by approx piece radius
                sx = fx + dx * (shrink / dist)
                sy = fy + dy * (shrink / dist)
                ex = tx - dx * (shrink / dist)
                ey = ty - dy * (shrink / dist)
                color = a.get("color", "black")
                svg_lines.append(
                    f'<line x1="{sx:.3f}" y1="{sy:.3f}" x2="{ex:.3f}" y2="{ey:.3f}" stroke="{color}" stroke-width="3" marker-end="url(#arrowhead)"/>'
                )

        svg_lines.append("</svg>")
        return "\n".join(svg_lines)

    def save_svg(self, filename: str, include_grid: bool = True, show_coords: bool = False):
        svg = self.render_svg(include_grid=include_grid, show_coords=show_coords)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(svg)

    def save_sequence(self, out_dir: str, prefix: str = "turn"):
        """
        Save one SVG per historical turn.
        Behavior: we rewind state and reapply turns one-by-one, saving after each application.
        The saved SVG for turn N shows the board AFTER the N-th turn.
        """
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        # Save initial (turn 0) snapshot: before any turns (empty or initial pieces)
        # To do this we need to reconstruct from history; but we saved history as pre-positions only.
        # The simplest approach: re-run actions from scratch using copies.
        # So instead, we'll assume the user provides turns and calls apply_turns() themselves,
        # or they can reconstruct by reinitializing a new engine and applying turns stepwise.

        raise NotImplementedError("Use run_save_sequence() which accepts turns and saves snapshots.")

    # Convenience static runner that applies given turns and saves snapshots
    @staticmethod
    def run_save_sequence(turns: List[Turn], out_dir: str, initial_pieces: Optional[List[Dict]] = None,
                          hex_size: float = 40.0):
        """
        Create an engine, place optional initial pieces, apply each turn and save an SVG per turn.
        Filenames: out_dir/turn-001.svg, turn-002.svg, ...
        """
        engine = HexGame(hex_size=hex_size)
        if initial_pieces:
            for ip in initial_pieces:
                engine.place_piece(ip["id"], ip["q"], ip["r"], ip.get("color", "gray"))

        # Save initial snapshot as turn-000 (if desired)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        engine.save_svg(os.path.join(out_dir, f"turn-000.svg"))

        for i, t in enumerate(turns, start=1):
            engine.apply_turn(t)
            engine.save_svg(os.path.join(out_dir, f"turn-{i:03d}.svg"))

# ---- Example usage (can be run when script executed directly) ----
if __name__ == "__main__":
    # Build a short scenario
    turns = [
        Turn([{"type":"place","id":"A","q":0,"r":0,"color":"#d9534f"},
              {"type":"place","id":"B","q":2,"r":-1,"color":"#337ab7"}]),
        Turn([{"type":"move","id":"A","to":(1,0)}]),
        Turn([{"type":"move","id":"B","to":(1,1), "color":"#222"}]),
        Turn([{"type":"arrow","from":(1,0),"to":(1,1),"color":"#555"}]),
        Turn([{"type":"remove","id":"A"}])
    ]

    outdir = "out_svgs"
    HexGame.run_save_sequence(turns, outdir, initial_pieces=None)
    print(f"Saved SVG sequence to ./{outdir}/ (turn-000.svg ... turn-{len(turns):03d}.svg)")
