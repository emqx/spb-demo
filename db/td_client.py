import os
import logging

import taosws

class Client:
	def __init__(self):
		host = os.environ["TD_HOST"]
		port = os.environ["TD_PORT"]
		user = os.environ["TD_USER"]
		password = os.environ["TD_PASSWORD"]
		try:
			conn = taosws.connect(host=host, port=port, user=user, password=password)
			self.__client = conn
		except Exception as e:
			logging.error(f"Error connecting to TD: {e}")
			self.__client = None
			exit(1)
	
	def execute(self, sql: str):
		return self.__client.execute(sql)
	
	def query(self, sql: str):
		return self.__client.query(sql)