"""
Unit tests for geometry helper functions
"""
import pytest
import math
from utils.geometry import haversine_distance, bearing_between, elevation_angle, is_plane_approaching


class TestHaversineDistance:
    """Test cases for haversine_distance function"""
    
    def test_same_location(self):
        """Distance between same points should be 0"""
        distance = haversine_distance(51.5074, -0.1278, 51.5074, -0.1278)
        assert distance == 0
    
    def test_known_distance(self):
        """Test with known distance between London and Paris (approx 344 km)"""
        # London: 51.5074° N, 0.1278° W
        # Paris: 48.8566° N, 2.3522° E
        distance = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
        assert 340 < distance < 350  # Allow for small calculation differences
    
    def test_equator_distance(self):
        """Test distance along equator (should be approx 111 km per degree)"""
        distance = haversine_distance(0, 0, 0, 1)
        assert 110 < distance < 112
    
    def test_pole_to_pole(self):
        """Test distance from North to South pole (approx 20,000 km)"""
        distance = haversine_distance(90, 0, -90, 0)
        assert 19900 < distance < 20100


class TestBearingBetween:
    """Test cases for bearing_between function"""
    
    def test_north_bearing(self):
        """Bearing should be 0° when destination is due north"""
        bearing = bearing_between(0, 0, 1, 0)
        assert -1 < bearing < 1  # Allow for floating point errors
    
    def test_east_bearing(self):
        """Bearing should be 90° when destination is due east"""
        bearing = bearing_between(0, 0, 0, 1)
        assert 89 < bearing < 91
    
    def test_south_bearing(self):
        """Bearing should be 180° when destination is due south"""
        bearing = bearing_between(1, 0, 0, 0)
        assert 179 < bearing < 181
    
    def test_west_bearing(self):
        """Bearing should be 270° when destination is due west"""
        bearing = bearing_between(0, 1, 0, 0)
        assert 269 < bearing < 271
    
    def test_bearing_range(self):
        """Bearing should always be between 0 and 360 degrees"""
        test_coords = [
            (51.5, -0.1, 48.8, 2.3),
            (40.7, -74.0, 51.5, -0.1),
            (-33.9, 18.4, 55.7, 12.6),
            (35.7, 139.7, -37.8, 144.9)
        ]
        for lat1, lon1, lat2, lon2 in test_coords:
            bearing = bearing_between(lat1, lon1, lat2, lon2)
            assert 0 <= bearing < 360


class TestElevationAngle:
    """Test cases for elevation_angle function"""
    
    def test_zero_altitude(self):
        """Elevation angle should be 0 when altitude is 0"""
        angle = elevation_angle(10, 0)
        assert angle == 0
    
    def test_directly_overhead(self):
        """Elevation angle should be 90° when distance is 0"""
        angle = elevation_angle(0, 10000)
        assert angle == 90
    
    def test_45_degree_angle(self):
        """Elevation angle should be 45° when altitude equals distance"""
        # 10 km altitude, 10 km distance
        angle = elevation_angle(10, 10000)
        assert 44.9 < angle < 45.1
    
    def test_typical_scenario(self):
        """Test typical aircraft scenario (30,000 ft at 50 km distance)"""
        # 30,000 ft ≈ 9,144 m
        angle = elevation_angle(50, 9144)
        expected = math.degrees(math.atan(9.144 / 50))
        assert abs(angle - expected) < 0.1
    
    def test_negative_values(self):
        """Test that negative values don't raise errors but return reasonable results"""
        # Negative distance doesn't make physical sense but function handles it
        angle = elevation_angle(10, -5000)
        assert angle < 0  # Negative altitude gives negative angle
        
        # Zero altitude should give zero angle
        angle = elevation_angle(10, 0)
        assert angle == 0


class TestIsPlaneApproaching:
    """Test cases for is_plane_approaching function"""
    
    def test_direct_approach(self):
        """Plane flying directly towards observer"""
        # Plane is north of us (home_bearing=0), plane sees us south (plane_bearing=180)
        # Plane flying south (true_track=180) towards us
        is_approaching = is_plane_approaching(0, 180, 180)
        assert is_approaching is True
    
    def test_flying_away(self):
        """Plane flying directly away from observer"""
        # Plane is north of us (home_bearing=0), plane sees us south (plane_bearing=180)
        # Plane flying north (true_track=0) away from us
        is_approaching = is_plane_approaching(0, 180, 0)
        assert is_approaching is False
    
    def test_perpendicular_flight(self):
        """Plane flying perpendicular to observer"""
        # Plane is north of us (home_bearing=0), plane sees us south (plane_bearing=180)
        # Plane flying east (true_track=90) perpendicular to us
        is_approaching = is_plane_approaching(0, 180, 90)
        assert is_approaching is False
    
    def test_approaching_at_angle(self):
        """Plane approaching at various angles"""
        # Test cases: (home_bearing, plane_bearing, true_track, expected)
        test_cases = [
            # Plane north of us, flying roughly south (approaching)
            (0, 180, 150, True),    # 30° off direct approach
            (0, 180, 210, True),    # 30° off from other side
            # Plane northeast, flying southwest (approaching)
            (45, 225, 225, True),   # Direct approach at 45° bearing
            # Plane east, flying west (approaching)
            (90, 270, 270, True),   # Direct approach from east
            # Plane north of us, flying away
            (0, 180, 45, False),    # Flying northeast (away)
            (0, 180, 315, False),   # Flying northwest (away)
        ]
        
        for home_bearing, plane_bearing, track, expected in test_cases:
            result = is_plane_approaching(home_bearing, plane_bearing, track)
            assert result == expected, f"Failed for home_bearing={home_bearing}, plane_bearing={plane_bearing}, track={track}"
    
    def test_wraparound_cases(self):
        """Test cases where angles wrap around 0/360"""
        # Test cases: (home_bearing, plane_bearing, true_track, expected)
        test_cases = [
            # Plane just west of north, we're just east of south, flying towards us
            (350, 170, 170, True),   # Approaching across 0°
            # Plane just east of north, we're just west of south, flying towards us  
            (10, 190, 190, True),    # Approaching across 0°
            # Testing other wraparound scenarios
            (170, 350, 350, True),   # Approaching across 180°
            (190, 10, 10, True),     # Approaching across 180°
        ]
        
        for home_bearing, plane_bearing, track, expected in test_cases:
            result = is_plane_approaching(home_bearing, plane_bearing, track)
            assert result == expected, f"Failed for home_bearing={home_bearing}, plane_bearing={plane_bearing}, track={track}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])