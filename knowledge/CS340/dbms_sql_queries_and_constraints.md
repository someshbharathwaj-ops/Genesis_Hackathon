# CS340 Database Management Systems — SQL Query Formulation & Integrity Constraints

**Course Code:** CS340  
**Topic:** SQL_LANG (SQL Query Formulation & Integrity)  
**Associated Learning Objectives:** `LO_SQL_SUBQUERIES`, `LO_SQL_GROUPING`, `LO_SQL_CONSTRAINTS`  
**Prerequisites:** Relational Algebra (`LO_RA_SELECT_PROJECT`, `LO_RA_JOINS`)  
**Authoritative References:** [Silberschatz et al., Chapter 3 & Chapter 4; Correlated Subqueries.pdf, SQL Notes.pdf]

---

## 1. Declarative Querying & Aggregation Pipelines

SQL (Structured Query Language) is a declarative domain-specific language operating on multisets (bags).

### 1.1 The SQL Execution Order
Understanding the evaluation order is crucial for reasoning about query behavior:
1. `FROM` (table references and join evaluation)
2. `WHERE` (tuple-level predicate filtering before grouping)
3. `GROUP BY` (partitioning rows into groups by unique key values)
4. `HAVING` (group-level predicate filtering after aggregation)
5. `SELECT` (expression computation and projection)
6. `DISTINCT` (duplicate elimination)
7. `ORDER BY` (sorting output rows)
8. `LIMIT` / `OFFSET` (windowing result set)

### 1.2 Aggregation & Grouping Semantics
- Aggregate functions (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`) compute a single summary value across a partition of rows.
- **The Grouping Rule:** When `GROUP BY` is used, every attribute appearing in the `SELECT` clause must either be in the `GROUP BY` list or be enclosed within an aggregate function.
- **`WHERE` vs `HAVING`:**
  - `WHERE` filters individual rows **prior** to aggregation; it cannot contain aggregate expressions (e.g. `WHERE AVG(salary) > 50000` is illegal).
  - `HAVING` filters aggregated groups **after** aggregation; it operates on aggregate values (e.g. `HAVING COUNT(*) >= 5`).

---

## 2. Correlated Subqueries & Set Predicates

A **subquery** is a `SELECT` statement nested inside another SQL statement.

### 2.1 Independent vs Correlated Subqueries
- **Independent Subquery:** Evaluated once; does not reference attributes from the outer query.
- **Correlated Subquery:** References attributes from the outer query (e.g. `WHERE o.dept_id = i.dept_id`). Evaluated once **per candidate row** of the outer query.

### 2.2 Set Membership & Existence Predicates
- `IN` / `NOT IN`: Checks if a scalar matches any element in a subquery set.
- `EXISTS` / `NOT EXISTS`: Evaluates to `TRUE` if the subquery returns at least one tuple. Efficiently evaluated with early-exit optimizations.
- `ALL` / `ANY` (`SOME`): Compares a value to all or any members of a subquery result set.

---

## 3. Referential Integrity & Constraints

1. **PRIMARY KEY:** Uniquely identifies each record; enforces uniqueness and `NOT NULL`.
2. **FOREIGN KEY:** Enforces referential integrity.
   - `ON DELETE RESTRICT` / `NO ACTION`: Rejects parent deletion if child references exist.
   - `ON DELETE CASCADE`: Automatically deletes dependent child records when parent is deleted.
   - `ON DELETE SET NULL`: Sets child foreign key columns to `NULL` when parent is deleted.
3. **CHECK:** Validates domain rules on attribute values (e.g. `CHECK (salary >= 0)`).

---

## 4. Common Misconceptions & Traps

| Misconception | Correction |
| :--- | :--- |
| **"`COUNT(*)` and `COUNT(column)` return the same count."** | `COUNT(*)` counts all rows including those with `NULL`s. `COUNT(column)` counts only rows where `column` is **not `NULL`**. |
| **"`WHERE` can filter on aggregate functions."** | Aggregates are evaluated after `WHERE` filtering. Group filtering must be placed in `HAVING`. |
| **"`NOT IN` handles `NULL` values safely."** | If the subquery result contains even a single `NULL`, `x NOT IN (subquery)` evaluates to `UNKNOWN`, resulting in zero rows returned. |
