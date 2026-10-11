# CS340 Database Management Systems — Normalization & Lossless Decomposition

**Course Code:** CS340  
**Topic:** FD_NORM (Functional Dependencies & Normalization)  
**Associated Learning Objectives:** `LO_NF_IDENTIFICATION`, `LO_DECOMPOSITION`  
**Prerequisites:** Attribute Closure & Candidate Keys (`LO_CLOSURE`, `LO_KEYS`)  
**Authoritative References:** [Silberschatz et al., Chapter 8; Chapter10-normalization.pdf, Decomposition[1].docx]

---

## 1. Normal Forms Hierarchy

Normalization systematically eliminates insertion, deletion, and update anomalies by decomposing relations into higher normal forms.

### 1.1 First Normal Form (1NF)
- A relation schema $R$ is in 1NF if and only if all attribute domains contain only **atomic (indivisible)** values, and there are no repeating groups or multivalued attributes.

### 1.2 Second Normal Form (2NF)
- $R$ is in 2NF if it is in 1NF and **no non-prime attribute is partially dependent** on any candidate key of $R$.
- That is, no non-prime attribute depends on a proper subset of a composite candidate key.

### 1.3 Third Normal Form (3NF)
- $R$ is in 3NF if for every functional dependency $X \to Y$ holding in $R$, at least one of the following holds:
  1. $X \to Y$ is trivial ($Y \subseteq X$).
  2. $X$ is a **superkey** of $R$.
  3. Each attribute in $Y \setminus X$ is a **prime attribute** (member of some candidate key).

### 1.4 Boyce-Codd Normal Form (BCNF)
- $R$ is in BCNF if for every non-trivial functional dependency $X \to Y$ holding in $R$:
  - $X$ is a **superkey** of $R$.
- BCNF strictly eliminates all redundancies derived from functional dependencies. Every BCNF relation is in 3NF, but not every 3NF relation is in BCNF.

---

## 2. Properties of Decomposition

When decomposing relation schema $R$ into $R_1, R_2, \dots, R_k$:

### 2.1 Lossless-Join Decomposition
- Guarantees that reconstructing the original relation via natural join produces the exact original relation without spurious tuples:
  $$R_1 \Join R_2 = R$$
- **Binary Lossless Join Theorem:** A decomposition of $R$ into $(R_1, R_2)$ is lossless with respect to dependency set $F$ if and only if:
  $$(R_1 \cap R_2) \to R_1 \in F^+ \quad \text{or} \quad (R_1 \cap R_2) \to R_2 \in F^+$$
  (The common attributes must form a superkey for at least one of the decomposed schemas).

### 2.2 Dependency Preservation
- A decomposition preserves dependencies if the union of functional dependencies holding in individual sub-relations covers all original dependencies:
  $$(F_1 \cup F_2 \cup \dots \cup F_k)^+ = F^+$$
- **Trade-off:**
  - 3NF synthesis **always guarantees** both lossless join and dependency preservation.
  - BCNF decomposition **always guarantees** lossless join, but **may not preserve dependencies**.

---

## 3. Common Misconceptions & Traps

| Misconception | Correction |
| :--- | :--- |
| **"BCNF always preserves functional dependencies."** | False. In some schemas (e.g. $R(A, B, C)$ with $AB \to C$ and $C \to B$), achieving BCNF forces a decomposition that fails to preserve $AB \to C$. |
| **"A relation with only single-attribute candidate keys can violate 2NF."** | False. Partial dependencies require a composite candidate key. If all candidate keys are single attributes, the relation is **automatically in 2NF**. |
| **"Lossless join means no data is lost upon decomposition."** | Lossless join means **no spurious tuples are created** when joining back. Lossy join actually creates *spurious (false)* tuples! |
