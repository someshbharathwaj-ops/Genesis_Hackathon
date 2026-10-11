# CS301 Operating Systems & Concurrency — Concurrency, Semaphores & Synchronization

**Course Code:** CS301  
**Topic:** OS_SYNCH (Concurrency & Process Synchronization)  
**Associated Learning Objectives:** `LO_OS_SYNCHRONIZATION`, `LO_OS_SEMAPHORES`, `LO_OS_CLASSICAL_PROBLEMS`  
**Prerequisites:** Process Lifecycle & Threads (`LO_OS_PROCESS`, `LO_OS_THREADS`)  
**Authoritative References:** [Silberschatz, Galvin & Gagne, Chapters 5 & 6; Synchronization Problems.docx, Critical_Section_Executable_Programs.docx]

---

## 1. The Critical-Section Problem

Concurrent access to shared data can lead to data inconsistency. A **race condition** occurs when multiple processes access and manipulate the same shared memory concurrently and the outcome of the execution depends on the specific order in which access takes place.

### 1.1 Requirements for Solution to Critical-Section Problem
Any valid solution to the critical-section problem must satisfy three essential criteria:
1. **Mutual Exclusion:** If process $P_i$ is executing in its critical section, then no other processes can be executing in their critical sections.
2. **Progress:** If no process is executing in its critical section and there are some processes that wish to enter their critical sections, only those processes that are not executing in their remainder sections can participate in deciding which will enter next, and this selection cannot be postponed indefinitely.
3. **Bounded Waiting:** There exists a bound on the number of times that other processes are allowed to enter their critical sections after a process has made a request to enter its critical section and before that request is granted.

---

## 2. Peterson's Algorithm

Peterson's solution is a classic software-based solution for two processes ($P_0$ and $P_1$) sharing variables:
```c
int turn;
boolean flag[2]; // flag[i] = true means P_i is ready to enter
```

### Protocol for Process $P_i$ ($j = 1 - i$):
```c
do {
    flag[i] = true;
    turn = j;
    while (flag[j] && turn == j); // Busy wait (spin)

    // CRITICAL SECTION

    flag[i] = false;

    // REMAINDER SECTION
} while (true);
```
- **Proof:**
  - Mutual exclusion is preserved because $P_i$ can enter only if `flag[j] == false` or `turn == i`. Since `turn` can only hold one value at a time, both cannot enter simultaneously.
  - Progress and bounded waiting are satisfied because `turn` prioritizes the other process.

---

## 3. Semaphores & Synchronization Primitives

A **semaphore** $S$ is an integer variable accessed only through two atomic operations: `wait()` ($P$) and `signal()` ($V$).

### 3.1 Primitive Definitions
```c
wait(S) {
    while (S <= 0); // or block on semaphore queue
    S--;
}

signal(S) {
    S++;
}
```

### 3.2 Counting vs Binary Semaphores
- **Binary Semaphore (Mutex):** Value can range only between 0 and 1. Used to ensure mutual exclusion.
- **Counting Semaphore:** Value can range over an unrestricted domain. Used to control access to a given resource consisting of a finite number of instances.

---

## 4. Classical Synchronization Problems

1. **Bounded-Buffer Problem (Producer-Consumer):** Uses `mutex = 1`, `empty = N`, `full = 0`.
2. **Readers-Writers Problem:** Prevents writer starvation while allowing multiple simultaneous readers.
3. **Dining Philosophers Problem:** Illustrates allocation of several resources among several processes in a deadlock-free and starvation-free manner.

---

## 5. Common Misconceptions & Traps

| Misconception | Correction |
| :--- | :--- |
| **"`turn = i` solves the critical section problem."** | If only a turn variable is used, strict alternation is enforced. If $P_0$ never wants to enter, $P_1$ is permanently blocked from entering, violating **Progress**. |
| **"Binary semaphores and mutexes are identical in all implementations."** | While mathematically similar, mutexes enforce **ownership** (only the thread that locked the mutex can unlock it); binary semaphores can be signaled by a different thread (e.g. for signaling completion). |
| **"Disabling interrupts is suitable for user-space synchronization."** | Disabling interrupts on a multiprocessor is extremely slow and only permissible in kernel space on single-core architectures. |
