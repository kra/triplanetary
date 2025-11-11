"""
Triplanetary Movement Phase Implementation

Based on the rules from pages 2-4:
- Vector movement: ships continue in same direction/distance unless accelerated
- One fuel point allows changing endpoint by one hex
- Gravity hexes affect movement on the turn AFTER entering them
- Weak gravity can be ignored or used (first hex), subsequent weak gravity acts as full
- Crashes occur when vector intersects astral body outline
- Landing and takeoff from bases (page 4)
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum


class FeatureType(Enum):
    PLANET = "planet"
    ASTEROID = "asteroid"
    STRONG_GRAVITY = "strong_gravity"
    WEAK_GRAVITY = "weak_gravity"
    MAP_BOUNDARY = "map_boundary"
    BASE = "base"


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
    landed: bool = False  # True if this position is on a planetary surface
    
    def __add__(self, vector: Vector):
        return Position(self.x + vector.dx, self.y + vector.dy, self.landed)
    
    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y)
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.landed == other.landed
    
    def __hash__(self):
        return hash((self.x, self.y, self.landed))
    
    def __repr__(self):
        landed_str = " [LANDED]" if self.landed else ""
        return f"Pos({self.x}, {self.y}){landed_str}"


@dataclass
class MapFeature:
    """Static map feature"""
    name: str
    feature_type: FeatureType
    position: Position
    gravity_direction: Optional[Vector] = None  # For gravity hexes
    planet_name: Optional[str] = None  # For bases - which planet they're on


@dataclass
class Ship:
    """Ship or ordnance in play"""
    name: str
    starting_position: Position


@dataclass
class Action:
    """Player's action for a ship on a turn"""
    acceleration: Vector  # Fuel burn this turn (0 or 1 hex change)
    chosen_weak_gravity: List[Vector]  # Weak gravity chosen this turn
    landing: bool = False  # True if attempting to land this turn
    taking_off: bool = False  # True if taking off this turn


@dataclass
class Turn:
    """Result of movement for one ship"""
    ship_name: str
    action: Action  # Player's action this turn
    start_position: Position
    start_vector: Vector  # Last turn's movement (input to this turn)
    start_strong_gravity: List[Vector]  # Strong gravity from hexes entered last turn
    new_position: Position
    new_vector: Vector  # This turn's movement (output from this turn)
    new_strong_gravity: List[Vector]  # Strong gravity for next turn
    new_weak_gravity_options: List[Vector]  # Weak gravity options for next turn
    path: List[Position]  # Hexes traversed during movement
    crashed: bool = False
    crash_reason: str = ""
    off_map: bool = False
    in_orbit: bool = False  # True if ship is in valid orbit


def is_in_orbit(position: Position, vector: Vector, features: List[MapFeature]) -> bool:
    """
    Check if ship is in a valid orbit.
    A ship is in orbit if it's moving at 1 hex per turn between adjacent gravity hexes
    of the same body.
    """
    if vector.length() != 1:
        return False
    
    # Check if current position is a gravity hex
    current_gravity = None
    for feature in features:
        if feature.position == position and feature.feature_type in [FeatureType.STRONG_GRAVITY, FeatureType.WEAK_GRAVITY]:
            current_gravity = feature
            break
    
    if current_gravity is None:
        return False
    
    # Check if destination is also a gravity hex of the same planet
    next_position = position + vector
    for feature in features:
        if feature.position == next_position and feature.feature_type in [FeatureType.STRONG_GRAVITY, FeatureType.WEAK_GRAVITY]:
            # Check if it's the same planet (simple name matching for now)
            if feature.planet_name and current_gravity.planet_name:
                if feature.planet_name == current_gravity.planet_name:
                    return True
    
    return False


def get_base_at_position(position: Position, features: List[MapFeature]) -> Optional[MapFeature]:
    """Find base at the given position"""
    for feature in features:
        if feature.feature_type == FeatureType.BASE and feature.position == position:
            return feature
    return None


def calculate_predicted_endpoint(
    start_position: Position, 
    start_vector: Vector,
    start_strong_gravity: List[Vector],
    start_chosen_weak_gravity: List[Vector]
) -> Position:
    """
    Calculate where ship would end up with no acceleration.
    This is the base vector plus accumulated gravity from last turn.
    """
    # Start with the ship's base vector (repeat last turn's movement)
    total_movement = Vector(start_vector.dx, start_vector.dy)
    
    # Apply strong gravity from last turn (mandatory and cumulative)
    for gravity in start_strong_gravity:
        total_movement = total_movement + gravity
    
    # Apply chosen weak gravity from last turn
    for gravity in start_chosen_weak_gravity:
        total_movement = total_movement + gravity
    
    result_pos = start_position + total_movement
    result_pos.landed = start_position.landed  # Preserve landed status
    return result_pos


def calculate_actual_endpoint(
    start_position: Position, 
    start_vector: Vector,
    start_strong_gravity: List[Vector],
    start_chosen_weak_gravity: List[Vector],
    acceleration: Vector
) -> Position:
    """
    Calculate actual endpoint including fuel burn.
    Fuel burn allows changing endpoint by one hex in any direction.
    """
    predicted = calculate_predicted_endpoint(
        start_position, start_vector, start_strong_gravity, start_chosen_weak_gravity
    )
    result = predicted + acceleration
    result.landed = predicted.landed  # Preserve landed status
    return result


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
    ships: List[Ship], 
    positions: List[Position], 
    start_vectors: List[Vector],
    start_strong_gravity_list: List[List[Vector]],
    actions: List[Action],
    features: List[MapFeature]
) -> List[Turn]:
    """
    Execute the movement phase for all ships.
    
    From rules p.2-3:
    1. Ships move along plotted courses (predicted course + acceleration)
    2. Gravity from LAST turn affects this turn's movement
    3. Gravity entered THIS turn affects NEXT turn
    4. Check for crashes against astral bodies
    
    From rules p.4 (Landing and Takeoff):
    1. Ships can land at bases if in orbit by expending 1 fuel point
    2. Ships take off using boosters (free 1 hex acceleration)
    3. Must land from orbit; must take off from where landed
    
    Args:
        ships: List of ships to move
        positions: Starting position for each ship (parallel to ships list)
        start_vectors: Last turn's movement for each ship (parallel to ships list)
        start_strong_gravity_list: Strong gravity from last turn for each ship
        actions: Player actions this turn for each ship (parallel to ships list)
        features: Map features (planets, gravity, etc.)
    """
    results = []
    
    for ship, start_position, prev_vector, start_strong_grav, action in zip(
        ships, positions, start_vectors, start_strong_gravity_list, actions
    ):
        # Handle takeoff
        if action.taking_off:
            if not start_position.landed:
                # Can't take off if not landed
                result = Turn(
                    ship_name=ship.name,
                    action=action,
                    start_position=start_position,
                    start_vector=prev_vector,
                    start_strong_gravity=start_strong_grav,
                    new_position=start_position,
                    new_vector=Vector(0, 0),
                    new_strong_gravity=[],
                    new_weak_gravity_options=[],
                    path=[start_position],
                    crashed=True,
                    crash_reason="Cannot take off - not landed at base"
                )
                results.append(result)
                continue
            
            # Check acceleration length BEFORE checking for base
            # This ensures we validate the action parameters first
            booster_accel = action.acceleration
            if booster_accel.length() > 1:
                result = Turn(
                    ship_name=ship.name,
                    action=action,
                    start_position=start_position,
                    start_vector=prev_vector,
                    start_strong_gravity=start_strong_grav,
                    new_position=start_position,
                    new_vector=Vector(0, 0),
                    new_strong_gravity=[],
                    new_weak_gravity_options=[],
                    path=[start_position],
                    crashed=True,
                    crash_reason="Takeoff acceleration too large (max 1 hex)"
                )
                results.append(result)
                continue
            
            # Check if there's a base at this position
            base = get_base_at_position(start_position, features)
            if base is None:
                result = Turn(
                    ship_name=ship.name,
                    action=action,
                    start_position=start_position,
                    start_vector=prev_vector,
                    start_strong_gravity=start_strong_grav,
                    new_position=start_position,
                    new_vector=Vector(0, 0),
                    new_strong_gravity=[],
                    new_weak_gravity_options=[],
                    path=[start_position],
                    crashed=True,
                    crash_reason="Cannot take off - no base at position"
                )
                results.append(result)
                continue
            
            # Takeoff: free booster gives 1 hex acceleration
            # The booster moves ship to adjacent gravity hex
            # Acceleration in action adds to the booster movement
            
            # Ship moves to adjacent hex (the gravity hex above the base)
            final_position = Position(
                start_position.x + booster_accel.dx,
                start_position.y + booster_accel.dy,
                landed=False  # No longer landed
            )
            
            # Path is just start to end
            path = get_path_hexes(start_position, final_position)
            
            # New vector from takeoff
            new_vector = booster_accel
            
            # Gravity cancels the takeoff velocity, leaving ship stationary
            # So we collect gravity but the ship ends up with zero effective vector
            strong_gravity_next, weak_gravity_next = get_gravity_effects(path, features)
            
            result = Turn(
                ship_name=ship.name,
                action=action,
                start_position=start_position,
                start_vector=prev_vector,
                start_strong_gravity=start_strong_grav,
                new_position=final_position,
                new_vector=new_vector,
                new_strong_gravity=strong_gravity_next,
                new_weak_gravity_options=weak_gravity_next,
                path=path,
                crashed=False,
                in_orbit=False  # Just took off, not yet in stable orbit
            )
            results.append(result)
            continue
        
        # Handle landing attempt
        if action.landing:
            # Must be in orbit to land
            in_orbit = is_in_orbit(start_position, prev_vector, features)
            if not in_orbit:
                result = Turn(
                    ship_name=ship.name,
                    action=action,
                    start_position=start_position,
                    start_vector=prev_vector,
                    start_strong_gravity=start_strong_grav,
                    new_position=start_position,
                    new_vector=Vector(0, 0),
                    new_strong_gravity=[],
                    new_weak_gravity_options=[],
                    path=[start_position],
                    crashed=True,
                    crash_reason="Cannot land - not in orbit"
                )
                results.append(result)
                continue
            
            # Landing requires expending 1 fuel point (acceleration must be length 1)
            if action.acceleration.length() != 1:
                result = Turn(
                    ship_name=ship.name,
                    action=action,
                    start_position=start_position,
                    start_vector=prev_vector,
                    start_strong_gravity=start_strong_grav,
                    new_position=start_position,
                    new_vector=Vector(0, 0),
                    new_strong_gravity=[],
                    new_weak_gravity_options=[],
                    path=[start_position],
                    crashed=True,
                    crash_reason="Landing requires expending exactly 1 fuel point"
                )
                results.append(result)
                continue
            
            # Calculate landing position (includes the acceleration)
            final_position = calculate_actual_endpoint(
                start_position, prev_vector, start_strong_grav, 
                action.chosen_weak_gravity, action.acceleration
            )
            
            # Check if there's a base at the landing position
            base = get_base_at_position(final_position, features)
            if base is None:
                result = Turn(
                    ship_name=ship.name,
                    action=action,
                    start_position=start_position,
                    start_vector=prev_vector,
                    start_strong_gravity=start_strong_grav,
                    new_position=final_position,
                    new_vector=Vector(0, 0),
                    new_strong_gravity=[],
                    new_weak_gravity_options=[],
                    path=[start_position, final_position],
                    crashed=True,
                    crash_reason="Cannot land - no base at destination"
                )
                results.append(result)
                continue
            
            # Successful landing
            final_position.landed = True
            
            result = Turn(
                ship_name=ship.name,
                action=action,
                start_position=start_position,
                start_vector=prev_vector,
                start_strong_gravity=start_strong_grav,
                new_position=final_position,
                new_vector=Vector(0, 0),  # Ship is now stationary on surface
                new_strong_gravity=[],
                new_weak_gravity_options=[],
                path=[start_position, final_position],
                crashed=False,
                in_orbit=False
            )
            results.append(result)
            continue
        
        # Normal movement (not landing or taking off)
        if start_position.landed:
            # Ship is landed - cannot move without taking off
            result = Turn(
                ship_name=ship.name,
                action=action,
                start_position=start_position,
                start_vector=prev_vector,
                start_strong_gravity=start_strong_grav,
                new_position=start_position,
                new_vector=Vector(0, 0),
                new_strong_gravity=[],
                new_weak_gravity_options=[],
                path=[start_position],
                crashed=True,
                crash_reason="Ship is landed - must take off first"
            )
            results.append(result)
            continue
        
        # Calculate final position for this turn
        final_position = calculate_actual_endpoint(
            start_position, prev_vector, start_strong_grav, 
            action.chosen_weak_gravity, action.acceleration
        )
        
        # Get path from start to end
        path = get_path_hexes(start_position, final_position)
        
        # Check for collisions
        crashed, crash_reason = check_collision(path, features)
        
        # Calculate new vector (from start to end position)
        new_vector = final_position - start_position
        
        # Determine gravity effects for NEXT turn from hexes entered THIS turn
        strong_gravity_next, weak_gravity_next = get_gravity_effects(path, features)
        
        # Check if in orbit
        in_orbit = is_in_orbit(final_position, new_vector, features)
        
        result = Turn(
            ship_name=ship.name,
            action=action,
            start_position=start_position,
            start_vector=prev_vector,
            start_strong_gravity=start_strong_grav,
            new_position=final_position,
            new_vector=new_vector,
            new_strong_gravity=strong_gravity_next,
            new_weak_gravity_options=weak_gravity_next,
            path=path,
            crashed=crashed,
            crash_reason=crash_reason,
            off_map=crash_reason == "Off map",
            in_orbit=in_orbit
        )
        
        results.append(result)
    
    return results


@dataclass
class Game:
    """Game state containing ships, map features, and turn history"""
    map_features: List[MapFeature] = field(default_factory=list)
    ships: List[Ship] = field(default_factory=list)
    turns: List[Turn] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate that all ship names are unique"""
        ship_names = [ship.name for ship in self.ships]
        if len(ship_names) != len(set(ship_names)):
            raise ValueError("All ships must have unique names")
    
    def add_ship(self, ship: Ship):
        """Add a ship to the game"""
        if any(s.name == ship.name for s in self.ships):
            raise ValueError(f"Ship with name '{ship.name}' already exists")
        self.ships.append(ship)
    
    def get_ship(self, ship_name: str) -> Optional[Ship]:
        """Get ship by name"""
        for ship in self.ships:
            if ship.name == ship_name:
                return ship
        return None
    
    def get_last_turn(self, ship_name: str) -> Optional[Turn]:
        """Get the most recent turn for a ship"""
        for turn in reversed(self.turns):
            if turn.ship_name == ship_name:
                return turn
        return None
    
    def add_turn(self, ship_name: str, action: Action):
        """
        Construct a new Turn for ship from action and that ship's previous Turn,
        and add it to my turns.
        """
        # Find the ship
        ship = self.get_ship(ship_name)
        if ship is None:
            raise ValueError(f"Ship '{ship_name}' not found in game")
        
        # Get previous turn to extract state
        prev_turn = self.get_last_turn(ship_name)
        
        if prev_turn is None:
            # First turn for this ship - starts at starting position with zero vector
            start_position = ship.starting_position
            start_vector = Vector(0, 0)
            start_strong_gravity = []
        else:
            # Use previous turn's ending state as this turn's starting state
            start_position = prev_turn.new_position
            start_vector = prev_turn.new_vector
            start_strong_gravity = prev_turn.new_strong_gravity
        
        # Execute movement for this single ship
        results = execute_movement_phase(
            [ship],
            [start_position],
            [start_vector],
            [start_strong_gravity],
            [action],
            self.map_features
        )
        
        # Add the resulting turn to our history
        self.turns.append(results[0])


# Example usage and test
if __name__ == "__main__":
    # Example: Ship landing and taking off from Mars
    
    # Create a game
    game = Game()
    
    # Add map features - Mars with gravity hexes and a base
    game.map_features = [
        MapFeature("Mars", FeatureType.PLANET, Position(10, 10)),
        MapFeature("Mars Gravity 1", FeatureType.STRONG_GRAVITY, 
                   Position(10, 9), Vector(0, 1), planet_name="Mars"),  # Above Mars
        MapFeature("Mars Gravity 2", FeatureType.STRONG_GRAVITY,
                   Position(9, 9), Vector(1, 1), planet_name="Mars"),  # Adjacent
        MapFeature("Mars Base", FeatureType.BASE, Position(10, 10), planet_name="Mars"),
    ]
    
    # Add ship starting in orbit
    ship1 = Ship(name="Lander One", starting_position=Position(10, 9))
    game.add_ship(ship1)
    
    # Turn 1: Ship is in orbit, moving between gravity hexes
    print("Turn 1: Ship establishes orbit")
    print("=" * 60)
    action1 = Action(acceleration=Vector(-1, 0), chosen_weak_gravity=[])
    game.add_turn("Lander One", action1)
    
    turn1 = game.turns[-1]
    print(f"Ship: {turn1.ship_name}")
    print(f"  Position: {turn1.start_position} -> {turn1.new_position}")
    print(f"  In Orbit: {turn1.in_orbit}")
    
    # Turn 2: Ship attempts to land
    print("\nTurn 2: Ship attempts landing")
    print("=" * 60)
    action2 = Action(acceleration=Vector(1, 1), chosen_weak_gravity=[], landing=True)
    game.add_turn("Lander One", action2)
    
    turn2 = game.turns[-1]
    print(f"Ship: {turn2.ship_name}")
    print(f"  Position: {turn2.start_position} -> {turn2.new_position}")
    print(f"  Landed: {turn2.new_position.landed}")
    print(f"  Crashed: {turn2.crashed}")
    if turn2.crash_reason:
        print(f"  Reason: {turn2.crash_reason}")
    
    # Turn 3: Ship takes off
    print("\nTurn 3: Ship takes off")
    print("=" * 60)
    action3 = Action(acceleration=Vector(0, -1), chosen_weak_gravity=[], taking_off=True)
    game.add_turn("Lander One", action3)
    
    turn3 = game.turns[-1]
    print(f"Ship: {turn3.ship_name}")
    print(f"  Position: {turn3.start_position} -> {turn3.new_position}")
    print(f"  Landed: {turn3.start_position.landed} -> {turn3.new_position.landed}")
    print(f"  New Vector: {turn3.new_vector}")
