clientloader
============

clienloader is a free, open source, lightweight load testing tool.
Created by FengJian(Arthur Feng)

To use the load testing tool:
python clientload.py
There is a http service will be run. you can use HTTP GET method deploy load test.

Example:
---------------------------
1. Add
*http://<ip>:<port>/web/add_client.html?url=<request url>&number=<request number>&uuid=<uuid>

2. Query
*http://<ip>:<port>/web/query_client.html

3. Status
*http://<ip>:<port>/web/status_client.html?uuid=<uuid>

4.Delete
*http://<ip>:<port>/web/del_client.html?uuid=<uuid>

5.Clear
*http://<ip>:<port>/web/clear_client.html
