# Bench tests

Every test below is **not executed**. The probe (`probe`, `GET /probe/<id>`) runs the health checks `http-get`, `tcp-connect`, `mqtt-ping`, `opcua-read`, `serial-probe`, `gpio-read`, `rpc-ping`, `ros2-node-alive` and `mavlink-heartbeat` for real, but only against local stand-ins in the tests (sockets, a character device and a streamed MAVLink heartbeat); the `opcua-read` check sends a Hello and does not read a node, the device checks only open the device file, and `rpc-ping` and `ros2-node-alive` only connect to the port. Every other kind of check answers `unsupported` and is never reported as healthy. Write a result only after a person ran the step.

## What the software already covers (no equipment needed)

- The unit tests start local servers (HTTP, TCP, an MQTT broker stand-in answering CONNACK and a stand-in answering the OPC UA Hello) and check healthy, unreachable, refused and timed-out answers.

## Setup

- The profile of the operator naming real places: a web service, a TCP port of a device, an MQTT broker and an OPC UA server.
- For the kinds not built (serial, GPIO, ROS 2, MAVLink, RPC, recent MQTT topic), the device or library that each would need.

## Steps

| # | Step | Expected result | Result |
|---|------|-----------------|--------|
| 1 | Probe each real place while it is up. | `http-get`, `tcp-connect`, `mqtt-ping` report healthy with a delay. | not executed |
| 2 | Stop each service and probe again. | Each reports unreachable, never healthy. | not executed |
| 3 | Probe a broker with the wrong credentials. | The answer is a refusal, not a success. | not executed |
| 4 | Probe the OPC UA server. | Healthy means only that it answered the Hello; the report says so. | not executed |
| 5 | Probe a declared check of a kind that is not built. | `unsupported`. | not executed |
| 6 | Set `HYDRA_UMC_HUB_ACTIVE_PROBES=1`, add `"active": true` to a real broker and probe it. | The report says `mqtt-pingresp` and `active: true`; with the switch off it says `mqtt-connack`. | not executed |
| 7 | Add the harmless order of a real serial device to the profile (`sendHex`, `expectHex`) and probe it with the switch on. | The device answers the declared bytes (`device-exchange`); a silent device is reported unhealthy. | not executed |

## What this bench cannot show

The reading of an OPC UA node, the content of a serial port or a GPIO line, a remote call or a ROS 2 node, and recent MQTT topics: the probes reach the place (and, with the active switch, exchange one harmless order), they do not read values.
