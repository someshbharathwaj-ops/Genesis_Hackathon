# CS305 Computer Networks — Transport Layer Protocols (TCP, UDP & Congestion Control)

**Course Code:** CS305  
**Topic:** CS305_TRANSPORT (Transport Protocols & Flow Control)  
**Associated Learning Objectives:** `LO_CS305_FOUNDATIONS`, `LO_CS305_APPLICATION`  
**Prerequisites:** Layered Architecture (`LO_CS305_FOUNDATIONS`)  
**Authoritative References:** [Kurose & Ross, Chapter 3; RFC 793, RFC 5681]

---

## 1. TCP vs UDP Design Trade-offs

| Dimension | Transmission Control Protocol (TCP) | User Datagram Protocol (UDP) |
| :--- | :--- | :--- |
| **Connection State** | Connection-oriented (3-way handshake) | Connectionless (no state maintained) |
| **Reliability** | Guaranteed in-order delivery via ACKs & retransmission | Unreliable, best-effort (packets may drop or arrive out of order) |
| **Flow Control** | Yes (Receive Window advertised by receiver) | None |
| **Congestion Control** | Yes (AIMD, Slow Start, Fast Recovery) | None |
| **Header Overhead** | 20 to 60 bytes | Strictly 8 bytes |
| **Typical Use Cases** | Web (HTTP), Email (SMTP), File Transfer (FTP), SSH | DNS, VoIP, Video Streaming, Real-time Gaming |

---

## 2. TCP Connection Lifecycle & 3-Way Handshake

### 2.1 Three-Way Handshake (Establishment)
1. **Client $\to$ Server:** `SYN` packet ($seq = x$). State: `SYN_SENT`.
2. **Server $\to$ Client:** `SYN-ACK` packet ($seq = y$, $ack = x + 1$). State: `SYN_RCVD`.
3. **Client $\to$ Server:** `ACK` packet ($seq = x + 1$, $ack = y + 1$). State: `ESTABLISHED`.

### 2.2 Connection Teardown (Four-Way Handshake)
1. Active closer sends `FIN` ($seq = u$).
2. Receiver sends `ACK` ($ack = u + 1$).
3. Receiver finishes sending remaining data and sends its own `FIN` ($seq = v$).
4. Active closer sends `ACK` ($ack = v + 1$) and enters `TIME_WAIT` (2MSL duration) to guarantee the final ACK is received before port reuse.

---

## 3. TCP Flow & Congestion Control

### 3.1 Flow Control vs Congestion Control
- **Flow Control:** Prevents the sender from overwhelming the **receiver's buffer**. Controlled by `rwnd` (Receive Window).
- **Congestion Control:** Prevents the sender from overwhelming the **network routers and links**. Controlled by `cwnd` (Congestion Window).
- Effective transmission window: $W = \min(\text{cwnd}, \text{rwnd})$.

### 3.2 Additive Increase Multiplicative Decrease (AIMD)
- **Slow Start:** Starts with $\text{cwnd} = 1 \text{ MSS}$; doubles every RTT ($2, 4, 8, \dots$) until threshold $\text{ssthresh}$ is reached.
- **Congestion Avoidance:** Once $\text{cwnd} \ge \text{ssthresh}$, increases linearly by $1 \text{ MSS}$ per RTT.
- **On Loss (Triple Duplicate ACKs):** Fast Retransmit triggers; $\text{ssthresh} = \text{cwnd} / 2$; cuts $\text{cwnd}$ in half (Multiplicative Decrease).
- **On Timeout:** Severe congestion assumed; $\text{ssthresh} = \text{cwnd} / 2$, and $\text{cwnd}$ resets to $1 \text{ MSS}$.

---

## 4. Common Misconceptions & Traps

| Misconception | Correction |
| :--- | :--- |
| **"UDP provides no error detection."** | False. UDP includes an optional 16-bit **checksum** in its 8-byte header to detect bit errors in the payload. |
| **"Flow control detects lost packets in routers."** | False. Flow control is end-to-end between sender and receiver. Link/router congestion is handled by **Congestion Control**. |
| **"SYN packets contain application data."** | False. The initial `SYN` packet contains zero payload bytes, but consumes one logical sequence number. |
