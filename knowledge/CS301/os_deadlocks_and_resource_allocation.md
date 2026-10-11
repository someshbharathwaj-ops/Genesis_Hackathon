# CS301 Operating Systems & Concurrency — Deadlocks & Resource Allocation

**Course Code:** CS301  
**Topic:** OS_DEADLOCK (Deadlocks & Resource Allocation)  
**Associated Learning Objectives:** `LO_OS_DEADLOCKS`, `LO_OS_RAG`, `LO_OS_BANKER`  
**Prerequisites:** Concurrency & Semaphores (`LO_OS_SYNCHRONIZATION`, `LO_OS_SEMAPHORES`)  
**Authoritative References:** [Silberschatz, Galvin & Gagne, Chapters 7 & 8; ch3.pptx]

---

## 1. Deadlock Concept & The Four Coffman Conditions

A **deadlock** is a situation where every process in a set of processes is waiting for an event that can only be caused by another process in the set.

### 1.1 The Four Necessary Coffman Conditions
Deadlock can arise if and only if all four conditions hold simultaneously in the system:
1. **Mutual Exclusion:** At least one resource must be held in a non-shareable mode (only one process can use it at a time).
2. **Hold and Wait:** A process must be holding at least one resource and waiting to acquire additional resources that are currently held by other processes.
3. **No Preemption:** Resources cannot be preempted; a resource can be released only voluntarily by the process holding it, after that process has completed its task.
4. **Circular Wait:** A closed chain of processes $\{P_0, P_1, \dots, P_n\}$ exists such that $P_0$ is waiting for a resource held by $P_1$, $P_1$ is waiting for a resource held by $P_2$, $\dots$, and $P_n$ is waiting for a resource held by $P_0$.

---

## 2. Resource Allocation Graphs (RAG)

A directed graph used to depict the allocation state of system resources:
- Vertices $V = P \cup R$, where $P = \{P_1, \dots, P_n\}$ are processes and $R = \{R_1, \dots, R_m\}$ are resource types.
- **Request Edge:** Directed edge $P_i \to R_j$ signifies that process $P_i$ has requested an instance of resource type $R_j$.
- **Assignment Edge:** Directed edge $R_j \to P_i$ signifies that an instance of resource type $R_j$ has been allocated to process $P_i$.

### 2.1 Cycle Detection Theorem
- If the Resource Allocation Graph contains **no cycles**, the system is **not in a deadlocked state**.
- If the graph **contains a cycle**:
  - If every resource type has **only one instance**, a cycle is **necessary and sufficient** for deadlock.
  - If some resource types have **multiple instances**, a cycle indicates a *potential* deadlock, but does **not guarantee** that deadlock has occurred.

---

## 3. Deadlock Avoidance: The Banker's Algorithm

The Banker's Algorithm evaluates resource requests dynamically to ensure the system never transitions into an **unsafe state**.
- **Safe State:** A state where there exists at least one safe sequence $\langle P_1, P_2, \dots, P_n \rangle$ such that for each $P_i$, the resources that $P_i$ can still request can be satisfied by currently available resources plus resources held by all preceding $P_j$ ($j < i$).

### 3.1 Data Structures ($n$ processes, $m$ resources)
- $\text{Available}[m]$: Available instances of each resource type.
- $\text{Max}[n][m]$: Maximum demand of each process.
- $\text{Allocation}[n][m]$: Resources currently allocated to each process.
- $\text{Need}[n][m] = \text{Max}[n][m] - \text{Allocation}[n][m]$: Remaining resources needed by each process.

### 3.2 Safety Algorithm Steps
1. Let $\text{Work} = \text{Available}$ and $\text{Finish}[i] = \text{False}$ for $i = 0, \dots, n-1$.
2. Find an index $i$ such that $\text{Finish}[i] == \text{False}$ and $\text{Need}[i] \le \text{Work}$. If no such $i$ exists, go to step 4.
3. $\text{Work} = \text{Work} + \text{Allocation}[i]$; $\text{Finish}[i] = \text{True}$; return to step 2.
4. If $\text{Finish}[i] == \text{True}$ for all $i$, the system is in a **safe state**.

---

## 4. Common Misconceptions & Traps

| Misconception | Correction |
| :--- | :--- |
| **"An unsafe state is a deadlocked state."** | False. An unsafe state is **not** necessarily deadlocked; it is merely a state from which the OS cannot prevent processes from eventually deadlocking if worst-case requests occur. |
| **"A cycle in a multi-instance RAG proves deadlock."** | False. In multi-instance graphs, another process not in the cycle can release an instance of the requested resource, breaking the wait chain. |
| **"Breaking one Coffman condition is insufficient."** | False. To prevent deadlock, it is sufficient to eliminate **any one** of the four necessary Coffman conditions. |
