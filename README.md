clientloader
============

clienloader is a free, open source, lightweight load testing tool.

To use the load testing tool:
python clientload.py
There is a HTTP RPC service will be run. you can use HTTP RPC client connect to this service and use open functions to control your simulate players.

Support Protocol:
---------------------------
* MMS --- need install libmms first, Linux Only
* HLS
* DASH
* RTSP
* RTMP

Open Functions:
---------------------------

* start_client(task_uuid, url, number)
* check_clients_status(task_uuid, restart_client_on_failure)
* check_task_status()
* stop_clients(task_uuid, client_number, random_stop, client_type)
* stop_force(task_uuid)
* clear_clients()
* check_clients_number(task_uuid)
