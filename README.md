## Overview

This project demonstrates a Sparkplug B (SPB) implementation featuring a chat-based interface for industrial IoT monitoring and control. It combines a Sparkplug MCP server with a web application that allows users to query device data, analyze historical metrics, and monitor device status through natural language interactions. The system supports both real-time monitoring and historical analysis of device metrics, making it ideal for industrial automation and IoT applications.

## Architect diagram
![alt text](./docs/arch.png)

## Setup workspace

Follow the steps below to set up and run the application:

1. Clone the Repository
```bash
git clone https://github.com/emqx/spb-demo/
cd spb-demo
```

2. The project use `uv` to manage libs and project, please install [uv](https://docs.astral.sh/uv/getting-started/installation/) before getting start.

3. Some dependencies need to be compiled through cmake, please install [cmake](https://cmake.org/download/) before getting start.

4. Install Dependencies and Activate Virtual Environment
```bash
uv sync
uv venv
```

## Pre-conditions
### Install software and configurations
Please refer to [software preparation](docs/software.md).

## Run the application
**Steps**
- Copy `.env.example` to `.env` and modify the values accordingly.
- Run sparkplug mcp server
```bash
  uv run spb_server.py
```
- Run biz mcp server
```bash
  uv run biz_app.py
```
- Run main application
```bash
  uv run main.py
```
- Open http://localhost:8000/ in browser.
- Type questions in the chatbox.

## Demos
Refer to [doc](docs/demo_scenario.md) for more detailed information.