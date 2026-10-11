# CS340 Database Management Systems — Transactions & Concurrency Control

**Course Code:** CS340  
**Topic:** TX_CONCURRENCY (Transactions & Concurrency Control)  
**Associated Learning Objectives:** `LO_TX_ACID`, `LO_TX_SERIALIZABILITY`, `LO_TX_LOCKING`  
**Prerequisites:** SQL Constraints & Relational Model (`LO_SQL_CONSTRAINTS`)  
**Authoritative References:** [Silberschatz et al., Chapter 14 & Chapter 15; ch17-Transaction.pdf]

---

## 1. Transaction Concept & ACID Guarantees

A transaction is a logical unit of work consisting of one or more database operations.
- **Atomicity (All-or-Nothing):** Either all operations of the transaction complete successfully, or all effects are undone (aborted/rolled back).
- **Consistency:** Execution of a transaction in isolation preserves database integrity constraints.
- **Isolation:** The concurrent execution of transactions results in a system state equivalent to some serial execution. Uncommitted changes are hidden from other concurrent transactions.
- **Durability:** Once a transaction commits, its updates persist permanently, surviving subsequent system crashes or power failures.

---

## 2. Concurrency & Conflict Serializability

### 2.1 Conflicting Operations
Two operations $I_i$ and $I_j$ belonging to transactions $T_i$ and $T_j$ ($i \ne j$) conflict if and only if:
1. They access the same data item $Q$.
2. **At least one** of the operations is a write operation ($\text{write}(Q)$).
- Read-Read does **not** conflict. Read-Write, Write-Read, and Write-Write do conflict.

### 2.2 Precedence Graph (Serialization Graph)
- **Construction:** A directed graph where vertices represent transactions. A directed edge $T_i \to T_j$ is drawn if an operation in $T_i$ conflicts with and executes before an operation in $T_j$.
- **Serializability Theorem:** A schedule $S$ is conflict serializable if and only if its precedence graph contains **no directed cycles**.
- The equivalent serial order is given by a **topological sort** of the precedence graph.

---

## 3. Concurrency Control Protocols: Two-Phase Locking (2PL)

To ensure conflict serializability dynamically without building precedence graphs at runtime, databases use locking protocols.

### 3.1 Lock Modes
- **Shared Lock ($S$):** Read access. Multiple transactions can hold shared locks simultaneously.
- **Exclusive Lock ($X$):** Read and write access. Only one transaction may hold an exclusive lock; all other requests are queued.

### 3.2 Basic Two-Phase Locking Rule
Each transaction executes in two distinct phases:
1. **Growing Phase:** The transaction may obtain locks, but cannot release any lock.
2. **Shrinking Phase:** The transaction may release locks, but cannot obtain any new locks.
- **Theorem:** Any schedule generated under 2PL is **guaranteed to be conflict serializable**.

### 3.3 Strict 2PL & Rigorous 2PL
- **Strict 2PL:** Requires all exclusive ($X$) locks to be held until the transaction commits or aborts. Prevents cascading rollbacks.
- **Rigorous 2PL:** Requires all locks ($S$ and $X$) to be held until commit or abort.

---

## 4. Common Misconceptions & Traps

| Misconception | Correction |
| :--- | :--- |
| **"Basic 2PL prevents deadlocks."** | False. Basic 2PL guarantees conflict serializability, but transactions can still deadlock (e.g. $T_1$ holds lock on $A$ waiting for $B$, while $T_2$ holds lock on $B$ waiting for $A$). |
| **"Two reads on the same item conflict."** | False. Read-Read operations are concurrent and conflict-free. At least one operation must be a `write` to create a conflict. |
| **"Serializability requires executing transactions one at a time."** | False. Concurrent interleaved execution is permitted as long as the net outcome is **equivalent** to a serial execution. |
