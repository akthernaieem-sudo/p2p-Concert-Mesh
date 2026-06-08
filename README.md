# P2P Concert Mesh Network

A decentralized, serverless peer-to-peer (P2P) mesh messaging application engineered for off-grid communication in high-density environments like crowded music festivals and concerts. This system completely bypasses cellular infrastructure, utilizing localized routing protocols and asynchronous data synchronization.

# System Architecture

The application is built as a split-runtime architecture: a lightweight, concurrent Python backend engine handling socket multiplexing and network routing, paired with an asynchronous JavaScript frontend client for real-time telemetry rendering.

* ## Decentralized Topology: Zero reliance on central servers, cloud providers (AWS/GCP), or external databases. Every node acts as both a client and a router.
* ## Asynchronous I/O Multiplexing: Utilizes non-blocking network sockets to handle concurrent incoming and outgoing peer connections seamlessly.
* ## Dynamic Discovery & Relay: Implements localized ad-hoc routing, allowing message packets to hop across intermediate nodes to reach peers outside of immediate radio/network range.

##  Key Features

## Real-Time Localized Broadcasting
Nodes maintain active peer-state lists, dynamically discovering and rendering nearby neighbors via a custom radar-style UI. Message propagation uses data serialization to prevent loop-back amplification.

## Resilient Emergency SOS Override
Includes an isolated distress broadcast layer. When triggered, the system bypasses standard chat throttles to flood critical telemetry data across all available mesh paths, leveraging multi-hop relay mechanics to breach areas with complete cellular blackout.
