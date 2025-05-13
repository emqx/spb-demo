## EMQX Enterprise 5.6.x
Install EMQX Enterprise 5.6.x and start it.

## NeuronEX >= 3.5.1
Install NeuronEX and create related devices. 

- You can create the device and tag configurations as in below.

```
demo
├── diagnose
│   └── error_code
└── robotic_arm
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
CREATE TABLE ot_it_mapping (
    ot_id VARCHAR(50) PRIMARY KEY,
    it_alias VARCHAR(100) NOT NULL
);

-- Insert the example data
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('factory_1', 'LA factory');  
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('assembly_1', 'Big boy');  
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('test', 'Bee');  
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('demo', '擎天柱');  
```