# CS340 Database Management Systems: Functional Dependencies and Normalization
**Authoritative Course Reference Notes**
**Instructor:** Prof. E. F. Codd

## 1. Functional Dependencies and Armstrong's Axioms

A functional dependency (FD) $X \to Y$ between two sets of attributes $X$ and $Y$ in relation schema $R$ denotes that whenever two tuples agree on attributes $X$, they must also agree on attributes $Y$.

Armstrong's Axioms form a sound and complete inference system for functional dependencies:
1. **Reflexivity Rule**: If $Y \subseteq X$, then $X \to Y$. (Trivial functional dependency).
2. **Augmentation Rule**: If $X \to Y$, then $XZ \to YZ$ for any attribute set $Z$.
3. **Transitivity Rule**: If $X \to Y$ and $Y \to Z$, then $X \to Z$.

Secondary derived inference rules:
- **Union Rule**: If $X \to Y$ and $X \to Z$, then $X \to YZ$.
- **Decomposition (Projectivity) Rule**: If $X \to YZ$, then $X \to Y$ and $X \to Z$.
- **Pseudotransitivity Rule**: If $X \to Y$ and $WY \to Z$, then $WX \to Z$.

## 2. Attribute Closure ($X^+$) Algorithm

The attribute closure $X^+$ of an attribute set $X$ under a set of functional dependencies $F$ is the set of all attributes functionally determined by $X$ under $F$.

**Closure Computation Algorithm:**
1. Initialize $closure = X$.
2. Repeatedly scan each functional dependency $U \to V \in F$:
   - If $U \subseteq closure$, then add $V$ to $closure$ ($closure = closure \cup V$).
3. Repeat step 2 until a complete pass produces no new attributes.
4. Return $closure$.

**Example:**
Given $R(A, B, C, D)$ and $F = \{A \to B, B \to C, C \to D\}$:
- Start with $\{A\}$.
- $A \to B$ applies: $\{A, B\}$.
- $B \to C$ applies: $\{A, B, C\}$.
- $C \to D$ applies: $\{A, B, C, D\}$.
- Therefore, $\{A\}^+ = \{A, B, C, D\}$.

## 3. Superkeys and Candidate Keys

- **Superkey**: A set of attributes $K \subseteq R$ is a superkey if $K^+ = R$ (the closure determines all attributes in the relation schema).
- **Candidate Key**: A candidate key $K$ is a minimal superkey; that is, $K^+ = R$ and for any proper subset $K' \subset K$, $K'^+$ does not determine $R$.
- **Primary Key**: An arbitrarily designated candidate key chosen as the primary identifier.

## 4. Canonical / Minimal Cover of Functional Dependencies

A minimal cover $F_{min}$ for a set of dependencies $F$ is an equivalent set of dependencies $(F_{min} \equiv F)$ satisfying:
1. Every right-hand side has exactly one attribute (Standard form: $X \to A$).
2. No extraneous attributes exist on the left-hand side: For $X \to A$ with $B \in X$, if $(X - \{B\})^+ \supseteq A$, attribute $B$ is extraneous and must be removed.
3. No redundant dependencies: If $(F - \{X \to A\}) \models X \to A$, then $X \to A$ is redundant and must be removed.

## 5. Normal Forms and Lossless Decomposition

- **First Normal Form (1NF)**: All attribute domains contain only atomic, indivisible values.
- **Second Normal Form (2NF)**: In 1NF and no non-prime attribute is partially dependent on any candidate key (every non-prime attribute is fully functionally dependent on every candidate key).
- **Third Normal Form (3NF)**: In 2NF and for every non-trivial FD $X \to A$, either $X$ is a superkey, or $A$ is a prime attribute (part of some candidate key).
- **Boyce-Codd Normal Form (BCNF)**: For every non-trivial FD $X \to A$, $X$ must be a superkey.
- **Lossless-Join Decomposition**: A decomposition of $R$ into $R_1, R_2$ is lossless-join with respect to $F$ if and only if $(R_1 \cap R_2) \to R_1 \in F^+$ or $(R_1 \cap R_2) \to R_2 \in F^+$.
