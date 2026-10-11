# CS301 Operating Systems & Concurrency — Process Lifecycle, PCB & Threads

**Course Code:** CS301  
**Topic:** OS_PROC_SCHED (Process Management & CPU Scheduling)  
**Associated Learning Objectives:** `LO_OS_PROCESS`, `LO_OS_THREADS`  
**Prerequisites:** Computer Architecture & Assembly Basics  
**Authoritative References:** [Silberschatz, Galvin & Gagne, Chapters 3 & 4; ch1.pptx, ch2.pptx]

---

## 1. Process Concept & Lifecycle

A **process** is an active program in execution.
- It comprises the program code (text section), current activity represented by the Program Counter (PC), processor registers, process stack (temporary data like function parameters, return addresses, local variables), and data section (global variables).

### 1.1 Process States
A process transitions through the following states:
1. **New:** The process is being created.
2. **Ready:** The process is in memory waiting to be assigned to a processor.
3. **Running:** Instructions are currently executing on a CPU core.
4. **Waiting (Blocked):** The process is waiting for some external event (e.g. I/O completion or signal).
5. **Terminated:** The process has finished execution and OS resources are reclaimed.

### 1.2 Process Control Block (PCB)
Each process is represented in the operating system by a PCB containing:
- Process state (New, Ready, Running, Waiting, Terminated)
- Program counter (location of next instruction to execute)
- CPU registers (accumulators, index registers, stack pointers)
- CPU-scheduling information (priority, scheduling queue pointers)
- Memory-management information (base and limit registers, page tables)
- Accounting information (CPU time used, time limits)
- I/O status information (list of allocated I/O devices, open file tables)

---

## 2. Context Switching

A **context switch** is the mechanism of saving the state of the currently executing process and loading the saved state of another process so execution can be resumed from the exact same point.
- **Overhead:** Context switches are pure overhead; the system does no useful application work while switching.
- **Hardware Support:** State saving is optimized by hardware registers and memory management units (MMUs).

---

## 3. Threads & Concurrency Models

A **thread** is a basic unit of CPU utilization consisting of a thread ID, program counter, register set, and a stack.
- It shares with other threads in the same process:
  - Code section
  - Data section
  - Operating system resources (open files, signals)
- **Advantages:** Responsiveness, resource sharing, economy (threads have much lower creation and context-switch overhead than processes), scalability on multiprocessor architectures.
- **Multithreading Models:**
  - *Many-to-One:* Many user threads mapped to one kernel thread (efficient, but blocks entire process if one thread blocks).
  - *One-to-One:* Each user thread mapped to a kernel thread (provides true parallelism; standard in Linux and Windows).
  - *Many-to-Many:* Many user threads multiplexed across an equal or smaller number of kernel threads.

---

## 4. Common Misconceptions & Traps

| Misconception | Correction |
| :--- | :--- |
| **"Threads in the same process share separate address spaces."** | False. All threads in a process **share the same address space**, code, heap, and open files. Only the stack and registers are thread-private. |
| **"A blocked process consumes CPU cycles in a spinlock."** | In a proper OS, a waiting process is placed in an I/O or event queue and its PCB state is set to `Waiting`. It consumes **zero CPU cycles** until woken by an interrupt. |
| **"Creating a thread has the same cost as `fork()`."** | False. Thread creation is significantly lighter because it reuses existing memory mappings, file descriptors, and address tables. |
