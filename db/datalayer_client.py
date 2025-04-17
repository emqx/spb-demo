import http
import os
from collections import OrderedDict

import pandas
import pyarrow as pa
import pyarrow.flight as flight
from flightsql import FlightSQLClient
from flightsql.client import PreparedStatement

class Client:
    def __init__(self):
        host = os.getenv("DATALAYER_HOST", "grpc+tcp://localhost:8360")
        user = os.getenv("DATALAYER_USER", "admin")
        password = os.getenv("DATALAYER_PASSWORD", "public")

        flight_client = flight.FlightClient(host)

        headers = []
        headers.append(
            flight_client.authenticate_basic_token(user, password)
        )

        flight_sql_client = FlightSQLClient.__new__(FlightSQLClient)
        flight_sql_client.client = flight_client
        flight_sql_client.headers = headers
        flight_sql_client.features = {}
        flight_sql_client.closed = False

        self.__client = flight_sql_client
    
    def use_database(self, database: str):
        headers = self.__client.headers + [(b"database", database.encode("utf-8"))]
        headers = list(OrderedDict(headers).items())
        self.__client.headers = headers
    
    def execute(self, sql: str) -> pandas.DataFrame:
        flight_info = self.__client.execute(sql)
        ticket = flight_info.endpoints[0].ticket
        reader = self.__client.do_get(ticket)
        df = reader.read_pandas()
        return df

    def execute_update(self, sql: str) -> int:
        return self.__client.execute_update(sql, None)

    def prepare(self, sql: str) -> PreparedStatement:
        return self.__client.prepare(sql)

    def execute_prepared(
        self, prepared_stmt: PreparedStatement, binding: pa.RecordBatch
    ) -> pandas.DataFrame:
        flight_info = prepared_stmt.execute(binding)
        ticket = flight_info.endpoints[0].ticket
        reader = self.__client.do_get(ticket)
        df = reader.read_pandas()
        return df

    def close_prepared(self, prepared_stmt: PreparedStatement):
        prepared_stmt.close()

    def close(self):
        self.__client.close()