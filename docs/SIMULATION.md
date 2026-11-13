# Simulation bench

Runs the real health probes of the hub against simulated machines on loopback (a broker, an OPC UA server, a vehicle that streams MAVLink, a controller with a declared exchange, a web endpoint) that fail on command.

Scenarios:

- every way a machine can fail (silence, a reset, a half answer, noise, a wrong checksum, a refusal code, a slow answer, an endless stream) ends in an unhealthy result with a reason, never in an exception and never in a healthy result;
- a passive probe never sends anything, and a profile that asks for an active probe is ignored without the host switch;
- a fleet of 40 simulated machines with a fault assigned from a fixed seed is classified exactly as expected;
- the result cache remembers a link that flaps for its window and re-checks afterwards.

The evidence of this project is `simulator`: it says nothing about real machines, real networks or real load.
