import pytest

from chalicelib import game


class TestVector:
    """Tests for game.Vector class"""
    
    def test_vector_addition(self):
        v1 = game.Vector(1, 2)
        v2 = game.Vector(3, 4)
        result = v1 + v2
        assert result.dx == 4
        assert result.dy == 6
    
    def test_vector_length_simple(self):
        v = game.Vector(3, 0)
        assert v.length() == 3
    
    def test_vector_length_diagonal(self):
        v = game.Vector(2, 2)
        # For hex grids: (|dx| + |dy| + |dx+dy|) / 2
        # (2 + 2 + 4) / 2 = 4
        assert v.length() == 4
    
    def test_vector_zero_length(self):
        v = game.Vector(0, 0)
        assert v.length() == 0


class TestPosition:
    """Tests for game.Position class"""
    
    def test_position_add_vector(self):
        pos = game.Position(5, 10)
        vec = game.Vector(2, 3)
        result = pos + vec
        assert result.x == 7
        assert result.y == 13
    
    def test_position_subtract_position(self):
        pos1 = game.Position(10, 5)
        pos2 = game.Position(3, 2)
        result = pos1 - pos2
        assert result.dx == 7
        assert result.dy == 3
    
    def test_position_equality(self):
        pos1 = game.Position(5, 5)
        pos2 = game.Position(5, 5)
        pos3 = game.Position(5, 6)
        assert pos1 == pos2
        assert pos1 != pos3


class TestBasicMovement:
    """Tests for basic movement without complications"""
    
    def test_stationary_ship(self):
        """game.Ship with zero vector stays put"""
        ship = game.Ship(
            name="Stationary",
            position=game.Position(5, 5),
            vector=game.Vector(0, 0),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[],
            chosen_weak_gravity_last_turn=[]
        )
        
        predicted = game.calculate_predicted_endpoint(ship)
        assert predicted == game.Position(5, 5)
    
    def test_simple_movement_no_acceleration(self):
        """game.Ship continues in same direction - basic rule"""
        ship = game.Ship(
            name="Cruiser",
            position=game.Position(0, 0),
            vector=game.Vector(3, 0),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[],
            chosen_weak_gravity_last_turn=[]
        )
        
        predicted = game.calculate_predicted_endpoint(ship)
        assert predicted == game.Position(3, 0)
        
        actual = game.calculate_actual_endpoint(ship)
        assert actual == game.Position(3, 0)
    
    def test_movement_with_acceleration(self):
        """game.Ship burns fuel to change course by one hex"""
        ship = game.Ship(
            name="Corvette",
            position=game.Position(0, 0),
            vector=game.Vector(3, 0),
            acceleration=game.Vector(0, 1),  # Burn fuel to move up one hex
            strong_gravity_last_turn=[],
            chosen_weak_gravity_last_turn=[]
        )
        
        predicted = game.calculate_predicted_endpoint(ship)
        assert predicted == game.Position(3, 0)
        
        actual = game.calculate_actual_endpoint(ship)
        assert actual == game.Position(3, 1)
    
    def test_diagonal_movement(self):
        """game.Ship moving diagonally"""
        ship = game.Ship(
            name="Frigate",
            position=game.Position(5, 5),
            vector=game.Vector(2, 2),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[],
            chosen_weak_gravity_last_turn=[]
        )
        
        actual = game.calculate_actual_endpoint(ship)
        assert actual == game.Position(7, 7)


class TestGravityEffects:
    """Tests for gravity affecting movement"""
    
    def test_strong_gravity_single_hex(self):
        """game.Ship affected by one gravity hex from last turn"""
        ship = game.Ship(
            name="Transport",
            position=game.Position(0, 0),
            vector=game.Vector(2, 0),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[game.Vector(1, 0)],  # Pulled right
            chosen_weak_gravity_last_turn=[]
        )
        
        predicted = game.calculate_predicted_endpoint(ship)
        assert predicted == game.Position(3, 0)  # 2 + 1 from gravity
    
    def test_strong_gravity_cumulative(self):
        """Multiple gravity hexes accumulate (p. 3)"""
        ship = game.Ship(
            name="Corsair",
            position=game.Position(0, 0),
            vector=game.Vector(2, 1),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[game.Vector(1, 0), game.Vector(0, 1)],
            chosen_weak_gravity_last_turn=[]
        )
        
        predicted = game.calculate_predicted_endpoint(ship)
        # Base (2,1) + gravity (1,0) + gravity (0,1) = (3,2)
        assert predicted == game.Position(3, 2)
    
    def test_weak_gravity_chosen(self):
        """Weak gravity that was chosen last turn"""
        ship = game.Ship(
            name="Packet",
            position=game.Position(0, 0),
            vector=game.Vector(3, 0),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[],
            chosen_weak_gravity_last_turn=[game.Vector(0, 1)]
        )
        
        predicted = game.calculate_predicted_endpoint(ship)
        assert predicted == game.Position(3, 1)
    
    def test_gravity_with_acceleration(self):
        """Gravity and fuel burn both affect movement"""
        ship = game.Ship(
            name="Dreadnaught",
            position=game.Position(0, 0),
            vector=game.Vector(2, 0),
            acceleration=game.Vector(1, 1),  # Burn fuel
            strong_gravity_last_turn=[game.Vector(0, 1)],  # Gravity from last turn
            chosen_weak_gravity_last_turn=[]
        )
        
        predicted = game.calculate_predicted_endpoint(ship)
        assert predicted == game.Position(2, 1)  # Base + gravity
        
        actual = game.calculate_actual_endpoint(ship)
        assert actual == game.Position(3, 2)  # Predicted + acceleration


class TestPathCalculation:
    """Tests for hex path calculation"""
    
    def test_path_same_position(self):
        """Path from position to itself"""
        path = game.get_path_hexes(game.Position(5, 5), game.Position(5, 5))
        assert len(path) == 1
        assert path[0] == game.Position(5, 5)
    
    def test_path_horizontal(self):
        """Horizontal movement"""
        path = game.get_path_hexes(game.Position(0, 0), game.Position(3, 0))
        assert len(path) == 4
        assert path[0] == game.Position(0, 0)
        assert path[-1] == game.Position(3, 0)
    
    def test_path_vertical(self):
        """Vertical movement"""
        path = game.get_path_hexes(game.Position(0, 0), game.Position(0, 3))
        assert len(path) == 4
        assert path[0] == game.Position(0, 0)
        assert path[-1] == game.Position(0, 3)
    
    def test_path_diagonal(self):
        """Diagonal movement"""
        path = game.get_path_hexes(game.Position(0, 0), game.Position(2, 2))
        assert path[0] == game.Position(0, 0)
        assert path[-1] == game.Position(2, 2)
        assert len(path) >= 3


class TestCollisionDetection:
    """Tests for crash detection"""
    
    def test_no_collision_clear_space(self):
        """game.Ship moving through clear space"""
        path = [game.Position(0, 0), game.Position(1, 0), game.Position(2, 0)]
        features = [
            game.MapFeature("Mars", game.FeatureType.PLANET, game.Position(10, 10))
        ]
        
        crashed, reason = game.check_collision(path, features)
        assert not crashed
        assert reason == ""
    
    def test_collision_with_planet(self):
        """game.Ship crashes into planet"""
        path = [game.Position(0, 0), game.Position(1, 0), game.Position(2, 0)]
        features = [
            game.MapFeature("Venus", game.FeatureType.PLANET, game.Position(2, 0))
        ]
        
        crashed, reason = game.check_collision(path, features)
        assert crashed
        assert "Venus" in reason
    
    def test_collision_with_asteroid(self):
        """game.Ship crashes into asteroid"""
        path = [game.Position(0, 0), game.Position(1, 1), game.Position(2, 2)]
        features = [
            game.MapFeature("Asteroid A", game.FeatureType.ASTEROID, game.Position(1, 1))
        ]
        
        crashed, reason = game.check_collision(path, features)
        assert crashed
        assert "asteroid" in reason.lower()
    
    def test_near_miss_planet(self):
        """game.Ship passes near but not through planet"""
        path = [game.Position(0, 0), game.Position(1, 0), game.Position(2, 0)]
        features = [
            game.MapFeature("Mars", game.FeatureType.PLANET, game.Position(2, 1))
        ]
        
        crashed, reason = game.check_collision(path, features)
        assert not crashed
    
    def test_off_map(self):
        """game.Ship goes off map edge"""
        path = [game.Position(0, 0), game.Position(1, 0), game.Position(100, 0)]
        features = [
            game.MapFeature("Edge", game.FeatureType.MAP_BOUNDARY, game.Position(100, 0))
        ]
        
        crashed, reason = game.check_collision(path, features)
        assert crashed
        assert reason == "Off map"


class TestGravityDetection:
    """Tests for detecting gravity hexes entered"""
    
    def test_no_gravity_entered(self):
        """game.Ship moves through clear space"""
        path = [game.Position(0, 0), game.Position(1, 0), game.Position(2, 0)]
        features = [
            game.MapFeature("Grav1", game.FeatureType.STRONG_GRAVITY, 
                      game.Position(5, 5), game.Vector(1, 0))
        ]
        
        strong, weak = game.get_gravity_effects(path, features)
        assert len(strong) == 0
        assert len(weak) == 0
    
    def test_strong_gravity_entered(self):
        """game.Ship enters strong gravity hex"""
        path = [game.Position(0, 0), game.Position(1, 0), game.Position(2, 0)]
        features = [
            game.MapFeature("Venus Grav", game.FeatureType.STRONG_GRAVITY,
                      game.Position(1, 0), game.Vector(0, 1))
        ]
        
        strong, weak = game.get_gravity_effects(path, features)
        assert len(strong) == 1
        assert strong[0] == game.Vector(0, 1)
    
    def test_multiple_gravity_hexes(self):
        """game.Ship enters multiple gravity hexes"""
        path = [game.Position(0, 0), game.Position(1, 0), game.Position(2, 0), game.Position(3, 0)]
        features = [
            game.MapFeature("Grav1", game.FeatureType.STRONG_GRAVITY,
                      game.Position(1, 0), game.Vector(1, 0)),
            game.MapFeature("Grav2", game.FeatureType.STRONG_GRAVITY,
                      game.Position(2, 0), game.Vector(0, 1))
        ]
        
        strong, weak = game.get_gravity_effects(path, features)
        assert len(strong) == 2
        assert game.Vector(1, 0) in strong
        assert game.Vector(0, 1) in strong
    
    def test_weak_gravity_entered(self):
        """game.Ship enters weak gravity hex"""
        path = [game.Position(0, 0), game.Position(1, 0), game.Position(2, 0)]
        features = [
            game.MapFeature("Luna Grav", game.FeatureType.WEAK_GRAVITY,
                      game.Position(1, 0), game.Vector(0, 1))
        ]
        
        strong, weak = game.get_gravity_effects(path, features)
        assert len(strong) == 0
        assert len(weak) == 1
        assert weak[0] == game.Vector(0, 1)
    
    def test_starting_position_ignored(self):
        """Gravity at starting position doesn't count"""
        path = [game.Position(0, 0), game.Position(1, 0)]
        features = [
            game.MapFeature("Grav", game.FeatureType.STRONG_GRAVITY,
                      game.Position(0, 0), game.Vector(1, 0))
        ]
        
        strong, weak = game.get_gravity_effects(path, features)
        assert len(strong) == 0


class TestMovementPhaseIntegration:
    """Integration tests for complete movement phase"""
    
    def test_single_ship_simple_move(self):
        """Basic movement phase execution"""
        ship = game.Ship(
            name="Test game.Ship",
            position=game.Position(0, 0),
            vector=game.Vector(2, 0),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[],
            chosen_weak_gravity_last_turn=[]
        )
        
        results = game.execute_movement_phase([ship], [])
        
        assert len(results) == 1
        result = results[0]
        assert result.new_position == game.Position(2, 0)
        assert result.new_vector == game.Vector(2, 0)
        assert not result.crashed
    
    def test_ship_with_gravity_and_acceleration(self):
        """Complex move with gravity and fuel"""
        ship = game.Ship(
            name="Corvette",
            position=game.Position(0, 0),
            vector=game.Vector(2, 0),
            acceleration=game.Vector(1, 0),
            strong_gravity_last_turn=[game.Vector(0, 1)],
            chosen_weak_gravity_last_turn=[]
        )
        
        features = [
            game.MapFeature("Grav", game.FeatureType.STRONG_GRAVITY,
                      game.Position(3, 1), game.Vector(-1, 0))
        ]
        
        results = game.execute_movement_phase([ship], features)
        result = results[0]
        
        # Base (2,0) + gravity (0,1) + accel (1,0) = (3,1)
        assert result.new_position == game.Position(3, 1)
        assert len(result.strong_gravity_next_turn) == 1
    
    def test_multiple_ships(self):
        """Movement phase with multiple ships"""
        ships = [
            game.Ship("game.Ship1", game.Position(0, 0), game.Vector(1, 0), game.Vector(0, 0), [], []),
            game.Ship("game.Ship2", game.Position(5, 5), game.Vector(0, 1), game.Vector(0, 0), [], []),
        ]
        
        results = game.execute_movement_phase(ships, [])
        
        assert len(results) == 2
        assert results[0].new_position == game.Position(1, 0)
        assert results[1].new_position == game.Position(5, 6)
    
    def test_crash_detected(self):
        """Movement phase detects crash"""
        ship = game.Ship(
            name="Doomed",
            position=game.Position(0, 0),
            vector=game.Vector(3, 0),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[],
            chosen_weak_gravity_last_turn=[]
        )
        
        features = [
            game.MapFeature("Planet", game.FeatureType.PLANET, game.Position(3, 0))
        ]
        
        results = game.execute_movement_phase([ship], features)
        result = results[0]
        
        assert result.crashed
        assert "Planet" in result.crash_reason
    
    def test_gravity_for_next_turn(self):
        """Movement phase correctly identifies gravity for next turn"""
        ship = game.Ship(
            name="Explorer",
            position=game.Position(0, 0),
            vector=game.Vector(3, 0),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[],
            chosen_weak_gravity_last_turn=[]
        )
        
        features = [
            game.MapFeature("Strong1", game.FeatureType.STRONG_GRAVITY,
                      game.Position(1, 0), game.Vector(0, 1)),
            game.MapFeature("Weak1", game.FeatureType.WEAK_GRAVITY,
                      game.Position(2, 0), game.Vector(1, 0))
        ]
        
        results = game.execute_movement_phase([ship], features)
        result = results[0]
        
        assert len(result.strong_gravity_next_turn) == 1
        assert len(result.weak_gravity_options_next_turn) == 1
        assert result.strong_gravity_next_turn[0] == game.Vector(0, 1)
        assert result.weak_gravity_options_next_turn[0] == game.Vector(1, 0)


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""
    
    def test_zero_vector_zero_acceleration(self):
        """game.Ship perfectly stationary"""
        ship = game.Ship(
            name="Station",
            position=game.Position(10, 10),
            vector=game.Vector(0, 0),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[],
            chosen_weak_gravity_last_turn=[]
        )
        
        results = game.execute_movement_phase([ship], [])
        result = results[0]
        
        assert result.new_position == game.Position(10, 10)
        assert result.new_vector == game.Vector(0, 0)
    
    def test_large_vector(self):
        """game.Ship moving at high speed"""
        ship = game.Ship(
            name="Torch",
            position=game.Position(0, 0),
            vector=game.Vector(10, 10),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[],
            chosen_weak_gravity_last_turn=[]
        )
        
        results = game.execute_movement_phase([ship], [])
        result = results[0]
        
        assert result.new_position == game.Position(10, 10)
    
    def test_negative_coordinates(self):
        """game.Ship in negative coordinate space"""
        ship = game.Ship(
            name="Outbound",
            position=game.Position(-5, -5),
            vector=game.Vector(-2, -2),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[],
            chosen_weak_gravity_last_turn=[]
        )
        
        results = game.execute_movement_phase([ship], [])
        result = results[0]
        
        assert result.new_position == game.Position(-7, -7)
    
    def test_gravity_cancellation(self):
        """Opposite gravity vectors (should still accumulate)"""
        ship = game.Ship(
            name="Balanced",
            position=game.Position(0, 0),
            vector=game.Vector(2, 0),
            acceleration=game.Vector(0, 0),
            strong_gravity_last_turn=[game.Vector(1, 0), game.Vector(-1, 0)],
            chosen_weak_gravity_last_turn=[]
        )
        
        predicted = game.calculate_predicted_endpoint(ship)
        # Base (2,0) + (1,0) + (-1,0) = (2,0)
        assert predicted == game.Position(2, 0)
