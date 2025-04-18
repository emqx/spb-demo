


## Setup workspace

Follow the steps below to set up and run the application:

1. Clone the Repository
```bash
git clone https://github.com/emqx/spb_demo/
cd spb_demo
```

2. Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

## EMQX Enterprise 5.6.x
Install EMQX Enterprise 5.6.x and start it.

## NeuronEX
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
CREATE TABLE int_tags (
  ts TIMESTAMP(9) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tag_name STRING,
  device_key STRING,
  tag_value INT,
  timestamp KEY (ts))
  PARTITION BY HASH(device_key) PARTITIONS 8
  ENGINE=TimeSeries
  with (ttl='10d');

CREATE TABLE float_tags (
  ts TIMESTAMP(9) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tag_name STRING,
  device_key STRING,
  tag_value FLOAT,
  timestamp KEY (ts))
  PARTITION BY HASH(device_key) PARTITIONS 8
  ENGINE=TimeSeries
  with (ttl='10d');

CREATE TABLE double_tags (
  ts TIMESTAMP(9) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tag_name STRING,
  device_key STRING,
  tag_value DOUBLE,
  timestamp KEY (ts))
  PARTITION BY HASH(device_key) PARTITIONS 8
  ENGINE=TimeSeries
  with (ttl='10d');

CREATE TABLE boolean_tags (
  ts TIMESTAMP(9) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tag_name STRING,
  device_key STRING,
  tag_value BOOLEAN,
  timestamp KEY (ts))
  PARTITION BY HASH(device_key) PARTITIONS 8
  ENGINE=TimeSeries
  with (ttl='10d');
```

## MariaDB
Refer to [doc](https://mariadb.com/resources/blog/get-started-with-mariadb-using-docker-in-3-steps/) for setting up the database.

Create a table in MariaDB to store the OT & IT mapping. For example, we have a telemetry data reported from `factory_1`, which is an identifier from OT pespective. Normally, for example, people would call the `factory_1` as `LA factory`, which means the factory locates in Los Angeles.

```sql
CREATE DATABASE sample;
USE sample;
CREATE TABLE ot_it_mapping (
    ot_id VARCHAR(50) PRIMARY KEY,
    it_alias VARCHAR(100) NOT NULL
);

-- Insert the example data
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
Create `.env` file under the root directory, and specify the following values.

```
#LLMs
DS_API_KEY=
DS_MODEL_NAME=deepseek-chat
DS_API_BASE_URL=https://api.deepseek.com

SF_API_KEY=
MODEL_NAME=Pro/deepseek-ai/DeepSeek-V3
# MODEL_NAME=Pro/deepseek-ai/DeepSeek-R1

EMBEDDING_API_KEY=
EMBEDDING_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

#EMQX Broker
MQTT_BROKER=127.0.0.1
MQTT_PORT=1883
MQTT_TOPIC=spBv1.0/#

#MariaDB
MARIADB_HOST=localhost
MARIADB_DATABASE=sample
MARIADB_USER=root
MARIADB_PASSWORD=Password123!

#Datalayers
DB_HOST=127.0.0.1
DB_PORT=8361
DB_TOKEN=YWRtaW46cHVibGlj

#PgSQL vector database
PGSQL_CONN=postgresql://emqx:public@localhost:5432
PGSQL_DB=mydatabase
PGSQL_TABLE=test_table

MCP_SRV_BASE_DIR=/Users/rocky/Downloads/workspace/spb_demo
```

## Run the application

Run the `spb_app.py` to collect the data and save it into the database.

## Demo scenario
### 查询过去一周节点 assembly_1 的离线情况 (Query the offline status of assembly_1 of last week.)

好的,我将用中文为您总结 factory_1 组下节点 assembly_1 的过去一周工作情况。让我继续分析已获取的数据。

根据收集到的数据，以下是节点 assembly_1 的工作状态总结：

1. 节点运行状态：
   - 在3月29日出现了多次启动(NBIRTH)事件，具体时间点为：
     - 00:36:45
     - 03:08:24
     - 03:12:33
     - 19:58:47
     - 23:18:38
     - 23:51:09
     - 23:52:16
   - 在3月29日记录到两次离线(NDEATH)事件：
     - 23:51:17
     - 23:51:34

2. 已连接设备：
   - 节点上连接了一个名为 'test' 的设备，其结构如下：
     - Device Control（设备控制）
       - Rebirth（重启）
       - Reboot（重启）
     - group1 分组
       - t1 标签
     - group2 分组
       - voltage（电压）标签
       - amper（电流）标签

3. 节点配置：
   - 节点具有以下控制功能：
     - Next Server（下一个服务器）
     - Rebirth（重生）
     - Reboot（重启）

4. 数据分析：
   - 虽然我们可以看到设备的结构，但过去一周的历史数据查询没有返回任何值，这可能说明：
     - 设备可能是新配置的
     - 数据可能以不同的格式存储
     - 或者最近没有数据记录

5. 稳定性分析：
   - 根据启动/离线事件记录，该节点在3月29日经历了多次重启
   - 特别是在23:51左右的多次启动事件，这可能表明：
     - 存在一些稳定性问题
     - 或是在进行计划内的维护活动

您是否需要我深入研究该节点运行状态的某个具体方面？比如：
- 某个具体时间段的详细数据
- 特定标签的历史值变化
- 设备重启的具体原因分析
等等，我都可以为您进一步查询和分析。


### 请列出设备 test 的树形结构 (List the tree structure of device named "test".)
```
test (设备)
├── Device Control
│   ├── Rebirth
│   └── Reboot
├── group1
│   └── t1
└── group2
    ├── voltage
    └── amper
```
```
test (设备)
├── Device Control
│   ├── Rebirth (布尔值: false)
│   └── Reboot (布尔值: false)
├── group1
│   └── t1 (整数值: 78)
└── group2
    ├── voltage (浮点值: 4.6)
    └── amper (双精度值: 3.14)
```
### 总结一下过去一周 factory_1 组下节点名称为 assembly_1 下的 test 设备点位 group2/voltage 的工作情况 (Summarize the last week status of tag points "group2/voltage", which is under device named "test" of assembly_1 edge node locates in factory_1.)

I'll help you analyze the working condition of the voltage tag under the specified device path. Let me break this down into steps:

1. First, I'll check the device history data for this specific tag. The full path should be `spBv1.0/factory_1/DDATA/assembly_1/test` with tag name `group2/voltage`.

Ran tool
2. Let me also check the device birth status to see if there were any device restarts:

Ran tool
Based on the data I've gathered, here's a summary of the working condition for the voltage tag (`group2/voltage`) under the device `test` in `factory_1/assembly_1`:

1. **Current Value**: The voltage is consistently reading at 4.6V.

2. **Data Reporting**:
   - The device is actively reporting data with regular intervals (approximately every second)
   - The most recent data point was recorded at 2025-03-30 00:11:29 (local time)
   - The data shows consistent reporting without significant gaps in the recent timeframe

3. **Device Status**:
   - The device has had several birth events (restarts) in the past 24 hours:
     - Latest restart at 2025-03-29 23:52:16
     - Previous restarts at 23:51:29, 23:51:09, 23:18:38, 19:58:47, and earlier
   - Despite these restarts, the voltage reading has remained stable at 4.6V

4. **Stability**:
   - The voltage reading shows remarkable stability, maintaining a constant value of 4.6V across all measurements
   - No fluctuations or anomalies were observed in the voltage readings
   - The device appears to be functioning normally with consistent data reporting

Overall, the voltage measurement appears to be stable and reliable, though the device has undergone several restarts. The consistent value might either indicate a very stable system or potentially suggest that you might want to verify the sensor's dynamic range is working as expected, since there's no variation at all in the readings.
