


## Setup workspace

Follow the steps below to set up and run the application:

1. Clone the Repository
```bash
git clone https://github.com/emqx/spb_demo/
cd spb_demo
```
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

3. Install Dependencies and Activate Virtual Environment
```bash
uv sync
uv venv
```

## EMQX Enterprise 5.6.x
Install EMQX Enterprise 5.6.x and start it.

## NeuronEX   >= 3.5.1
Install NeuronEX and create related devices. 

- You can create the device and tag configurations as in below.

```
test
├── group1
│   └── t1
└── group2
    ├── voltage
    └── amper
```

- Create a Sparkplug north application to report the data to EMQX.
  - Group name is `factory_1` 
  - Node name is `assembly_1`

## Setup timeseries database

- Pull Datalayers

```bash
docker pull datalayers/datalayers:v2.2.15
```

- Run Datalayers

```bash
docker run --name datalayers -d \
  -v ~/data:/var/lib/datalayers \
  -p 8360:8360 -p 8361:8361 \
  datalayers/datalayers:v2.2.15
```
- To enter the bash
```bash
docker exec -it datalayers bash
```
- Login and create database
```bash
dlsql -u admin -p public
create database demo;
use demo;
```
- Create tables
```sql
 CREATE TABLE tags (
  ts TIMESTAMP(9) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tag STRING,
  device STRING,
  value STRING,
  timestamp KEY (ts))
  PARTITION BY HASH(device) PARTITIONS 8
  ENGINE=TimeSeries
  with (ttl='10d');

 CREATE TABLE devices (
  ts TIMESTAMP(9) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  device STRING,
  status STRING,
  timestamp KEY (ts))
  PARTITION BY HASH(device) PARTITIONS 8
  ENGINE=TimeSeries
  with (ttl='10d');
```

## MariaDB
Refer to [doc](https://mariadb.com/resources/blog/get-started-with-mariadb-using-docker-in-3-steps/) for setting up the database.

Create a table in MariaDB to store the OT & IT mapping. For example, we have a telemetry data reported from `factory_1`, which is an identifier from OT pespective. Normally, for example, people would call the `factory_1` as `LA factory`, which means the factory locates in Los Angeles.

```sql
CREATE DATABASE demo;
USE demo;
CREATE TABLE device_alias (
     id INT AUTO_INCREMENT PRIMARY KEY,
     device VARCHAR(255) NOT NULL,
     alias VARCHAR(255) NOT NULL,
     UNIQUE KEY (device, alias)
);
CREATE TABLE ot_it_mapping (
    ot_id VARCHAR(50) PRIMARY KEY,
    it_alias VARCHAR(100) NOT NULL
);

-- Insert the example data
INSERT INTO device_alias (device, alias) VALUES ('modbus', '温度传感器');  
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('factory_1', 'LA factory');  
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('assembly_1', 'Big boy');  
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('test', 'Bee');  
```

## Install PostGres vectordb

Refer to [doc](https://medium.com/@adarsh.ajay/setting-up-postgresql-with-pgvector-in-docker-a-step-by-step-guide-d4203f6456bd) for detailed instruction.

```shell
docker pull ankane/pgvector

docker run -e POSTGRES_USER=emqx \
           -e POSTGRES_PASSWORD=public \
           -e POSTGRES_DB=mydatabase \
           --name my_postgres \
           -p 5432:5432 \
           -d ankane/pgvector

#In container
psql -h localhost -U emqx -d mydatabase -p 5432

#SQLs
#List the tables
\dt 
            List of relations
 Schema |      Name       | Type  | Owner
--------+-----------------+-------+-------
 public | data_test_table | table | emqx
(1 row)
```

## Usage
Copy `.env.example` to `.env` and modify the values accordingly.

## Run the application
**Steps**
- Run sparkplug mcp server
```bash
  uv run spb_server.py
```
- Run main application
```bash
  uv run main.py
```
- Open http://localhost:8000/ in browser.
- Type questions in the chatbox.

**Demo scenario**
- 查询过去一周节点 assembly_1 的离线情况 
  - Query the offline status of assembly_1 of last week.

- 请列出设备 test 的树形结构 
  - List the tree structure of device named "test".

- 总结一下过去一周 factory_1 组下节点名称为 assembly_1 下的 test 设备点位 group2/voltage 的工作情况 
  - Summarize the last week status of tag points "group2/voltage", which is under device named "test" of assembly_1 edge node locates in factory_1.

- Query the offline status of  "Big boy" of last week.