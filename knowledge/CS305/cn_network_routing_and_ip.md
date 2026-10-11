# Network Layer: IP Addressing, Subnetting, and Routing Protocols

**Course ID:** `CS305`  
**Topic:** `Network Layer & Routing`  
**Learning Objective IDs:** `LO_IP_ADDRESSING`, `LO_ROUTING_ALGORITHMS`  
**Prerequisites:** `LO_LAYERS_OSI_TCPIP`

---

## 1. Core Concepts & Definitions

### IPv4 Addressing & CIDR
An IPv4 address is a 32-bit identifier typically written in dotted-decimal notation (`X.X.X.X`). In Classless Inter-Domain Routing (CIDR), an IP address is accompanied by a prefix length `/<prefix>` specifying the number of leading bits assigned to the network prefix:
$$\text{Total host capacity per subnet} = 2^{(32 - \text{prefix})} - 2$$
The subtraction of 2 accounts for:
1. **Network Address:** All host bits set to 0 (identifies the network segment).
2. **Directed Broadcast Address:** All host bits set to 1 (broadcasts to all hosts on the segment).

### Routing Protocols: Distance-Vector vs. Link-State

| Metric | Distance-Vector (e.g., RIP) | Link-State (e.g., OSPF) |
|---|---|---|
| **Underlying Algorithm** | Bellman-Ford | Dijkstra's Shortest Path First (SPF) |
| **Information Shared** | Distance vector (vector of costs to known destinations) | Complete state of all directly attached links (LSA) |
| **Exchange Scope** | Exchanged only with immediate physical neighbors | Flooded to all routers within the routing area |
| **Convergence Speed** | Slow; susceptible to count-to-infinity and routing loops | Fast; global topology map maintained independently |
| **Loop Mitigation** | Split Horizon, Poison Reverse, Holddown Timers | Loop-free SPF tree computed from synchronized LSDB |

---

## 2. Worked Examples

### Example 1: Subnetting a `/24` Network
**Problem:** An organization is assigned the block `192.168.10.0/24`. Allocate subnets to support:
- Subnet A: 60 hosts
- Subnet B: 28 hosts
- Subnet C: 12 hosts

**Step-by-Step Solution:**
1. **Subnet A (60 hosts):**
   - Need $2^h - 2 \ge 60 \implies 2^6 - 2 = 62 \ge 60$. Hence $h = 6$ host bits.
   - Prefix length $= 32 - 6 = /26$. Block size $= 2^6 = 64$.
   - **Range:** `192.168.10.0/26` (Network: `192.168.10.0`, Usable: `.1` to `.62`, Broadcast: `.63`).
2. **Subnet B (28 hosts):**
   - Next available boundary is `192.168.10.64`.
   - Need $2^h - 2 \ge 28 \implies 2^5 - 2 = 30 \ge 28$. Hence $h = 5$ host bits.
   - Prefix length $= 32 - 5 = /27$. Block size $= 32$.
   - **Range:** `192.168.10.64/27` (Network: `192.168.10.64`, Usable: `.65` to `.94`, Broadcast: `.95`).
3. **Subnet C (12 hosts):**
   - Next available boundary is `192.168.10.96`.
   - Need $2^h - 2 \ge 12 \implies 2^4 - 2 = 14 \ge 12$. Hence $h = 4$ host bits.
   - Prefix length $= 32 - 4 = /28$. Block size $= 16$.
   - **Range:** `192.168.10.96/28` (Network: `192.168.10.96`, Usable: `.97` to `.110`, Broadcast: `.111`).

---

## 3. Common Misconceptions & Corrections

- **Misconception:** "Routers forward packets using destination host IP addresses by looking up individual end machines in the global routing table."
  - **Correction:** Routers forward packets based on **longest prefix matching** against aggregated network prefixes (CIDR blocks), not individual host addresses. This prevents exponential explosion of routing tables.
- **Misconception:** "In Dijkstra SPF (Link-State), routers simply take the neighbor's word for the path cost."
  - **Correction:** In Link-State protocols, each router builds an identical Link-State Database (LSDB) representing the entire area graph, and then independently computes the shortest path tree rooted at itself using Dijkstra's algorithm.

---

## 4. Key Takeaways & Exam Summary

- CIDR replaces fixed classes (A, B, C) with flexible arbitrary-length prefixes, dramatically conserving IPv4 address space.
- Subnet mask bits set to 1 indicate the network/subnet portion; bits set to 0 denote assignable host addresses.
- Distance-vector protocols suffer from count-to-infinity and slow convergence; Link-state protocols exchange raw link states and compute loop-free shortest paths at the cost of higher memory and CPU utilization.
