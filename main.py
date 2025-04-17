from db import mariadb
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO, filename="./logs/spb_demo.log", filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")

mariadb = mariadb.Client()
mariadb.connect()