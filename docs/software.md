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

- Pull TDengine

```bash
docker pull tdengine/tdengine:latest
```

- Run TDengine

```bash
docker run -d -p 6030:6030 -p 6041:6041 -p 6043:6043 -p 6044-6049:6044-6049 -p 6044-6045:6044-6045/udp -p 6060:6060 tdengine/tdengine
```
- Create database and table

Main application will create the database and table automatically.

```sql
CREATE TABLE IF NOT EXISTS devices (
    `ts` TIMESTAMP,
    `device` BINARY(128),
    `status` BINARY(32))

CREATE TABLE IF NOT EXISTS tag_values (
    `ts` TIMESTAMP, `tag_name` BINARY(128), `tag_value` BINARY(128), `device` BINARY(128))
```

## MariaDB
Refer to [doc](https://mariadb.com/resources/blog/get-started-with-mariadb-using-docker-in-3-steps/) for setting up the database.

Create a table in MariaDB to store the OT & IT mapping. For example, we have a telemetry data reported from `factory_1`, which is an identifier from OT pespective. Normally, for example, people would call the `factory_1` as `LA factory`, which means the factory locates in Los Angeles.

```sql
CREATE DATABASE demo;
USE demo;
CREATE TABLE ot_it_mapping (
    ot_id VARCHAR(50),
    it_alias VARCHAR(100) NOT NULL
);

-- Insert the example data
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('factory_1', 'LA factory');  
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('assembly_1', 'Big boy');  
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('test', 'Bee');  
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('demo', '擎天柱');  
INSERT INTO ot_it_mapping (ot_id, it_alias) VALUES ('demo', 'Optimus Prime');  
```