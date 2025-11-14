"""
Triplanetary Movement Phase Implementation

Based on the rules from pages 2-4:
- Vector movement: ships continue in same direction/distance unless accelerated
- One fuel point allows changing endpoint by one hex
- Gravity hexes affect movement on the turn AFTER entering them
- Weak gravity can be ignored or used (first hex), subsequent weak gravity acts as full
- Crashes occur when vector intersects astral body outline
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum


class FeatureType(Enum):
    PLANET = "planet"
    ASTEROID = "asteroid"
    STRONG_GRAVITY = "strong_gravity"
    WEAK_GRAVITY = "weak_gravity"
    MAP_BOUNDARY = "map_boundary"


@dataclass
class Vector:
    """Represents direction and magnitude as hex coordinates"""
    dx: int  # horizontal hex displacement
    dy: int  # vertical hex displacement
    
    def length(self) -> int:
        """Calculate hex distance (using cube coordinate distance)"""
        return (abs(self.dx) + abs(self.dy) + abs(self.dx + self.dy)) // 2
    
    def __add__(self, other):
        return Vector(self.dx + other.dx, self.dy + other.dy)
    
    def __repr__(self):
        return f"Vector({self.dx}, {self.dy})"


@dataclass
class Position:
    """Hex position on map"""
    x: int
    y: int
    
    def __add__(self, vector: Vector):
        return Position(self.x + vector.dx, self.y + vector.dy)
    
    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y)
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))
    
    def __repr__(self):
        return f"Pos({self.x}, {self.y})"


@dataclass
class Ship:
    """Ship or ordnance in play"""
    name: str
    position: Position
    vector: Vector  # Last turn's movement
    acceleration: Vector  # Fuel burn this turn (0 or 1 hex change)
    strong_gravity_last_turn: List[Vector]  # Gravity from hexes entered last turn
    chosen_weak_gravity_last_turn: List[Vector]  # Weak gravity chosen last turn


@dataclass
class MapFeature:
    """Static map feature"""
    name: str
    feature_type: FeatureType
    position: Position
    gravity_direction: Optional[Vector] = None  # For gravity hexes


@dataclass
class Movement:
    """Result of movement for one ship"""
    new_position: Position
    new_vector: Vector
    strong_gravity_next_turn: List[Vector]
    weak_gravity_options_next_turn: List[Vector]
    path: List[Position]  # Hexes traversed during movement
    crashed: bool = False
    crash_reason: str = ""
    off_map: bool = False


def calculate_predicted_endpoint(ship: Ship) -> Position:
    """
    Calculate where ship would end up with no acceleration.
    This is the base vector plus accumulated gravity from last turn.
    """
    # Start with the ship's base vector (repeat last turn's movement)
    total_movement = Vector(ship.vector.dx, ship.vector.dy)
    
    # Apply strong gravity from last turn (mandatory and cumulative)
    for gravity in ship.strong_gravity_last_turn:
        total_movement = total_movement + gravity
    
    # Apply chosen weak gravity from last turn
    for gravity in ship.chosen_weak_gravity_last_turn:
        total_movement = total_movement + gravity
    
    return ship.position + total_movement


def calculate_actual_endpoint(ship: Ship) -> Position:
    """
    Calculate actual endpoint including fuel burn.
    Fuel burn allows changing endpoint by one hex in any direction.
    """
    predicted = calculate_predicted_endpoint(ship)
    return predicted + ship.acceleration


def get_path_hexes(start: Position, end: Position) -> List[Position]:
    """
    Get all hexes along the path from start to end.
    Uses line-drawing algorithm for hex grids.
    """
    path = [start]
    
    if start == end:
        return path
    
    dx = end.x - start.x
    dy = end.y - start.y
    
    # Determine number of steps
    steps = max(abs(dx), abs(dy), abs(dx + dy))
    
    # Generate intermediate positions
    for i in range(1, steps + 1):
        t = i / steps
        x = round(start.x + dx * t)
        y = round(start.y + dy * t)
        pos = Position(x, y)
        if pos not in path:
            path.append(pos)
    
    return path


def check_collision(path: List[Position], features: List[MapFeature]) -> Tuple[bool, str]:
    """
    Check if path intersects any astral bodies.
    Returns (crashed, reason)
    """
    planets = [f for f in features if f.feature_type == FeatureType.PLANET]
    asteroids = [f for f in features if f.feature_type == FeatureType.ASTEROID]
    boundaries = [
        f for f in features if f.feature_type == FeatureType.MAP_BOUNDARY]
    
    # Check planet collisions (must hit exact position)
    for pos in path:
        for planet in planets:
            if pos == planet.position:
                return True, f"Crashed into {planet.name}"
    
    # Check asteroid collisions (must hit exact position, speed > 1 causes damage roll)
    for pos in path[1:]:  # Skip starting position
        for asteroid in asteroids:
            if pos == asteroid.position:
                return True, f"Crashed into asteroid {asteroid.name}"
    
    # Check map boundary
    final_pos = path[-1]
    for boundary in boundaries:
        if final_pos == boundary.position:
            return True, "Off map"
    
    return False, ""


def get_gravity_effects(path: List[Position], features: List[MapFeature]) -> Tuple[List[Vector], List[Vector]]:
    """
    Determine gravity effects for next turn based on hexes entered this turn.
    Returns (strong_gravity_vectors, weak_gravity_vectors)
    
    Rules:
    - Gravity takes effect on the turn AFTER entering the hex
    - First weak gravity hex can be ignored, subsequent ones cannot
    """
    strong_gravity = []
    weak_gravity = []
    
    # Get all gravity hexes along the path (excluding start position)
    for pos in path[1:]:
        for feature in features:
            if pos == feature.position:
                if feature.feature_type == FeatureType.STRONG_GRAVITY:
                    strong_gravity.append(feature.gravity_direction)
                elif feature.feature_type == FeatureType.WEAK_GRAVITY:
                    weak_gravity.append(feature.gravity_direction)
    
    return strong_gravity, weak_gravity


def execute_movement_phase(
        ships: List[Ship], features: List[MapFeature]) -> List[Movement]:
    """
    Execute the movement phase for all ships.
    
    From rules p.2-3:
    1. Ships move along plotted courses (predicted course + acceleration)
    2. Gravity from LAST turn affects this turn's movement
    3. Gravity entered THIS turn affects NEXT turn
    4. Check for crashes against astral bodies
    """
    results = []
    
    for ship in ships:
        # Calculate final position for this turn
        final_position = calculate_actual_endpoint(ship)
        
        # Get path from start to end
        path = get_path_hexes(ship.position, final_position)
        
        # Check for collisions
        crashed, crash_reason = check_collision(path, features)
        
        # Calculate new vector (from start to end position)
        new_vector = final_position - ship.position
        
        # Determine gravity effects for NEXT turn from hexes entered THIS turn
        strong_gravity_next, weak_gravity_next = get_gravity_effects(path, features)
        
        result = Movement(
            new_position=final_position,
            new_vector=new_vector,
            strong_gravity_next_turn=strong_gravity_next,
            weak_gravity_options_next_turn=weak_gravity_next,
            path=path,
            crashed=crashed,
            crash_reason=crash_reason,
            off_map=crash_reason == "Off map"
        )
        
        results.append(result)
    
    return results


# Example usage and test
if __name__ == "__main__":
    # Example: Ship moving near a planet with gravity
    
    # Create a ship at position (0, 0) moving to (3, 0)
    ship1 = Ship(
        name="Corvette Alpha",
        position=Position(0, 0),
        vector=Vector(3, 0),  # Moved 3 hexes right last turn
        acceleration=Vector(0, 0),  # Not burning fuel this turn
        strong_gravity_last_turn=[],  # No gravity from last turn
        chosen_weak_gravity_last_turn=[]
    )
    
    # Create map features
    features = [
        MapFeature("Venus", FeatureType.PLANET, Position(5, 0)),
        MapFeature("Venus Gravity 1", FeatureType.STRONG_GRAVITY, 
                   Position(4, 0), Vector(1, 0)),  # Pulls right toward planet
        MapFeature("Venus Gravity 2", FeatureType.STRONG_GRAVITY,
                   Position(4, -1), Vector(0, 1)),  # Pulls down toward planet
    ]
    
    # Execute movement
    results = execute_movement_phase([ship1], features)
    
    print("Movement Phase Results:")
    print("=" * 60)
    for result in results:
        print(f"\nShip: {result.name}")
        print(f"  New Position: {result.new_position}")
        print(f"  New Vector: {result.new_vector}")
        print(f"  Path: {' -> '.join(str(p) for p in result.path)}")
        print(f"  Strong Gravity for Next Turn: {result.strong_gravity_next_turn}")
        print(f"  Weak Gravity Options for Next Turn: {result.weak_gravity_options_next_turn}")
        if result.crashed:
            print(f"  ** CRASHED: {result.crash_reason} **")
    
    # Example 2: Ship with gravity from last turn
    print("\n" + "=" * 60)
    print("Example 2: Ship affected by gravity from last turn")
    print("=" * 60)
    
    ship2 = Ship(
        name="Corsair Beta",
        position=Position(0, 0),
        vector=Vector(2, 1),  # Base vector
        acceleration=Vector(0, 0),
        strong_gravity_last_turn=[Vector(1, 0), Vector(0, 1)],  # Two gravity hexes from last turn
        chosen_weak_gravity_last_turn=[]
    )
    
    results2 = execute_movement_phase([ship2], features)
    
    for result in results2:
        print(f"\nShip: {result.name}")
        print(f"  Base Vector: (2, 1)")
        print(f"  Gravity from Last Turn: (1, 0) + (0, 1)")
        print(f"  Predicted Endpoint without Gravity: Pos(2, 1)")
        print(f"  Actual Endpoint with Gravity: {result.new_position}")
        print(f"  New Vector: {result.new_vector}")

