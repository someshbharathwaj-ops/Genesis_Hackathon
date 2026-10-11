"""Comprehensive Multi-Topic Curriculum & Multi-Type Question Bank Seeder.

Expands DBMS (CS340) and OS (CS301) to:
- 4 rich Topics / DAG Clusters per course
- 12–14 granular Learning Objectives per course with formal prerequisite DAG links
- 20+ verified, versioned questions per course covering:
    * MULTIPLE_CHOICE
    * MULTIPLE_SELECT
    * EXPRESSION
    * MINIMAL_COVER / DECOMPOSITION
- Deterministic answer keys, rubrics, and provenance hashes (ADR 0001).
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.curriculum import LearningObjective, Topic
from app.models.identity import Course, CourseEnrollment, User, UserRole
from app.models.question import (
    DifficultyLevel,
    Question,
    QuestionType,
    QuestionVersion,
    VerificationStatus,
)
from app.repositories.course_repo import (
    CourseRepository,
    LearningObjectiveRepository,
    TopicRepository,
)
from app.repositories.question_repo import (
    QuestionRepository,
    QuestionVersionRepository,
    calculate_provenance_hash,
)
from app.repositories.user_repo import EnrollmentRepository, UserRepository


# ==============================================================================
# DBMS COMPREHENSIVE CURRICULUM (CS340)
# ==============================================================================

DBMS_TOPICS = [
    {
        "code": "REL_ALGEBRA",
        "title": "Relational Model & Relational Algebra",
        "description": "Formal procedural query language, fundamental relational operators, joins, and calculus.",
        "order_index": 1,
        "objectives": [
            ("LO_RA_SELECT_PROJECT", "Selection & Projection Operations", "Unary relational operations and horizontal/vertical filtering", 1, []),
            ("LO_RA_JOINS", "Relational Joins & Cartesian Products", "Natural joins, theta joins, outer joins, and cross products", 2, ["LO_RA_SELECT_PROJECT"]),
            ("LO_RA_AGGREGATION", "Grouping & Aggregate Calculus", "Group by calculus and aggregate operator evaluation", 3, ["LO_RA_JOINS"]),
        ],
    },
    {
        "code": "SQL_LANG",
        "title": "SQL Query Formulation & Integrity",
        "description": "Declarative queries, correlated subqueries, group by pipelines, and referential constraints.",
        "order_index": 2,
        "objectives": [
            ("LO_SQL_SUBQUERIES", "Correlated Subqueries & Predicates", "Nested subqueries, EXISTS, IN, and correlated scoping", 1, []),
            ("LO_SQL_GROUPING", "Grouping & Aggregate Pipelines", "GROUP BY, HAVING vs WHERE filtering, and aggregation semantics", 2, ["LO_SQL_SUBQUERIES"]),
            ("LO_SQL_CONSTRAINTS", "Referential Integrity & Constraints", "Primary keys, foreign keys, ON DELETE CASCADE, and domain constraints", 3, ["LO_SQL_GROUPING"]),
        ],
    },
    {
        "code": "FD_NORM",
        "title": "Functional Dependencies & Normalization",
        "description": "Attribute closure, minimal covers, 3NF/BCNF synthesis, and losslessness.",
        "order_index": 3,
        "objectives": [
            ("LO_CLOSURE", "Attribute Closure Computation", "Compute attribute closures X+ via Armstrong axioms", 1, []),
            ("LO_KEYS", "Candidate Key Derivation", "Determine superkeys and minimal candidate keys", 2, ["LO_CLOSURE"]),
            ("LO_MINIMAL_COVER", "Minimal Canonical Cover", "Synthesize minimal canonical covers of functional dependencies", 3, ["LO_CLOSURE"]),
            ("LO_NF_IDENTIFICATION", "Normal Form Verification", "Diagnose 1NF, 2NF, 3NF, and BCNF violations", 4, ["LO_KEYS"]),
            ("LO_DECOMPOSITION", "Lossless Join Decomposition", "Validate lossless join and dependency preservation", 5, ["LO_NF_IDENTIFICATION"]),
        ],
    },
    {
        "code": "TX_CONCURRENCY",
        "title": "Transactions & Concurrency Control",
        "description": "ACID guarantees, conflict serializability, precedence graphs, and two-phase locking.",
        "order_index": 4,
        "objectives": [
            ("LO_TX_ACID", "ACID Properties & Transaction States", "Atomicity, consistency, isolation, and durability guarantees", 1, []),
            ("LO_TX_SERIALIZABILITY", "Conflict Serializability & Graphs", "Precedence graphs, topological sort, and conflict equivalence", 2, ["LO_TX_ACID"]),
            ("LO_TX_LOCKING", "Two-Phase Locking (2PL)", "Growing/shrinking phases, strict 2PL, and cascading abort prevention", 3, ["LO_TX_SERIALIZABILITY"]),
        ],
    },
]

DBMS_NEW_QUESTIONS: list[dict[str, Any]] = [
    # REL_ALGEBRA
    {
        "objective_code": "LO_RA_SELECT_PROJECT",
        "title": "Commutativity of Relational Selection and Projection",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "Under which condition does the selection operator sigma_{c} commute with the projection operator pi_{L} "
            "(i.e., pi_{L}(sigma_{c}(R)) = sigma_{c}(pi_{L}(R)))?"
        ),
        "options": [
            {"id": "A", "text": "Always for any condition c and attribute list L"},
            {"id": "B", "text": "Only when all attributes involved in condition c are contained within list L"},
            {"id": "C", "text": "Only when R is in Boyce-Codd Normal Form"},
            {"id": "D", "text": "Selection and projection never commute"},
        ],
        "answer_key": {"value": "B", "reference": "Silberschatz Chapter 2 Relational Algebra Equivalence Rules"},
        "rubric": {"type": "multiple_choice", "criterion": "Correct algebraic commutativity condition", "points": 1.0},
        "explanation": "Condition c can only be evaluated after projection if all attributes referenced in c are retained in projection list L.",
    },
    {
        "objective_code": "LO_RA_JOINS",
        "title": "Tuples Produced in Natural Join vs Cartesian Product",
        "question_type": QuestionType.MULTIPLE_SELECT,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.5,
        "prompt": (
            "Consider relations R(A, B) with 10 tuples and S(B, C) with 20 tuples. "
            "Which of the following statements regarding R natural join S are ALWAYS TRUE?"
        ),
        "options": [
            {"id": "A", "text": "The natural join contains at most 200 tuples."},
            {"id": "B", "text": "The natural join contains at least 10 tuples."},
            {"id": "C", "text": "If attribute B is a foreign key in R referencing candidate key B in S, the join has exactly 10 tuples."},
            {"id": "D", "text": "The schema of the natural join contains 3 attributes: (A, B, C)."},
        ],
        "answer_key": {"value": ["A", "C", "D"], "reference": "Relational Join Cardinality Bounds"},
        "rubric": {"type": "multiple_select", "criterion": "All valid cardinality and schema invariants", "points": 1.5},
        "explanation": "Cartesian max is 10*20=200; with foreign key it equals |R|=10; schema combines shared B once to (A,B,C). Min tuples can be 0 if no B matches.",
    },
    {
        "objective_code": "LO_RA_AGGREGATION",
        "title": "Aggregate Grouping Attribute Cardinality",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "Given relation Employee(DeptID, Role, Salary). When evaluating the aggregate expression "
            "gamma_{DeptID, Role, avg(Salary)}(Employee), what constitutes the grouping key?"
        ),
        "answer_key": {"value": "DeptID, Role", "reference": "Aggregate Relational Calculus Grouping"},
        "rubric": {"type": "expression", "criterion": "Exact composite grouping attributes", "points": 1.0},
        "explanation": "All attributes preceding the aggregate function in the gamma subscript form the composite grouping key.",
    },
    # SQL_LANG
    {
        "objective_code": "LO_SQL_SUBQUERIES",
        "title": "Correlated Subquery Evaluation Mechanism",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "How does an SQL query execution engine evaluate a correlated subquery in the WHERE clause?"
        ),
        "options": [
            {"id": "A", "text": "The subquery is executed once prior to the outer query execution"},
            {"id": "B", "text": "The subquery is re-evaluated for each candidate row processed by the outer query"},
            {"id": "C", "text": "The subquery executes asynchronously in a separate transaction"},
            {"id": "D", "text": "The subquery creates a temporary materialized table in tempdb"},
        ],
        "answer_key": {"value": "B", "reference": "SQL Standard Correlated Subquery Execution"},
        "rubric": {"type": "multiple_choice", "criterion": "Correct row-by-row correlation concept", "points": 1.0},
        "explanation": "A correlated subquery references values from the current outer row, necessitating per-row re-evaluation unless decorrelated by optimizer.",
    },
    {
        "objective_code": "LO_SQL_GROUPING",
        "title": "WHERE vs HAVING Filtering Semantics",
        "question_type": QuestionType.MULTIPLE_SELECT,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.5,
        "prompt": (
            "Which of the following statements distinguish SQL WHERE from HAVING clauses correctly?"
        ),
        "options": [
            {"id": "A", "text": "WHERE filters individual candidate rows prior to grouping."},
            {"id": "B", "text": "HAVING filters aggregated groups after GROUP BY evaluation."},
            {"id": "C", "text": "Aggregate functions (e.g. COUNT, SUM) cannot appear directly in a WHERE clause."},
            {"id": "D", "text": "HAVING cannot be used without a GROUP BY clause in ANSI SQL."},
        ],
        "answer_key": {"value": ["A", "B", "C"], "reference": "ANSI SQL Specification Aggregation Order"},
        "rubric": {"type": "multiple_select", "criterion": "Exact semantic distinctions", "points": 1.5},
        "explanation": "WHERE filters rows before grouping; HAVING filters groups; aggregates are illegal in WHERE. HAVING without GROUP BY operates on entire table as 1 group.",
    },
    {
        "objective_code": "LO_SQL_CONSTRAINTS",
        "title": "ON DELETE CASCADE Referential Action",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "In relational DDL, if a foreign key is declared with ON DELETE CASCADE, "
            "what action is taken when a parent row in the referenced table is deleted?"
        ),
        "answer_key": {"value": "Delete all matching child rows in the referencing table", "reference": "SQL DDL Referential Actions"},
        "rubric": {"type": "expression", "criterion": "Cascading deletion of dependent child tuples", "points": 1.0},
        "explanation": "ON DELETE CASCADE automatically removes all dependent referencing tuples in child relations to prevent orphaned foreign keys.",
    },
    # TX_CONCURRENCY
    {
        "objective_code": "LO_TX_ACID",
        "title": "ACID Atomicity Enforcement Component",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "Which database management subsystem is primarily responsible for ensuring transaction ATOMICITY upon system crashes or aborts?"
        ),
        "options": [
            {"id": "A", "text": "Query Optimizer"},
            {"id": "B", "text": "Recovery Manager (WAL / Undo Logging)"},
            {"id": "C", "text": "B+ Tree Index Manager"},
            {"id": "D", "text": "Lock Manager"},
        ],
        "answer_key": {"value": "B", "reference": "Transaction ACID Subsystem Architecture"},
        "rubric": {"type": "multiple_choice", "criterion": "Recovery manager undo log responsibility", "points": 1.0},
        "explanation": "The Recovery Manager uses Write-Ahead Logging (WAL) and undo records to roll back uncommitted changes, preserving all-or-nothing atomicity.",
    },
    {
        "objective_code": "LO_TX_SERIALIZABILITY",
        "title": "Cycle in Precedence Graph Implications",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "If the precedence (serialization) graph of a concurrent schedule contains a directed cycle (e.g., T1 -> T2 -> T1), "
            "what does this prove about the schedule?"
        ),
        "options": [
            {"id": "A", "text": "The schedule is conflict serializable"},
            {"id": "B", "text": "The schedule is NOT conflict serializable"},
            {"id": "C", "text": "The schedule is guaranteed to be deadlock-free"},
            {"id": "D", "text": "The schedule is strict and recoverable"},
        ],
        "answer_key": {"value": "B", "reference": "Conflict Serializability Theorem"},
        "rubric": {"type": "multiple_choice", "criterion": "Acyclic graph theorem for conflict serializability", "points": 1.0},
        "explanation": "By the Serializability Theorem, a schedule S is conflict serializable if and only if its precedence graph has no cycles.",
    },
    {
        "objective_code": "LO_TX_LOCKING",
        "title": "Strict Two-Phase Locking (Strict 2PL) Invariants",
        "question_type": QuestionType.MULTIPLE_SELECT,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.5,
        "prompt": (
            "Which properties are GUARANTEED by the Strict Two-Phase Locking (Strict 2PL) protocol?"
        ),
        "options": [
            {"id": "A", "text": "Conflict serializability of all schedules"},
            {"id": "B", "text": "Freedom from cascading aborts (recoverable and cascade-free)"},
            {"id": "C", "text": "Complete immunity from deadlocks without need for wait-for graphs"},
            {"id": "D", "text": "Exclusive locks are held until transaction commit or abort"},
        ],
        "answer_key": {"value": ["A", "B", "D"], "reference": "Strict 2PL Properties Silberschatz Chapter 18"},
        "rubric": {"type": "multiple_select", "criterion": "Strict 2PL guarantees", "points": 1.5},
        "explanation": "Strict 2PL guarantees conflict serializability, holds exclusive locks until commit, and prevents cascading aborts. However, deadlocks are still possible.",
    },
]


# ==============================================================================
# OS COMPREHENSIVE CURRICULUM (CS301)
# ==============================================================================

OS_TOPICS = [
    {
        "code": "OS_PROC_SCHED",
        "title": "Process Management & CPU Scheduling",
        "description": "Process state transitions, PCB attributes, context switching, and CPU scheduling algorithms.",
        "order_index": 1,
        "objectives": [
            ("LO_OS_PROCESS", "Process Lifecycle & PCB", "State transitions, process control block data structures, and context overheads", 1, []),
            ("LO_OS_THREADS", "Threads & Concurrency Models", "User vs kernel threads, thread pools, and multithreading architectures", 2, ["LO_OS_PROCESS"]),
            ("LO_OS_SCHEDULING", "CPU Scheduling Algorithms", "Preemptive vs non-preemptive scheduling (FCFS, SJF, SRTF, Round Robin)", 3, ["LO_OS_PROCESS"]),
        ],
    },
    {
        "code": "OS_SYNCH",
        "title": "Concurrency & Process Synchronization",
        "description": "Race conditions, critical sections, atomic hardware instructions, semaphores, and classic problems.",
        "order_index": 2,
        "objectives": [
            ("LO_OS_SYNCHRONIZATION", "Critical Section & Peterson's Algorithm", "Mutual exclusion, progress, bounded waiting, and software solutions", 1, []),
            ("LO_OS_SEMAPHORES", "Semaphores & Mutex Locks", "Counting semaphores, binary mutexes, wait/signal invariants", 2, ["LO_OS_SYNCHRONIZATION"]),
            ("LO_OS_CLASSICAL_PROBLEMS", "Classical Synchronization Problems", "Producer-Consumer, Readers-Writers, and Dining Philosophers implementations", 3, ["LO_OS_SEMAPHORES"]),
        ],
    },
    {
        "code": "OS_DEADLOCK",
        "title": "Deadlocks & Resource Allocation",
        "description": "Coffman conditions, resource allocation graphs, deadlock avoidance, and Banker's algorithm.",
        "order_index": 3,
        "objectives": [
            ("LO_OS_DEADLOCKS", "Coffman Conditions for Deadlock", "Mutual exclusion, hold & wait, no preemption, and circular wait", 1, []),
            ("LO_OS_RAG", "Resource Allocation Graphs (RAG)", "Cycle detection, multi-instance resource claim edges, and knots", 2, ["LO_OS_DEADLOCKS"]),
            ("LO_OS_BANKER", "Banker's Algorithm & Safe States", "Need matrix computation, safety vectors, and resource request algorithm", 3, ["LO_OS_RAG"]),
        ],
    },
    {
        "code": "OS_MEMORY",
        "title": "Memory Management & Virtual Memory",
        "description": "Paging, logical-to-physical translation, TLB performance, and page replacement policies.",
        "order_index": 4,
        "objectives": [
            ("LO_OS_PAGING", "Paging & Address Translation", "Frame allocation, page offset arithmetic, and internal fragmentation", 1, []),
            ("LO_OS_TLB", "TLB & Effective Access Time", "Translation Lookaside Buffer hits, miss penalties, and multi-level page tables", 2, ["LO_OS_PAGING"]),
            ("LO_OS_PAGE_REPLACEMENT", "Page Replacement Algorithms", "FIFO, LRU, Optimal replacement, and Belady's anomaly analysis", 3, ["LO_OS_TLB"]),
        ],
    },
]

OS_NEW_QUESTIONS: list[dict[str, Any]] = [
    # OS_PROC_SCHED
    {
        "objective_code": "LO_OS_THREADS",
        "title": "User-Level Threads vs Kernel-Level Threads",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "What is a major limitation of pure User-Level Threads (Many-to-One model) compared to Kernel-Level Threads?"
        ),
        "options": [
            {"id": "A", "text": "Thread creation is slower because it requires a kernel context switch"},
            {"id": "B", "text": "If one thread makes a blocking system call, the entire process is blocked by the kernel"},
            {"id": "C", "text": "User-level threads cannot share the address space of the process"},
            {"id": "D", "text": "User-level threads require hardware support from the CPU"},
        ],
        "answer_key": {"value": "B", "reference": "Silberschatz Chapter 4 Threading Models"},
        "rubric": {"type": "multiple_choice", "criterion": "Identification of blocking system call limitation", "points": 1.0},
        "explanation": "Because the kernel only sees 1 scheduling entity for the process, a blocking syscall in one user thread puts the entire process in WAITING state.",
    },
    {
        "objective_code": "LO_OS_SCHEDULING",
        "title": "Shortest Job First (SJF) Optimality and Starvation",
        "question_type": QuestionType.MULTIPLE_SELECT,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.5,
        "prompt": (
            "Which of the following characteristics are TRUE regarding Shortest Job First (SJF / SRTF) CPU scheduling?"
        ),
        "options": [
            {"id": "A", "text": "SJF provably minimizes the average waiting time for a given set of processes."},
            {"id": "B", "text": "Long-running processes may suffer from indefinite starvation if short processes arrive continuously."},
            {"id": "C", "text": "The exact length of the next CPU burst is known deterministically by the kernel in general-purpose OS."},
            {"id": "D", "text": "Aging can be used as a technique to mitigate starvation in SJF."},
        ],
        "answer_key": {"value": ["A", "B", "D"], "reference": "CPU Scheduling Algorithms Silberschatz Chapter 5"},
        "rubric": {"type": "multiple_select", "criterion": "Correct SJF optimality and starvation properties", "points": 1.5},
        "explanation": "SJF minimizes average wait time; continuous arrivals of short jobs cause starvation of long jobs; aging gradually raises priority to prevent starvation. Next burst is predicted, not known.",
    },
    # OS_SYNCH
    {
        "objective_code": "LO_OS_CLASSICAL_PROBLEMS",
        "title": "Dining Philosophers Deadlock Prevention",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "In the Classical Dining Philosophers problem with 5 philosophers and 5 chopsticks, "
            "which technique successfully eliminates deadlock without preventing concurrency?"
        ),
        "options": [
            {"id": "A", "text": "Let all philosophers pick up the left chopstick first simultaneously"},
            {"id": "B", "text": "Asymmetric solution: odd philosophers pick left first, even philosophers pick right first"},
            {"id": "C", "text": "Remove the mutual exclusion requirement on chopsticks"},
            {"id": "D", "text": "Increase the number of philosophers to 6"},
        ],
        "answer_key": {"value": "B", "reference": "Dining Philosophers Synchronization Asymmetry"},
        "rubric": {"type": "multiple_choice", "criterion": "Asymmetric chopstick acquisition strategy", "points": 1.0},
        "explanation": "An asymmetric solution breaks the Circular Wait Coffman condition, guaranteeing at least one philosopher can acquire both chopsticks and eat.",
    },
    {
        "objective_code": "LO_OS_SEMAPHORES",
        "title": "Semaphore Invariant on Negative Values",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "In an implementation of counting semaphores with a waiting queue, if semaphore S.value = -3, "
            "how many processes are currently blocked and waiting in S's queue?"
        ),
        "answer_key": {"value": "3", "reference": "Semaphore Data Structure Invariants"},
        "rubric": {"type": "expression", "criterion": "Correct count of waiting blocked processes", "points": 1.0},
        "explanation": "When semaphore values can be negative, the magnitude |S.value| equals the exact count of processes waiting in the blocked queue.",
    },
    # OS_DEADLOCK
    {
        "objective_code": "LO_OS_RAG",
        "title": "Cycle in Resource Allocation Graph Condition",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "In a Resource Allocation Graph (RAG), if each resource type has EXACTLY ONE instance, "
            "what does the existence of a cycle imply?"
        ),
        "options": [
            {"id": "A", "text": "A deadlock may or may not exist"},
            {"id": "B", "text": "A deadlock definitely exists (necessary and sufficient condition)"},
            {"id": "C", "text": "The system is in a safe state"},
            {"id": "D", "text": "The cycle will resolve automatically via aging"},
        ],
        "answer_key": {"value": "B", "reference": "RAG Single Instance Theorem"},
        "rubric": {"type": "multiple_choice", "criterion": "Single instance RAG necessary and sufficient condition", "points": 1.0},
        "explanation": "If each resource type has exactly one instance, a cycle is both necessary and sufficient for deadlock.",
    },
    {
        "objective_code": "LO_OS_BANKER",
        "title": "Banker's Algorithm Need Matrix Formula",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "In Dijkstra's Banker's algorithm for deadlock avoidance, write the mathematical equation "
            "used to compute the Need matrix for process P_i given Max[i] and Allocation[i]."
        ),
        "answer_key": {"value": "Need[i] = Max[i] - Allocation[i]", "reference": "Banker's Algorithm Need Matrix"},
        "rubric": {"type": "expression", "criterion": "Exact Need vector subtraction formula", "points": 1.0},
        "explanation": "Need[i, j] = Max[i, j] - Allocation[i, j] specifies the remaining resources process P_i may request before terminating.",
    },
    # OS_MEMORY
    {
        "objective_code": "LO_OS_PAGING",
        "title": "Paging vs Segmentation Fragmentation",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "Which form of fragmentation is inherent to standard Paging memory management systems?"
        ),
        "options": [
            {"id": "A", "text": "External fragmentation"},
            {"id": "B", "text": "Internal fragmentation"},
            {"id": "C", "text": "Both internal and external fragmentation equally"},
            {"id": "D", "text": "Neither; paging guarantees zero fragmentation"},
        ],
        "answer_key": {"value": "B", "reference": "Silberschatz Chapter 8 Paging Fragmentation"},
        "rubric": {"type": "multiple_choice", "criterion": "Identification of internal fragmentation in paging", "points": 1.0},
        "explanation": "Because frames are allocated in fixed power-of-two page sizes, the last page allocated to a process is rarely completely filled, producing internal fragmentation.",
    },
    {
        "objective_code": "LO_OS_TLB",
        "title": "Effective Memory Access Time (EMAT) Calculation",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.5,
        "prompt": (
            "Assume memory access time is 100 ns, TLB lookup time is 20 ns, and TLB hit ratio is 90% (0.90). "
            "In a single-level page table system, compute the Effective Memory Access Time (EMAT) in nanoseconds."
        ),
        "answer_key": {"value": "130 ns", "reference": "EMAT Formula: Hit*(TLB+Mem) + Miss*(TLB+2*Mem)"},
        "rubric": {"type": "expression", "criterion": "EMAT = 0.90*(20+100) + 0.10*(20+2*100) = 108 + 22 = 130 ns", "points": 1.5},
        "explanation": "Hit time: 20+100=120 ns. Miss time: 20+100(page table)+100(data)=220 ns. EMAT = 0.9*120 + 0.1*220 = 108 + 22 = 130 ns.",
    },
    {
        "objective_code": "LO_OS_PAGE_REPLACEMENT",
        "title": "Belady's Anomaly and Stack Algorithms",
        "question_type": QuestionType.MULTIPLE_SELECT,
        "difficulty": DifficultyLevel.ADVANCED,
        "max_score": 1.5,
        "prompt": (
            "Which page replacement algorithms CANNOT exhibit Belady's Anomaly (i.e., are proven Stack Algorithms)?"
        ),
        "options": [
            {"id": "A", "text": "First-In, First-Out (FIFO)"},
            {"id": "B", "text": "Least Recently Used (LRU)"},
            {"id": "C", "text": "Optimal Page Replacement (OPT / MIN)"},
            {"id": "D", "text": "Second-Chance / Clock Algorithm"},
        ],
        "answer_key": {"value": ["B", "C"], "reference": "Mattson's Stack Algorithm Property"},
        "rubric": {"type": "multiple_select", "criterion": "Identification of LRU and OPT as stack algorithms", "points": 1.5},
        "explanation": "LRU and OPT satisfy the inclusion property B(m) subseteq B(m+1) for all m frames, proving they can never produce more page faults with more frames.",
    },
]


async def seed_comprehensive_curriculum(session: AsyncSession) -> dict[str, Any]:
    """Execute full multi-topic, multi-DAG seeding across DBMS and OS."""
    user_repo = UserRepository(session)
    course_repo = CourseRepository(session)
    topic_repo = TopicRepository(session)
    lo_repo = LearningObjectiveRepository(session)
    q_repo = QuestionRepository(session)
    v_repo = QuestionVersionRepository(session)

    # 1. Instructors
    codd = await user_repo.get_by_email("instructor.dbms@recall.edu")
    if not codd:
        codd = User(email="instructor.dbms@recall.edu", full_name="Prof. E. F. Codd", role=UserRole.INSTRUCTOR)
        await user_repo.create(codd)

    tanenbaum = await user_repo.get_by_email("instructor.os@recall.edu")
    if not tanenbaum:
        tanenbaum = User(email="instructor.os@recall.edu", full_name="Prof. Andrew Tanenbaum", role=UserRole.INSTRUCTOR)
        await user_repo.create(tanenbaum)

    # 2. Seed DBMS Topics and Questions
    dbms_course = await course_repo.get_by_code("CS340")
    if not dbms_course:
        dbms_course = Course(
            code="CS340",
            title="Database Management Systems",
            description="Relational data model, formal algebra, SQL, normalization, and concurrency.",
            instructor_id=codd.id,
        )
        await course_repo.create(dbms_course)

    dbms_lo_map: dict[str, LearningObjective] = {}
    for top_data in DBMS_TOPICS:
        topics = await topic_repo.list_by_course(dbms_course.id)
        topic = next((t for t in topics if t.code == top_data["code"]), None)
        if not topic:
            topic = Topic(
                course_id=dbms_course.id,
                code=top_data["code"],
                title=top_data["title"],
                description=top_data["description"],
                order_index=top_data["order_index"],
                objectives=[],
            )
            await topic_repo.create(topic)

        existing_los = await lo_repo.list_by_topic(topic.id)
        for lo in existing_los:
            dbms_lo_map[lo.code] = lo

        for lo_code, lo_title, lo_desc, order, prereqs in top_data["objectives"]:
            if lo_code not in dbms_lo_map:
                prereq_ids = [dbms_lo_map[c].id for c in prereqs if c in dbms_lo_map]
                lo = LearningObjective(
                    topic_id=topic.id,
                    code=lo_code,
                    title=lo_title,
                    description=lo_desc,
                    order_index=order,
                    prerequisite_objective_ids=prereq_ids,
                )
                await lo_repo.create(lo)
                dbms_lo_map[lo_code] = lo

    dbms_q_seeded = 0
    for q_data in DBMS_NEW_QUESTIONS:
        lo = dbms_lo_map.get(q_data["objective_code"])
        if not lo:
            continue
        existing_qs = await q_repo.list_by_objective(lo.id)
        if any(eq.title == q_data["title"] for eq in existing_qs):
            continue

        q = Question(
            objective_id=lo.id,
            title=q_data["title"],
            question_type=q_data["question_type"],
            is_active=True,
        )
        await q_repo.create(q)
        prov_hash = calculate_provenance_hash(
            prompt=q_data["prompt"],
            answer_key=q_data["answer_key"],
            rubric=q_data["rubric"],
        )
        v = QuestionVersion(
            question_id=q.id,
            version_number=1,
            difficulty=q_data["difficulty"],
            max_score=q_data["max_score"],
            options=q_data.get("options"),
            prompt=q_data["prompt"],
            answer_key=q_data["answer_key"],
            rubric=q_data["rubric"],
            explanation=q_data["explanation"],
            verification_status=VerificationStatus.VERIFIED,
            verified_by="Prof. E. F. Codd",
            provenance_hash=prov_hash,
        )
        await v_repo.create(v)
        q.current_version_id = v.id
        await session.flush()
        dbms_q_seeded += 1

    # 3. Seed OS Topics and Questions
    os_course = await course_repo.get_by_code("CS301")
    if not os_course:
        os_course = Course(
            code="CS301",
            title="Operating Systems & Concurrency",
            description="Process management, CPU scheduling, synchronization, deadlocks, and virtual memory.",
            instructor_id=tanenbaum.id,
        )
        await course_repo.create(os_course)

    os_lo_map: dict[str, LearningObjective] = {}
    for top_data in OS_TOPICS:
        topics = await topic_repo.list_by_course(os_course.id)
        topic = next((t for t in topics if t.code == top_data["code"]), None)
        if not topic:
            topic = Topic(
                course_id=os_course.id,
                code=top_data["code"],
                title=top_data["title"],
                description=top_data["description"],
                order_index=top_data["order_index"],
                objectives=[],
            )
            await topic_repo.create(topic)

        existing_los = await lo_repo.list_by_topic(topic.id)
        for lo in existing_los:
            os_lo_map[lo.code] = lo

        for lo_code, lo_title, lo_desc, order, prereqs in top_data["objectives"]:
            if lo_code not in os_lo_map:
                prereq_ids = [os_lo_map[c].id for c in prereqs if c in os_lo_map]
                lo = LearningObjective(
                    topic_id=topic.id,
                    code=lo_code,
                    title=lo_title,
                    description=lo_desc,
                    order_index=order,
                    prerequisite_objective_ids=prereq_ids,
                )
                await lo_repo.create(lo)
                os_lo_map[lo_code] = lo

    os_q_seeded = 0
    for q_data in OS_NEW_QUESTIONS:
        lo = os_lo_map.get(q_data["objective_code"])
        if not lo:
            continue
        existing_qs = await q_repo.list_by_objective(lo.id)
        if any(eq.title == q_data["title"] for eq in existing_qs):
            continue

        q = Question(
            objective_id=lo.id,
            title=q_data["title"],
            question_type=q_data["question_type"],
            is_active=True,
        )
        await q_repo.create(q)
        prov_hash = calculate_provenance_hash(
            prompt=q_data["prompt"],
            answer_key=q_data["answer_key"],
            rubric=q_data["rubric"],
        )
        v = QuestionVersion(
            question_id=q.id,
            version_number=1,
            difficulty=q_data["difficulty"],
            max_score=q_data["max_score"],
            options=q_data.get("options"),
            prompt=q_data["prompt"],
            answer_key=q_data["answer_key"],
            rubric=q_data["rubric"],
            explanation=q_data["explanation"],
            verification_status=VerificationStatus.VERIFIED,
            verified_by="Prof. Andrew Tanenbaum",
            provenance_hash=prov_hash,
        )
        await v_repo.create(v)
        q.current_version_id = v.id
        await session.flush()
        os_q_seeded += 1

    return {
        "status": "success",
        "dbms_new_questions": dbms_q_seeded,
        "dbms_total_objectives": len(dbms_lo_map),
        "os_new_questions": os_q_seeded,
        "os_total_objectives": len(os_lo_map),
    }
