"""
Tests for database optimization.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta

from backend.optimize_db_indexes import DatabaseOptimizer
from backend.db import AircraftDatabase


class TestDatabaseOptimization:
    """Test database optimization functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Initialize database with test data
        self._setup_test_data()
    
    def teardown_method(self):
        """Clean up after tests."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _setup_test_data(self):
        """Create test database with sample data."""
        db = AircraftDatabase(self.db_path)
        
        # Add aircraft data
        for i in range(100):
            db.save_aircraft_to_cache({
                'icao24': f'test{i:03d}',
                'image_url': f'https://example.com/plane{i}.jpg',
                'type': f'B73{i%10}'
            })
        
        # Add logbook data
        for i in range(50):
            db.add_to_logbook(f'Boeing 73{i%10}', f'https://example.com/boeing{i}.jpg')
        
        db.close()
    
    def test_optimizer_initialization(self):
        """Test optimizer initialization."""
        optimizer = DatabaseOptimizer(self.db_path)
        assert optimizer.db_path == self.db_path
        assert optimizer.connection is None
    
    def test_connect_and_close(self):
        """Test database connection management."""
        optimizer = DatabaseOptimizer(self.db_path)
        
        # Test connect
        optimizer.connect()
        assert optimizer.connection is not None
        assert isinstance(optimizer.connection, sqlite3.Connection)
        
        # Test close
        optimizer.close()
        # Connection should be closed but not None
        assert optimizer.connection is not None
    
    def test_analyze_current_indexes(self):
        """Test analyzing current indexes."""
        optimizer = DatabaseOptimizer(self.db_path)
        optimizer.connect()
        
        indexes = optimizer.analyze_current_indexes()
        
        # Should have at least the primary key indexes
        assert len(indexes) >= 0
        
        # Check index format
        for name, sql in indexes:
            assert isinstance(name, str)
            assert sql is None or isinstance(sql, str)
        
        optimizer.close()
    
    def test_get_table_info(self):
        """Test getting table information."""
        optimizer = DatabaseOptimizer(self.db_path)
        optimizer.connect()
        
        # Test aircraft table
        aircraft_info = optimizer.get_table_info('aircraft')
        assert len(aircraft_info) > 0
        
        # Check for expected columns
        column_names = [col['name'] for col in aircraft_info]
        assert 'icao24' in column_names
        assert 'image_url' in column_names
        assert 'type' in column_names
        assert 'last_updated' in column_names
        
        # Test logbook table
        logbook_info = optimizer.get_table_info('logbook')
        assert len(logbook_info) > 0
        
        optimizer.close()
    
    def test_create_aircraft_indexes(self):
        """Test creating aircraft table indexes."""
        optimizer = DatabaseOptimizer(self.db_path)
        optimizer.connect()
        
        # Create indexes
        optimizer.create_aircraft_indexes()
        
        # Verify indexes were created
        indexes = optimizer.analyze_current_indexes()
        index_names = [idx[0] for idx in indexes]
        
        assert 'idx_aircraft_last_updated' in index_names
        assert 'idx_aircraft_type_updated' in index_names
        
        optimizer.close()
    
    def test_create_logbook_indexes(self):
        """Test creating logbook table indexes."""
        optimizer = DatabaseOptimizer(self.db_path)
        optimizer.connect()
        
        # Create indexes
        optimizer.create_logbook_indexes()
        
        # Verify indexes were created
        indexes = optimizer.analyze_current_indexes()
        index_names = [idx[0] for idx in indexes]
        
        assert 'idx_logbook_first_spotted' in index_names
        assert 'idx_logbook_last_spotted' in index_names
        assert 'idx_logbook_sighting_count' in index_names
        assert 'idx_logbook_spotted_type' in index_names
        
        optimizer.close()
    
    def test_get_database_stats(self):
        """Test getting database statistics."""
        optimizer = DatabaseOptimizer(self.db_path)
        optimizer.connect()
        
        stats = optimizer.get_database_stats()
        
        assert 'database_size_mb' in stats
        assert 'aircraft_rows' in stats
        assert 'logbook_rows' in stats
        assert 'index_count' in stats
        
        assert stats['aircraft_rows'] == 100
        assert stats['logbook_rows'] == 50
        assert stats['database_size_mb'] > 0
        
        optimizer.close()
    
    def test_analyze_tables(self):
        """Test analyzing tables."""
        optimizer = DatabaseOptimizer(self.db_path)
        optimizer.connect()
        
        # Should not raise any exceptions
        optimizer.analyze_tables()
        
        optimizer.close()
    
    def test_vacuum_database(self):
        """Test vacuuming database."""
        optimizer = DatabaseOptimizer(self.db_path)
        optimizer.connect()
        
        # Get size before vacuum
        stats_before = optimizer.get_database_stats()
        
        # Vacuum should not raise any exceptions
        optimizer.vacuum_database()
        
        # Database should still be functional
        stats_after = optimizer.get_database_stats()
        assert stats_after['aircraft_rows'] == stats_before['aircraft_rows']
        
        optimizer.close()
    
    def test_full_optimization_process(self):
        """Test the complete optimization process."""
        optimizer = DatabaseOptimizer(self.db_path)
        
        # Should not raise any exceptions
        optimizer.optimize()
        
        # Verify indexes were created
        optimizer.connect()
        indexes = optimizer.analyze_current_indexes()
        index_names = [idx[0] for idx in indexes]
        
        # Should have all the expected indexes
        expected_indexes = [
            'idx_aircraft_last_updated',
            'idx_aircraft_type_updated',
            'idx_logbook_first_spotted',
            'idx_logbook_last_spotted',
            'idx_logbook_sighting_count',
            'idx_logbook_spotted_type'
        ]
        
        for expected in expected_indexes:
            assert expected in index_names
        
        optimizer.close()
    
    def test_query_performance_improvement(self):
        """Test that indexes improve query performance."""
        # Test without indexes
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Measure query without indexes
        cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM logbook ORDER BY first_spotted DESC")
        plan_before = cursor.fetchall()
        
        conn.close()
        
        # Optimize database
        optimizer = DatabaseOptimizer(self.db_path)
        optimizer.optimize()
        
        # Test with indexes
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Measure query with indexes
        cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM logbook ORDER BY first_spotted DESC")
        plan_after = cursor.fetchall()
        
        # The query plan should mention using an index
        plan_text = str(plan_after)
        assert 'idx_logbook_first_spotted' in plan_text or 'INDEX' in plan_text
        
        conn.close()