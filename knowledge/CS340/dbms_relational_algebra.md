# CS340 Database Management Systems — Relational Model & Relational Algebra

**Course Code:** CS340  
**Topic:** REL_ALGEBRA (Relational Model & Relational Algebra)  
**Associated Learning Objectives:** `LO_RA_SELECT_PROJECT`, `LO_RA_JOINS`, `LO_RA_AGGREGATION`  
**Prerequisites:** Set Theory Basics  
**Authoritative References:** [Silberschatz et al., Chapter 2 & Chapter 6; DBMS_Lecture2 2-relational model.pdf]

---

## 1. Fundamentals of the Relational Model

The relational model represents data as mathematical relations.
- A **relation schema** $R(A_1, A_2, \dots, A_n)$ denotes the relation name $R$ and its list of attributes $A_i$.
- A **relation instance** $r(R)$ is a finite set of tuples $t = \langle v_1, v_2, \dots, v_n \rangle$, where each value $v_i \in \text{Domain}(A_i)$.
- **Integrity Constraints:**
  - *Entity Integrity:* No primary key attribute may contain a `NULL` value.
  - *Referential Integrity:* If a foreign key $FK$ in relation $R_1$ references primary key $PK$ of $R_2$, then for every tuple in $R_1$, the value of $FK$ must either be `NULL` or match an existing $PK$ value in $R_2$.

---

## 2. Fundamental Relational Algebra Operations

Relational algebra is a formal procedural query language consisting of operations that take one or two relations as input and produce a new relation as output.

### 2.1 Select Operation ($\sigma$)
- **Purpose:** Filters tuples horizontally based on a selection predicate $P$.
- **Notation:** $\sigma_P(r) = \{ t \in r \mid P(t) = \text{True} \}$
- **Example:** $\sigma_{\text{salary} > 50000}(\text{Instructor})$ selects all instructor tuples with salary greater than 50,000.

### 2.2 Project Operation ($\Pi$)
- **Purpose:** Filters columns vertically, selecting a specified subset of attributes and automatically eliminating duplicate tuples.
- **Notation:** $\Pi_{A_1, A_2, \dots, A_k}(r)$
- **Example:** $\Pi_{\text{name, dept\_name}}(\text{Instructor})$ yields a relation with only names and department names.

### 2.3 Cartesian Product ($\times$)
- **Purpose:** Combines every tuple of relation $r$ with every tuple of relation $s$.
- **Degree:** $\text{Degree}(r \times s) = \text{Degree}(r) + \text{Degree}(s)$
- **Cardinality:** $|r \times s| = |r| \times |s|$

---

## 3. Relational Joins

### 3.1 Theta Join ($\Join_\theta$)
- Combines Cartesian product with a selection condition:
  $$r \Join_\theta s = \sigma_\theta(r \times s)$$

### 3.2 Natural Join ($\Join$)
- Computes the equijoin over all identically named common attributes between $r$ and $s$, and projects away the duplicate common columns:
  $$r \Join s = \Pi_{\text{Schema}(r) \cup \text{Schema}(s)}(\sigma_{r.A_1 = s.A_1 \wedge \dots \wedge r.A_k = s.A_k}(r \times s))$$

### 3.3 Outer Joins
- **Left Outer Join ($⟕$):** Retains all tuples from the left relation, padding right attributes with `NULL` where no match exists.
- **Right Outer Join ($⟖$):** Retains all tuples from the right relation, padding left attributes with `NULL`.
- **Full Outer Join ($⟗$):** Retains all tuples from both relations.

---

## 4. Common Misconceptions & Traps

| Misconception | Correction |
| :--- | :--- |
| **"Projection retains duplicate rows."** | In formal relational algebra, relations are mathematical sets. Therefore, $\Pi$ **strictly eliminates duplicates**. (SQL `SELECT` preserves duplicates by default unless `DISTINCT` is specified). |
| **"Natural join requires specifying a condition."** | Natural join $\Join$ implicitly and automatically equates **all attributes with identical names** in both schemas. |
| **"Cartesian product requires a common attribute."** | Cartesian product $r \times s$ pairs all tuples unconditionally, regardless of whether schemas share common attributes. |
