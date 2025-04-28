import os
import mysql.connector
import logging

# Table definitions
# CREATE TABLE device_alias (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     device VARCHAR(255) NOT NULL,
#     alias VARCHAR(255) NOT NULL,
#     UNIQUE KEY (device, alias)
# );

#CREATE TABLE ot_it_mapping (
#    ot_id VARCHAR(50) PRIMARY KEY,
#    it_alias VARCHAR(100) NOT NULL
#);

class Client:
    def __init__(self):
        self.host = os.getenv("MARIADB_HOST", "localhost")
        self.user = os.getenv("MARIADB_USER", "root")
        self.password = os.getenv("MARIADB_PASSWORD", "public")
        self.connection = None
    
    def connect(self) -> bool:
        try:
            connection = mysql.connector.connect(
                host=self.host,
                database='demo',
                user=self.user,
                password=self.password,
                charset="utf8mb4",
                collation="utf8mb4_general_ci"  # Using MariaDB compatible collation
            )
            logging.info(f"Connected to MariaDB at {self.host}")
            self.connection = connection
            return True
        except mysql.connector.Error as err:
            logging.critical(f"Error connecting to MariaDB: {err}")
            return False
    
    def get_ot_id_by_alias(self, it_alias: str) -> list[str]:
        """
        Retrieve OT IDs based on fuzzy matching of descriptions from the ot_it_mapping table
        
        Args:
            description (str): The description to search for
            
        Returns:
            list[str]: A list of matching OT IDs, empty list if none found
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            # Using LIKE with wildcards for fuzzy matching
            query = "SELECT ot_id FROM ot_it_mapping WHERE it_alias LIKE %s"
            # Add wildcards before and after the search term
            search_term = f"%{it_alias}%"

            logging.info(f'{query} {search_term}')
            cursor.execute(query, (search_term,))
            
            results = cursor.fetchall()
            return [result[0] for result in results] if results else []
            
        except mysql.connector.Error as err:
            print(f"Error querying database: {err}")
            return []
        
    