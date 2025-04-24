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
            self.__create_device_table()
            self.__create_ot_it_mapping_table()
            #self.insert_device_alias("温度传感器", "modbus")
            #self.insert_ot_it_mapping("factory_1", "LA factory")
            #self.insert_ot_it_mapping('assembly_1', "Big boy")
            #self.insert_ot_it_mapping('test', 'Bee')
            return True
        except mysql.connector.Error as err:
            logging.critical(f"Error connecting to MariaDB: {err}")
            return False
    
    def __create_device_table(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_alias (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    device VARCHAR(255) NOT NULL,
                    alias VARCHAR(255) NOT NULL,
                    UNIQUE KEY (device, alias)
                )
            """)
            self.connection.commit()
            logging.info("Table device_alias created successfully")
        except mysql.connector.Error as err:
            logging.error(f"Error creating table: {err}")
    
    def __create_ot_it_mapping_table(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ot_it_mapping (
                    ot_id VARCHAR(50) PRIMARY KEY,
                    it_alias VARCHAR(100) NOT NULL
                )
            """)
            self.connection.commit()
            logging.info("Table ot_it_mapping created successfully")
        except mysql.connector.Error as err:
            logging.error(f"Error creating table: {err}")
    
    def query_device_by_alias(self, alias: str) -> str | None:
        try:
            cursor = self.connection.cursor()
            query = "SELECT device FROM device_alias WHERE alias = %s"
            cursor.execute(query, (alias,))
            result = cursor.fetchone()
            return result[0] if result else None
        except mysql.connector.Error as err:
            logging.error(f"Error querying database: {err}")
            return None

    
    def insert_device_alias(self, alias: str, device: str): 
        try:
            cursor = self.connection.cursor()
            query = "INSERT INTO device_alias (device, alias) VALUES (%s, %s)"
            cursor.execute(query, (device, alias))
            self.connection.commit()
            logging.info(f"Inserted device alias {alias} for device {device}")
        except mysql.connector.Error as err:
            logging.error(f"Error inserting device alias: {err}")
    
    def insert_ot_it_mapping(self, ot_id: str, it_alias: str):
        try:
            cursor = self.connection.cursor()
            query = "INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES (%s, %s)"
            cursor.execute(query, (ot_id, it_alias))
            self.connection.commit()
            logging.info(f"Inserted OT ID {ot_id} with alias {it_alias}")
        except mysql.connector.Error as err:
            logging.error(f"Error inserting OT ID mapping: {err}")
    
    def get_ot_id_by_alias(self, it_alias: str) -> list[str]:
        """
        Retrieve OT IDs based on fuzzy matching of descriptions from the ot_it_mapping table
        
        Args:
            description (str): The description to search for
            
        Returns:
            list[str]: A list of matching OT IDs, empty list if none found
        """
        try:
            cursor = self.connection.cursor()
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
    