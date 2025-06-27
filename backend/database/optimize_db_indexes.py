"""
Database index optimization script.

This script analyzes the database schema and creates optimal indexes
for improving query performance.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Optimizes database indexes for better performance."""
    
    def __init__(self, db_path: str = "backend/aircraft_cache.db"):
        """Initialize the database optimizer."""
        self.db_path = db_path
        self.connection = None
    
    def connect(self) -> None:
        """Connect to the database."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.db_path}")
    
    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def analyze_current_indexes(self) -> List[Tuple[str, str]]:
        """Analyze current indexes in the database."""
        cursor = self.connection.cursor()
        
        # Get all indexes
        cursor.execute("""
            SELECT name, sql 
            FROM sqlite_master 
            WHERE type = 'index' 
            AND sql IS NOT NULL
        """)
        
        indexes = cursor.fetchall()
        return [(idx['name'], idx['sql']) for idx in indexes]
    
    def get_table_info(self, table_name: str) -> List[dict]:
        """Get information about table columns."""
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [dict(row) for row in cursor.fetchall()]
    
    def create_aircraft_indexes(self) -> None:
        """Create optimized indexes for the aircraft table."""
        cursor = self.connection.cursor()
        
        # Index on last_updated for time-based queries
        logger.info("Creating index on aircraft.last_updated...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_aircraft_last_updated 
            ON aircraft(last_updated DESC)
        """)
        
        # Composite index for type and last_updated
        logger.info("Creating composite index on aircraft(type, last_updated)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_aircraft_type_updated 
            ON aircraft(type, last_updated DESC)
        """)
        
        self.connection.commit()
        logger.info("Aircraft table indexes created")
    
    def create_logbook_indexes(self) -> None:
        """Create optimized indexes for the logbook table."""
        cursor = self.connection.cursor()
        
        # Index on first_spotted for chronological queries
        logger.info("Creating index on logbook.first_spotted...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_logbook_first_spotted 
            ON logbook(first_spotted DESC)
        """)
        
        # Index on last_spotted for recent activity queries
        logger.info("Creating index on logbook.last_spotted...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_logbook_last_spotted 
            ON logbook(last_spotted DESC)
        """)
        
        # Index on sighting_count for popularity queries
        logger.info("Creating index on logbook.sighting_count...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_logbook_sighting_count 
            ON logbook(sighting_count DESC)
        """)
        
        # Composite index for filtered queries by date
        logger.info("Creating composite index on logbook(first_spotted, aircraft_type)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_logbook_spotted_type 
            ON logbook(first_spotted DESC, aircraft_type)
        """)
        
        self.connection.commit()
        logger.info("Logbook table indexes created")
    
    def analyze_query_plans(self) -> None:
        """Analyze query execution plans for common queries."""
        cursor = self.connection.cursor()
        
        queries = [
            # Aircraft cache queries
            ("Get aircraft by ICAO24", 
             "SELECT * FROM aircraft WHERE icao24 = 'abc123'"),
            
            ("Get recent aircraft updates",
             "SELECT * FROM aircraft WHERE last_updated > datetime('now', '-1 day')"),
            
            ("Get aircraft by type",
             "SELECT * FROM aircraft WHERE type = 'B737' ORDER BY last_updated DESC"),
            
            # Logbook queries
            ("Get all logbook entries",
             "SELECT * FROM logbook ORDER BY first_spotted DESC"),
            
            ("Get recent logbook entries",
             "SELECT * FROM logbook WHERE first_spotted > datetime('now', '-7 days')"),
            
            ("Get most spotted aircraft",
             "SELECT * FROM logbook ORDER BY sighting_count DESC LIMIT 10"),
            
            ("Get recently spotted aircraft",
             "SELECT * FROM logbook ORDER BY last_spotted DESC LIMIT 10"),
        ]
        
        logger.info("\nQuery execution plans:")
        logger.info("-" * 80)
        
        for description, query in queries:
            cursor.execute(f"EXPLAIN QUERY PLAN {query}")
            plan = cursor.fetchall()
            
            logger.info(f"\n{description}:")
            logger.info(f"Query: {query}")
            logger.info("Plan:")
            for step in plan:
                logger.info(f"  {dict(step)}")
    
    def vacuum_database(self) -> None:
        """Vacuum the database to reclaim space and optimize."""
        logger.info("Vacuuming database...")
        self.connection.execute("VACUUM")
        logger.info("Database vacuum completed")
    
    def analyze_tables(self) -> None:
        """Update SQLite's internal statistics for query optimization."""
        logger.info("Analyzing tables...")
        self.connection.execute("ANALYZE")
        logger.info("Table analysis completed")
    
    def get_database_stats(self) -> dict:
        """Get database statistics."""
        cursor = self.connection.cursor()
        
        stats = {}
        
        # Get database size
        db_size = Path(self.db_path).stat().st_size
        stats['database_size_mb'] = round(db_size / (1024 * 1024), 2)
        
        # Get table row counts
        tables = ['aircraft', 'logbook']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[f'{table}_rows'] = cursor.fetchone()['count']
        
        # Get index count
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM sqlite_master 
            WHERE type = 'index'
        """)
        stats['index_count'] = cursor.fetchone()['count']
        
        return stats
    
    def optimize(self) -> None:
        """Run the complete optimization process."""
        try:
            self.connect()
            
            # Show current state
            logger.info("Current database state:")
            stats_before = self.get_database_stats()
            for key, value in stats_before.items():
                logger.info(f"  {key}: {value}")
            
            # Show existing indexes
            logger.info("\nExisting indexes:")
            current_indexes = self.analyze_current_indexes()
            for name, sql in current_indexes:
                logger.info(f"  {name}: {sql}")
            
            # Create new indexes
            logger.info("\nCreating optimized indexes...")
            self.create_aircraft_indexes()
            self.create_logbook_indexes()
            
            # Analyze tables
            self.analyze_tables()
            
            # Show query plans
            self.analyze_query_plans()
            
            # Vacuum database
            self.vacuum_database()
            
            # Show final state
            logger.info("\nFinal database state:")
            stats_after = self.get_database_stats()
            for key, value in stats_after.items():
                logger.info(f"  {key}: {value}")
            
            logger.info("\nDatabase optimization completed successfully!")
            
        finally:
            self.close()


def main():
    """Main entry point."""
    optimizer = DatabaseOptimizer()
    optimizer.optimize()


if __name__ == "__main__":
    main()