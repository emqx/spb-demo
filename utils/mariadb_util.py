import mysql.connector
from typing import Optional
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def __get_mariadb_connection():
    """Establish connection to MariaDB database"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('MARIADB_HOST', 'localhost'),
            database=os.getenv('MARIADB_DATABASE', 'sample'),
            user=os.getenv('MARIADB_USER'),
            password=os.getenv('MARIADB_PASSWORD'),
            charset="utf8mb4",
            collation="utf8mb4_general_ci"  # Using MariaDB compatible collation
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to MariaDB: {err}")
        return None

def get_ot_id_by_alias(it_alias: str) -> list[str]:
    """
    Retrieve OT IDs based on fuzzy matching of descriptions from the ot_it_mapping table
    
    Args:
        description (str): The description to search for
        
    Returns:
        list[str]: A list of matching OT IDs, empty list if none found
    """
    connection = __get_mariadb_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor()
        # Using LIKE with wildcards for fuzzy matching
        query = "SELECT ot_id FROM ot_it_mapping WHERE it_alias LIKE %s"
        # Add wildcards before and after the search term
        search_term = f"%{it_alias}%"
        cursor.execute(query, (search_term,))
        
        results = cursor.fetchall()
        return [result[0] for result in results] if results else []
        
    except mysql.connector.Error as err:
        print(f"Error querying database: {err}")
        return []
        
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Example usage:
if __name__ == "__main__":
    # Example: Search OT IDs by description
    ot_ids = get_ot_id_by_alias('factory')
    print(f"Matching OT IDs: {ot_ids}")
