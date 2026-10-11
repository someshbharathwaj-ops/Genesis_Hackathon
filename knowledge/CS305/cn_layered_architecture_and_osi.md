# CS305 Computer Networks — Layered Architecture & The OSI / TCP/IP Reference Models

**Course Code:** CS305  
**Topic:** CS305_CORE (Network Core Principles & Layered Architecture)  
**Associated Learning Objectives:** `LO_CS305_FOUNDATIONS`, `LO_CS305_APPLICATION`  
**Prerequisites:** Digital Logic & Bit Representation  
**Authoritative References:** [Kurose & Ross, Computer Networking: A Top-Down Approach, Chapters 1 & 2; Tanenbaum, Computer Networks]

---

## 1. Network Layering Principles & Modularity

Computer networks employ protocol layering to organize complex hardware and software systems into modular, manageable abstractions.
- **Service:** Defines what a layer does for the layer above it, specified through service interfaces.
- **Protocol:** A set of rules governing the format and meaning of packets exchanged between peer entities at the same layer.
- **Encapsulation:** As application data travels down the protocol stack, each layer prepends a protocol header containing control metadata (e.g. addresses, sequence numbers, checksums), creating a Protocol Data Unit (PDU).

---

## 2. The 7-Layer OSI Model vs 5-Layer Internet Model

| Layer | OSI Name | Internet Protocol Stack | Primary Protocol Data Unit (PDU) | Core Responsibilities & Protocols |
| :---: | :--- | :--- | :--- | :--- |
| **7** | Application | Application | Message | Network applications, process-to-process exchange (`HTTP`, `DNS`, `SSH`, `SMTP`). |
| **6** | Presentation | *(Integrated in App)* | Data | Syntax, encryption, data compression, translation. |
| **5** | Session | *(Integrated in App)* | Data | Dialog control, synchronization checkpoints, token management. |
| **4** | Transport | Transport | Segment (TCP) / Datagram (UDP) | End-to-end host-to-host process delivery, port multiplexing, reliability (`TCP`, `UDP`). |
| **3** | Network | Network | Packet / IP Datagram | Host-to-host routing across networks, logical addressing (`IPv4`, `IPv6`, `ICMP`, `BGP`, `OSPF`). |
| **2** | Data Link | Link | Frame | Node-to-node hop-by-hop frame delivery, MAC addressing, error detection (`Ethernet`, `Wi-Fi`, `PPP`). |
| **1** | Physical | Physical | Bits | Transmission of raw unstructured bit streams over physical transmission media. |

---

## 3. Multiplexing, Demultiplexing & Ports

- **Port Numbers:** 16-bit integers (0 to 65535) identifying distinct application endpoints on a host.
  - Well-Known Ports (0–1023): e.g. Port 80 (HTTP), 443 (HTTPS), 53 (DNS), 22 (SSH).
  - Registered Ports (1024–49151): Assigned to specific user services.
  - Dynamic / Ephemeral Ports (49152–65535): Temporarily assigned to client sockets.
- **Socket Tuple:** A connection is uniquely identified by the 5-tuple:
  $$\langle \text{Source IP}, \text{Source Port}, \text{Dest IP}, \text{Dest Port}, \text{Protocol} \rangle$$

---

## 4. Common Misconceptions & Traps

| Misconception | Correction |
| :--- | :--- |
| **"Routers examine transport layer port numbers."** | In standard forwarding, routers are Layer 3 devices that inspect only **Layer 3 IP headers**. (NAT firewalls are special intermediate exceptions). |
| **"MAC address changes when traveling across the Internet."** | True! MAC addresses are hop-to-hop and change at every router hop. **IP addresses remain constant** end-to-end. |
| **"OSI Session and Presentation layers are separate protocols in the Internet."** | False. In the Internet architecture, session and presentation functions are implemented directly within the **Application Layer** (e.g. TLS in HTTPS). |
