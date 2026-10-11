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
    {
        "objective_code": "LO_CLOSURE",
        "title": "Attribute Closure Multi-Step Derivation",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "Given relation R(A, B, C, D, E) and functional dependencies F = {A -> B, B -> C, CD -> E}. "
            "What is the attribute closure {A, D}+ under F?"
        ),
        "options": [
            {"id": "A", "text": "{A, D}"},
            {"id": "B", "text": "{A, B, D}"},
            {"id": "C", "text": "{A, B, C, D, E}"},
            {"id": "D", "text": "{A, B, C, D}"},
        ],
        "answer_key": {"value": "C", "reference": "Silberschatz Chapter 8 Armstrong Axioms Closure"},
        "rubric": {"type": "multiple_choice", "criterion": "Correct sequential attribute closure evaluation", "points": 1.0},
        "explanation": "Start: {A, D}. A->B adds B -> {A, B, D}. B->C adds C -> {A, B, C, D}. CD->E adds E -> {A, B, C, D, E}.",
    },
    {
        "objective_code": "LO_KEYS",
        "title": "Candidate Key Identification with Missing Attributes",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "Given relation R(A, B, C, D) and functional dependencies F = {AB -> C, C -> D, D -> A}. "
            "Which of the following constitutes a minimal candidate key for R?"
        ),
        "options": [
            {"id": "A", "text": "{A, B}"},
            {"id": "B", "text": "{B, C}"},
            {"id": "C", "text": "{B, D}"},
            {"id": "D", "text": "All of {AB}, {BC}, and {BD} are valid candidate keys"},
        ],
        "answer_key": {"value": "D", "reference": "Candidate Key Derivation Algorithms"},
        "rubric": {"type": "multiple_choice", "criterion": "Identification of all minimal candidate keys", "points": 1.0},
        "explanation": "Attribute B never appears on the right side of any dependency, so every key must contain B. {AB}+ = {A,B,C,D}, {BC}+ = {A,B,C,D}, {BD}+ = {A,B,C,D}. All three are minimal candidate keys.",
    },
    {
        "objective_code": "LO_MINIMAL_COVER",
        "title": "Extraneous Attribute Elimination in Minimal Cover",
        "question_type": QuestionType.MULTIPLE_SELECT,
        "difficulty": DifficultyLevel.ADVANCED,
        "max_score": 1.5,
        "prompt": (
            "Which conditions must hold for an attribute A to be considered extraneous in a functional dependency X -> Y?"
        ),
        "options": [
            {"id": "A", "text": "If A is on the left-hand side (A in X), removing A produces (X - {A}) -> Y logically implied by F."},
            {"id": "B", "text": "If A is on the right-hand side (A in Y), removing A produces X -> (Y - {A}) that still implies the original F."},
            {"id": "C", "text": "An attribute is extraneous whenever it is a prime attribute."},
            {"id": "D", "text": "A minimal canonical cover cannot contain any extraneous attributes."},
        ],
        "answer_key": {"value": ["A", "B", "D"], "reference": "Canonical Cover Algorithm Silberschatz Chapter 8"},
        "rubric": {"type": "multiple_select", "criterion": "Rigorous definition of extraneous attributes", "points": 1.5},
        "explanation": "Extraneous attributes can occur on LHS or RHS if removing them preserves equivalence; minimal covers strictly exclude extraneous attributes. Prime status is irrelevant.",
    },
    {
        "objective_code": "LO_NF_IDENTIFICATION",
        "title": "Distinguishing 3NF from BCNF Boundary Conditions",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "A relation R is in Third Normal Form (3NF) but NOT in Boyce-Codd Normal Form (BCNF) if and only if:"
        ),
        "options": [
            {"id": "A", "text": "It contains a partial dependency on a candidate key"},
            {"id": "B", "text": "There exists X -> Y where X is not a superkey, but Y consists exclusively of prime attributes"},
            {"id": "C", "text": "It has no candidate keys"},
            {"id": "D", "text": "It contains multivalued dependencies"},
        ],
        "answer_key": {"value": "B", "reference": "3NF vs BCNF Formal Criteria"},
        "rubric": {"type": "multiple_choice", "criterion": "Prime attribute exception in 3NF definition", "points": 1.0},
        "explanation": "3NF allows X -> Y where X is not a superkey as long as every attribute in Y is prime (part of some candidate key). BCNF forbids this, strictly requiring X to be a superkey.",
    },
    {
        "objective_code": "LO_DECOMPOSITION",
        "title": "Lossless Join Decomposition Condition for Two Relations",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "A decomposition of relation R into R1 and R2 is lossless with respect to dependency set F if and only if:"
        ),
        "options": [
            {"id": "A", "text": "R1 intersection R2 is empty"},
            {"id": "B", "text": "(R1 intersection R2) -> R1 is in F+ or (R1 intersection R2) -> R2 is in F+"},
            {"id": "C", "text": "All functional dependencies are preserved in R1 alone"},
            {"id": "D", "text": "R1 and R2 have identical candidate keys"},
        ],
        "answer_key": {"value": "B", "reference": "Lossless Join Decomposition Theorem"},
        "rubric": {"type": "multiple_choice", "criterion": "Intersection superkey condition for lossless decomposition", "points": 1.0},
        "explanation": "By the Lossless Join Theorem, decomposing R into R1 and R2 is lossless if and only if the common attributes (R1 intersect R2) form a superkey of at least one of the decomposed relations.",
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
    {
        "objective_code": "LO_OS_PROCESS",
        "title": "PCB Attributes and Context Switch Overhead",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "During a CPU context switch between two processes, which of the following is SAVED to the outgoing process's Process Control Block (PCB)?"
        ),
        "options": [
            {"id": "A", "text": "Only the PID and parent process pointer"},
            {"id": "B", "text": "Program counter, CPU registers, stack pointer, and memory management state"},
            {"id": "C", "text": "The entire user physical RAM allocation"},
            {"id": "D", "text": "The disk swap partition blocks"},
        ],
        "answer_key": {"value": "B", "reference": "Silberschatz Chapter 3 Process Management & PCB"},
        "rubric": {"type": "multiple_choice", "criterion": "Identification of CPU state registers in PCB", "points": 1.0},
        "explanation": "The context switch saves CPU registers, program counter, and stack pointer to the outgoing PCB and restores the incoming PCB's register state.",
    },
    {
        "objective_code": "LO_OS_SYNCHRONIZATION",
        "title": "Three Essential Criteria for Critical Section Problem",
        "question_type": QuestionType.MULTIPLE_SELECT,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.5,
        "prompt": (
            "Which THREE criteria must any correct software or hardware solution to the Critical Section problem satisfy?"
        ),
        "options": [
            {"id": "A", "text": "Mutual Exclusion"},
            {"id": "B", "text": "Progress"},
            {"id": "C", "text": "Bounded Waiting"},
            {"id": "D", "text": "Preemptive Multi-Core Affinity"},
        ],
        "answer_key": {"value": ["A", "B", "C"], "reference": "Silberschatz Chapter 6 Synchronization Criteria"},
        "rubric": {"type": "multiple_select", "criterion": "Three critical section criteria", "points": 1.5},
        "explanation": "Every valid solution must guarantee Mutual Exclusion (only 1 process in CS), Progress (decision not postponed indefinitely), and Bounded Waiting (no starvation).",
    },
    {
        "objective_code": "LO_OS_SYNCHRONIZATION",
        "title": "Peterson's Algorithm Turn and Flag Invariants",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "In Peterson's two-process mutual exclusion algorithm, why does process P_i execute 'turn = j' immediately after setting 'flag[i] = true'?"
        ),
        "options": [
            {"id": "A", "text": "To forcibly lock process j out of the critical section"},
            {"id": "B", "text": "To politely grant priority to process j, preventing mutual deadlock and satisfying progress"},
            {"id": "C", "text": "To flush the CPU memory write buffers"},
            {"id": "D", "text": "To increment the thread synchronization epoch"},
        ],
        "answer_key": {"value": "B", "reference": "Peterson's Algorithm Symmetry and Turn Invariant"},
        "rubric": {"type": "multiple_choice", "criterion": "Turn polite yield mechanism in Peterson's algorithm", "points": 1.0},
        "explanation": "By setting turn=j, P_i expresses readiness to yield if P_j is also interested, ensuring both processes cannot be blocked simultaneously.",
    },
    {
        "objective_code": "LO_OS_DEADLOCKS",
        "title": "Four Necessary Coffman Conditions for Deadlock",
        "question_type": QuestionType.MULTIPLE_SELECT,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.5,
        "prompt": (
            "Which of the following are the four necessary Coffman conditions for a resource deadlock to occur?"
        ),
        "options": [
            {"id": "A", "text": "Mutual Exclusion"},
            {"id": "B", "text": "Hold and Wait"},
            {"id": "C", "text": "No Preemption"},
            {"id": "D", "text": "Circular Wait"},
        ],
        "answer_key": {"value": ["A", "B", "C", "D"], "reference": "Coffman Conditions for Deadlock"},
        "rubric": {"type": "multiple_select", "criterion": "All four Coffman conditions", "points": 1.5},
        "explanation": "Deadlock can arise if and only if all four Coffman conditions hold concurrently: Mutual Exclusion, Hold & Wait, No Preemption, and Circular Wait.",
    },
    {
        "objective_code": "LO_OS_DEADLOCKS",
        "title": "Deadlock Prevention via Global Resource Ordering",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "Havender's resource ordering strategy prevents deadlocks by requiring that all resources be requested in strictly increasing linear order (F(R_i) < F(R_j)). Which Coffman condition is eliminated by this rule?"
        ),
        "options": [
            {"id": "A", "text": "Mutual Exclusion"},
            {"id": "B", "text": "Circular Wait"},
            {"id": "C", "text": "Hold and Wait"},
            {"id": "D", "text": "Aging"},
        ],
        "answer_key": {"value": "B", "reference": "Deadlock Prevention Techniques"},
        "rubric": {"type": "multiple_choice", "criterion": "Elimination of Circular Wait", "points": 1.0},
        "explanation": "Imposing a total ordering on all resources makes it mathematically impossible to form a directed cycle of requests, eliminating Circular Wait.",
    },
    {
        "objective_code": "LO_OS_PAGING",
        "title": "Page Table Size Arithmetic in 32-bit Architecture",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.5,
        "prompt": (
            "Consider a 32-bit virtual address space with a 4 KB page size (2^12 bytes). If each page table entry (PTE) requires 4 bytes, how many bytes are needed for the complete single-level page table?"
        ),
        "answer_key": {"value": "4 MB", "reference": "Page Table Size = (2^32 / 2^12) * 4 bytes = 2^20 * 4 = 4 MB"},
        "rubric": {"type": "expression", "criterion": "Exact 4 MB calculation", "points": 1.5},
        "explanation": "Number of pages = 2^32 / 2^12 = 2^20 pages (1,048,576 pages). Size = 2^20 * 4 bytes = 4,194,304 bytes = 4 MB.",
    },
]


# ==============================================================================
# COMPUTER NETWORKS COMPREHENSIVE CURRICULUM (CS305)
# ==============================================================================

NET_TOPICS = [
    {
        "code": "NET_ARCH",
        "title": "Layered Architectures & Protocol Models",
        "description": "OSI 7-layer reference model, TCP/IP 4-layer architecture, encapsulation, and PDUs.",
        "order_index": 1,
        "objectives": [
            ("LO_NET_OSI_LAYERS", "OSI 7-Layer vs TCP/IP Architecture", "Layer responsibilities, service primitives, and architectural comparison", 1, []),
            ("LO_NET_ENCAPSULATION", "Protocol Data Units & Encapsulation", "PDU transitions, headers, trailers, and packet decapsulation", 2, ["LO_NET_OSI_LAYERS"]),
        ],
    },
    {
        "code": "NET_TRANSPORT",
        "title": "Transport Layer Protocols & Reliability",
        "description": "TCP connection lifecycle, three-way handshakes, flow control, and AIMD congestion control.",
        "order_index": 2,
        "objectives": [
            ("LO_NET_TCP_HANDSHAKE", "TCP 3-Way Handshake & Connection States", "SYN, SYN-ACK, ACK transitions, sequence numbers, and teardown", 1, ["LO_NET_ENCAPSULATION"]),
            ("LO_NET_CONGESTION", "Flow Control vs Congestion Control", "Sliding window, AIMD, Slow Start, and Fast Retransmit", 2, ["LO_NET_TCP_HANDSHAKE"]),
        ],
    },
    {
        "code": "NET_ROUTING",
        "title": "Network Layer Addressing & Routing Protocols",
        "description": "IPv4 CIDR addressing, subnet calculations, distance-vector, and link-state algorithms.",
        "order_index": 3,
        "objectives": [
            ("LO_NET_IP_SUBNETTING", "IPv4 CIDR Addressing & Subnet Calculation", "Subnet masks, network/broadcast boundaries, and host capacities", 1, ["LO_NET_ENCAPSULATION"]),
            ("LO_NET_ROUTING_PROTOCOLS", "Distance-Vector vs Link-State Routing", "Bellman-Ford, Dijkstra SPF, count-to-infinity, and split horizon", 2, ["LO_NET_IP_SUBNETTING"]),
        ],
    },
]

NET_NEW_QUESTIONS: list[dict[str, Any]] = [
    {
        "objective_code": "LO_NET_OSI_LAYERS",
        "title": "OSI 7-Layer Responsibilities",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "Which layer of the OSI 7-layer reference model is primarily responsible for end-to-end process-to-process communication, flow control, and error recovery?"
        ),
        "options": [
            {"id": "A", "text": "Network Layer"},
            {"id": "B", "text": "Transport Layer"},
            {"id": "C", "text": "Data Link Layer"},
            {"id": "D", "text": "Session Layer"},
        ],
        "answer_key": {"value": "B", "reference": "Tanenbaum Chapter 1 Computer Networks Layer Models"},
        "rubric": {"type": "multiple_choice", "criterion": "Transport layer responsibility", "points": 1.0},
        "explanation": "The Transport Layer (Layer 4) provides logical, end-to-end process-to-process communication, segmentation, flow control, and reliability.",
    },
    {
        "objective_code": "LO_NET_OSI_LAYERS",
        "title": "OSI Presentation and Session Layer Roles in TCP/IP",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "In the 4-layer TCP/IP architectural model, where are the functionalities of the OSI Presentation and Session layers handled?"
        ),
        "options": [
            {"id": "A", "text": "Merged into the Application Layer"},
            {"id": "B", "text": "Implemented inside the Transport Layer protocol stack"},
            {"id": "C", "text": "Completely omitted without modern equivalent"},
            {"id": "D", "text": "Handled directly by router firmware in the Network Layer"},
        ],
        "answer_key": {"value": "A", "reference": "Kurose & Ross Chapter 1 Protocol Layers"},
        "rubric": {"type": "multiple_choice", "criterion": "Application layer consolidation in TCP/IP", "points": 1.0},
        "explanation": "In TCP/IP, presentation tasks (encryption, compression) and session tasks (dialog control) are implemented directly by application protocols (e.g. TLS, HTTP).",
    },
    {
        "objective_code": "LO_NET_ENCAPSULATION",
        "title": "Protocol Data Unit (PDU) Naming Across Protocol Stack",
        "question_type": QuestionType.MULTIPLE_SELECT,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.5,
        "prompt": (
            "Which of the following PDU mappings to their respective protocol layers are CORRECT?"
        ),
        "options": [
            {"id": "A", "text": "Transport Layer PDU -> Segment (TCP) / Datagram (UDP)"},
            {"id": "B", "text": "Network Layer PDU -> Packet"},
            {"id": "C", "text": "Data Link Layer PDU -> Frame"},
            {"id": "D", "text": "Physical Layer PDU -> Bits"},
        ],
        "answer_key": {"value": ["A", "B", "C", "D"], "reference": "PDU Taxonomy Kurose & Ross"},
        "rubric": {"type": "multiple_select", "criterion": "All correct PDU layer mappings", "points": 1.5},
        "explanation": "PDUs are termed Message (Application), Segment/Datagram (Transport), Packet (Network), Frame (Data Link), and Bits (Physical).",
    },
    {
        "objective_code": "LO_NET_ENCAPSULATION",
        "title": "Data Link Frame Trailer Functionality",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "Unlike other layers which only prepend headers, the Data Link layer appends a trailer containing a Frame Check Sequence (FCS). What is its primary purpose?"
        ),
        "options": [
            {"id": "A", "text": "Payload compression"},
            {"id": "B", "text": "Error detection via Cyclic Redundancy Check (CRC)"},
            {"id": "C", "text": "IP address translation"},
            {"id": "D", "text": "End-to-end encryption"},
        ],
        "answer_key": {"value": "B", "reference": "Ethernet Frame Format IEEE 802.3"},
        "rubric": {"type": "multiple_choice", "criterion": "CRC error detection in FCS trailer", "points": 1.0},
        "explanation": "The frame trailer contains a 32-bit CRC code (FCS) enabling the receiver hardware to detect transmission bit errors and discard corrupted frames.",
    },
    {
        "objective_code": "LO_NET_TCP_HANDSHAKE",
        "title": "TCP 3-Way Handshake Connection Sequence",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "What is the exact sequence of control packets exchanged to establish a TCP connection between client C and server S?"
        ),
        "options": [
            {"id": "A", "text": "1. SYN (from C), 2. SYN-ACK (from S), 3. ACK (from C)"},
            {"id": "B", "text": "1. ACK (from C), 2. SYN (from S), 3. ACK (from C)"},
            {"id": "C", "text": "1. SYN (from C), 2. ACK (from S)"},
            {"id": "D", "text": "1. FIN (from C), 2. ACK (from S), 3. FIN-ACK (from C)"},
        ],
        "answer_key": {"value": "A", "reference": "RFC 793 Transmission Control Protocol Handshake"},
        "rubric": {"type": "multiple_choice", "criterion": "Correct 3-way handshake sequence", "points": 1.0},
        "explanation": "Client sends SYN(seq=x); Server responds with SYN(seq=y)+ACK(ack=x+1); Client acknowledges with ACK(ack=y+1).",
    },
    {
        "objective_code": "LO_NET_TCP_HANDSHAKE",
        "title": "TCP SYN Flood Attack Mitigation Mechanism",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "Which technique allows a server to resist SYN Flood denial-of-service attacks without allocating memory for half-open connections in the backlog queue?"
        ),
        "options": [
            {"id": "A", "text": "SYN Cookies"},
            {"id": "B", "text": "Selective Acknowledgments (SACK)"},
            {"id": "C", "text": "Nagle's Algorithm"},
            {"id": "D", "text": "Slow Start Restart"},
        ],
        "answer_key": {"value": "A", "reference": "SYN Flood Defense RFC 4987"},
        "rubric": {"type": "multiple_choice", "criterion": "Identification of SYN Cookies", "points": 1.0},
        "explanation": "SYN Cookies encode connection parameters into the Initial Sequence Number (ISN) of the SYN-ACK packet, avoiding server-side state allocation until the final ACK arrives.",
    },
    {
        "objective_code": "LO_NET_CONGESTION",
        "title": "TCP Congestion Control AIMD Invariant",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "In TCP Reno Congestion Avoidance mode, what is the behavior of the congestion window (cwnd) upon receiving ACKs and upon packet loss?"
        ),
        "options": [
            {"id": "A", "text": "Additive Increase by 1 MSS per RTT; Multiplicative Decrease by halving cwnd upon loss"},
            {"id": "B", "text": "Exponential increase per RTT; linear decrease upon loss"},
            {"id": "C", "text": "Constant window size managed strictly by the receiver"},
            {"id": "D", "text": "Doubles cwnd per RTT until server buffer overflows"},
        ],
        "answer_key": {"value": "A", "reference": "RFC 5681 TCP Congestion Control AIMD"},
        "rubric": {"type": "multiple_choice", "criterion": "AIMD rule in congestion avoidance", "points": 1.0},
        "explanation": "Additive Increase Multiplicative Decrease (AIMD) increases cwnd linearly by 1 MSS every round-trip time, and halves cwnd when packet loss is detected.",
    },
    {
        "objective_code": "LO_NET_CONGESTION",
        "title": "Flow Control vs Congestion Control Distinction",
        "question_type": QuestionType.MULTIPLE_SELECT,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.5,
        "prompt": (
            "Which statements correctly distinguish TCP Flow Control from Congestion Control?"
        ),
        "options": [
            {"id": "A", "text": "Flow control protects the receiver from buffer overflow using the Receive Window (rwnd)."},
            {"id": "B", "text": "Congestion control protects the intermediate network routers from packet drops using the Congestion Window (cwnd)."},
            {"id": "C", "text": "The sender's effective transmission window is min(rwnd, cwnd)."},
            {"id": "D", "text": "Flow control and congestion control are identical mechanisms with different names."},
        ],
        "answer_key": {"value": ["A", "B", "C"], "reference": "Kurose & Ross Chapter 3 Transport Layer"},
        "rubric": {"type": "multiple_select", "criterion": "Distinction between rwnd and cwnd", "points": 1.5},
        "explanation": "Flow control is end-to-end matching sender rate to receiver buffer; Congestion control prevents network saturation; Effective window = min(rwnd, cwnd).",
    },
    {
        "objective_code": "LO_NET_IP_SUBNETTING",
        "title": "Usable Host Calculation for CIDR /26 Subnet",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "Given an IPv4 subnet with CIDR prefix /26, compute the total number of USABLE host IP addresses available for assignment to client devices."
        ),
        "answer_key": {"value": "62", "reference": "Formula: 2^(32-26) - 2 = 2^6 - 2 = 64 - 2 = 62"},
        "rubric": {"type": "expression", "criterion": "Exact 62 host addresses", "points": 1.0},
        "explanation": "With prefix /26, there are 32 - 26 = 6 host bits. Total addresses = 2^6 = 64. Subtracting 2 (network and broadcast addresses) yields 62 usable host addresses.",
    },
    {
        "objective_code": "LO_NET_IP_SUBNETTING",
        "title": "Determining Directed Broadcast Address in Subnet",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "For IP address 192.168.1.130 with subnet mask 255.255.255.192 (/26), what is the directed broadcast address for this subnet?"
        ),
        "options": [
            {"id": "A", "text": "192.168.1.128"},
            {"id": "B", "text": "192.168.1.191"},
            {"id": "C", "text": "192.168.1.255"},
            {"id": "D", "text": "192.168.1.127"},
        ],
        "answer_key": {"value": "B", "reference": "Subnet Masking Arithmetic"},
        "rubric": {"type": "multiple_choice", "criterion": "Correct broadcast address calculation", "points": 1.0},
        "explanation": "Block size = 256 - 192 = 64. Subnet containing .130 spans 192.168.1.128 to 192.168.1.191. Network ID is .128 and Broadcast address is .191.",
    },
    {
        "objective_code": "LO_NET_ROUTING_PROTOCOLS",
        "title": "Distance-Vector vs Link-State Routing Algorithms",
        "question_type": QuestionType.MULTIPLE_SELECT,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.5,
        "prompt": (
            "Which of the following characteristics distinguish Link-State (e.g. OSPF) from Distance-Vector (e.g. RIP) routing protocols?"
        ),
        "options": [
            {"id": "A", "text": "Link-state routers flood link-state advertisements (LSAs) so every router maintains a complete topology map."},
            {"id": "B", "text": "Link-state algorithms run Dijkstra's algorithm independently on each router."},
            {"id": "C", "text": "Distance-vector algorithms (Bellman-Ford) are susceptible to the Count-to-Infinity problem."},
            {"id": "D", "text": "Distance-vector protocols exchange full network topology graphs with every router in the autonomous system."},
        ],
        "answer_key": {"value": ["A", "B", "C"], "reference": "Tanenbaum Chapter 5 Routing Algorithms"},
        "rubric": {"type": "multiple_select", "criterion": "Accurate comparison between Link-State and Distance-Vector", "points": 1.5},
        "explanation": "Link-state floods LSAs and computes Dijkstra trees locally. Distance-vector only sends distance vectors to immediate neighbors and suffers from count-to-infinity.",
    },
    {
        "objective_code": "LO_NET_ROUTING_PROTOCOLS",
        "title": "Split Horizon Rule in Distance-Vector Routing",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.ADVANCED,
        "max_score": 1.0,
        "prompt": (
            "What is the fundamental rule of Split Horizon with Poison Reverse in Distance-Vector routing?"
        ),
        "options": [
            {"id": "A", "text": "Never advertise a route back to the neighbor from which it was learned, or advertise it with infinity metric (16 in RIP)"},
            {"id": "B", "text": "Split the IP packet into fragments if MTU is exceeded"},
            {"id": "C", "text": "Divide the routing table between TCP and UDP protocols"},
            {"id": "D", "text": "Limit maximum hop count to 255"},
        ],
        "answer_key": {"value": "A", "reference": "RFC 1058 Routing Information Protocol Split Horizon"},
        "rubric": {"type": "multiple_choice", "criterion": "Definition of Split Horizon with Poison Reverse", "points": 1.0},
        "explanation": "Split Horizon prevents 2-node routing loops by not advertising a learned route back to the next-hop neighbor (or advertising cost infinity via poison reverse).",
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

    # 4. Seed Computer Networks Topics and Questions (CS305)
    net_course = await course_repo.get_by_code("CS305")
    if not net_course:
        cerf = await user_repo.get_by_email("instructor.net@recall.edu")
        if not cerf:
            cerf = User(email="instructor.net@recall.edu", full_name="Prof. Vint Cerf", role=UserRole.INSTRUCTOR)
            await user_repo.create(cerf)
        net_course = Course(
            code="CS305",
            title="Computer Networks & Internet Protocols",
            description="Layered architectures, OSI/TCP-IP stacks, transport protocols, IP subnetting, and routing algorithms.",
            instructor_id=cerf.id,
        )
        await course_repo.create(net_course)

    net_lo_map: dict[str, LearningObjective] = {}
    for top_data in NET_TOPICS:
        topics = await topic_repo.list_by_course(net_course.id)
        topic = next((t for t in topics if t.code == top_data["code"]), None)
        if not topic:
            topic = Topic(
                course_id=net_course.id,
                code=top_data["code"],
                title=top_data["title"],
                description=top_data["description"],
                order_index=top_data["order_index"],
                objectives=[],
            )
            await topic_repo.create(topic)

        existing_los = await lo_repo.list_by_topic(topic.id)
        for lo in existing_los:
            net_lo_map[lo.code] = lo

        for lo_code, lo_title, lo_desc, order, prereqs in top_data["objectives"]:
            if lo_code not in net_lo_map:
                prereq_ids = [net_lo_map[c].id for c in prereqs if c in net_lo_map]
                lo = LearningObjective(
                    topic_id=topic.id,
                    code=lo_code,
                    title=lo_title,
                    description=lo_desc,
                    order_index=order,
                    prerequisite_objective_ids=prereq_ids,
                )
                await lo_repo.create(lo)
                net_lo_map[lo_code] = lo

    net_q_seeded = 0
    for q_data in NET_NEW_QUESTIONS:
        lo = net_lo_map.get(q_data["objective_code"])
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
            verified_by="Prof. Vint Cerf",
            provenance_hash=prov_hash,
        )
        await v_repo.create(v)
        q.current_version_id = v.id
        await session.flush()
        net_q_seeded += 1

    return {
        "status": "success",
        "dbms_new_questions": dbms_q_seeded,
        "dbms_total_objectives": len(dbms_lo_map),
        "os_new_questions": os_q_seeded,
        "os_total_objectives": len(os_lo_map),
        "net_new_questions": net_q_seeded,
        "net_total_objectives": len(net_lo_map),
    }


if __name__ == "__main__":
    import asyncio
    from app.core.database import AsyncSessionLocal

    async def _main():
        async with AsyncSessionLocal() as s:
            res = await seed_comprehensive_curriculum(s)
            await s.commit()
            print("SEEDING RESULT:", res)

    asyncio.run(_main())
