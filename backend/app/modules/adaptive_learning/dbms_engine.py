"""Deterministic Relational DBMS Algorithm Engine.

Implements pure, verified algorithms for:
- Attribute Closure (Armstrong's Axioms)
- Candidate Key and Superkey derivation
- Prime and Non-Prime attribute partitioning
- Minimal Cover / Canonical Cover computation
- Normal Form verification (1NF, 2NF, 3NF, BCNF) with violation diagnostics
- Lossless Join decomposition testing (Chase test & 2-way intersection key test)
- Dependency Preservation testing
"""

from itertools import combinations
from typing import Any, Dict, FrozenSet, List, Set, Tuple

FDType = Tuple[FrozenSet[str], FrozenSet[str]]


def parse_attributes(s: str) -> Set[str]:
    """Parse comma/space/character separated attributes into clean uppercase string set."""
    if not s:
        return set()
    cleaned = s.replace(",", " ").strip()
    tokens = [tok.strip().upper() for tok in cleaned.split() if tok.strip()]
    if len(tokens) == 1 and len(tokens[0]) > 1 and not s.strip().startswith("{"):
        # e.g. "ABC" -> {"A", "B", "C"}
        return {char for char in tokens[0] if char.isalnum()}
    attrs: Set[str] = set()
    for tok in tokens:
        clean_tok = tok.strip("{}")
        if clean_tok:
            attrs.add(clean_tok)
    return attrs


def parse_fd(fd_str: str) -> FDType:
    """Parse functional dependency string e.g. 'A -> B' or 'AB -> C'."""
    arrow = "->"
    if "->" not in fd_str:
        if "→" in fd_str:
            arrow = "→"
        else:
            raise ValueError(f"Invalid FD string '{fd_str}', expected '->' or '→'")

    left_str, right_str = fd_str.split(arrow, 1)
    lhs = frozenset(parse_attributes(left_str))
    rhs = frozenset(parse_attributes(right_str))
    return lhs, rhs


def parse_fd_list(fd_strings: List[str]) -> List[FDType]:
    """Parse list of FD strings into canonical FD tuples."""
    return [parse_fd(s) for s in fd_strings if s.strip()]


def compute_attribute_closure(
    initial_attrs: Set[str] | FrozenSet[str],
    fds: List[FDType],
) -> Set[str]:
    """Compute attribute closure X+ using Armstrong's Axioms fixpoint iteration."""
    closure = set(initial_attrs)
    changed = True

    while changed:
        changed = False
        for lhs, rhs in fds:
            if lhs.issubset(closure):
                for attr in rhs:
                    if attr not in closure:
                        closure.add(attr)
                        changed = True

    return closure


def is_superkey(
    candidate_attrs: Set[str] | FrozenSet[str],
    relation_attrs: Set[str] | FrozenSet[str],
    fds: List[FDType],
) -> bool:
    """Returns True if candidate_attrs closure covers all relation_attrs."""
    closure = compute_attribute_closure(candidate_attrs, fds)
    return set(relation_attrs).issubset(closure)


def find_all_candidate_keys(
    relation_attrs: Set[str] | FrozenSet[str],
    fds: List[FDType],
) -> Set[FrozenSet[str]]:
    """Find all minimal candidate keys for relation_attrs under fds."""
    all_attrs = list(relation_attrs)
    n = len(all_attrs)
    candidate_keys: Set[FrozenSet[str]] = set()

    # Search by increasing size k=1..n
    for k in range(1, n + 1):
        for combo in combinations(all_attrs, k):
            subset = frozenset(combo)
            # Check if any existing candidate key is a proper subset
            if any(ck.issubset(subset) for ck in candidate_keys):
                continue

            if is_superkey(subset, relation_attrs, fds):
                candidate_keys.add(subset)

    return candidate_keys


def get_prime_attributes(candidate_keys: Set[FrozenSet[str]]) -> Set[str]:
    """Return set of all attributes that belong to at least one candidate key."""
    primes: Set[str] = set()
    for ck in candidate_keys:
        primes.update(ck)
    return primes


def is_fd_implied(fd: FDType, fds: List[FDType]) -> bool:
    """Returns True if FD X -> Y is implied by the set fds."""
    lhs, rhs = fd
    closure = compute_attribute_closure(lhs, fds)
    return rhs.issubset(closure)


def are_fd_sets_equivalent(fds1: List[FDType], fds2: List[FDType]) -> bool:
    """Returns True if fds1 and fds2 generate identical closures (F+ = G+)."""
    for fd in fds1:
        if not is_fd_implied(fd, fds2):
            return False
    for fd in fds2:
        if not is_fd_implied(fd, fds1):
            return False
    return True


def compute_minimal_cover(fds: List[FDType]) -> List[FDType]:
    """Compute canonical / minimal cover of a set of functional dependencies.

    Steps:
    1. Singleton right-hand side decomposition.
    2. Elimination of extraneous left-hand side attributes.
    3. Elimination of redundant functional dependencies.
    """
    # Step 1: Singleton RHS
    singletons: List[FDType] = []
    for lhs, rhs in fds:
        for attr in rhs:
            singletons.append((lhs, frozenset([attr])))

    # Step 2: Eliminate extraneous LHS attributes
    reduced_lhs: List[FDType] = []
    for lhs, rhs in singletons:
        current_lhs = set(lhs)
        for attr in list(lhs):
            if len(current_lhs) > 1:
                test_lhs = current_lhs - {attr}
                # Check if test_lhs closure under original singletons includes rhs
                if rhs.issubset(compute_attribute_closure(test_lhs, singletons)):
                    current_lhs = test_lhs
        reduced_lhs.append((frozenset(current_lhs), rhs))

    # Step 3: Eliminate redundant FDs
    final_cover: List[FDType] = []
    for i, current_fd in enumerate(reduced_lhs):
        # Build candidate pool without current_fd
        remaining = reduced_lhs[:i] + reduced_lhs[i + 1:]
        lhs, rhs = current_fd
        # If remaining FDs already imply current_fd, current_fd is redundant
        if not rhs.issubset(compute_attribute_closure(lhs, remaining)):
            final_cover.append(current_fd)

    return final_cover


def check_normal_form(
    relation_attrs: Set[str] | FrozenSet[str],
    fds: List[FDType],
) -> Dict[str, Any]:
    """Analyze relation and determine highest normal form achieved (1NF, 2NF, 3NF, BCNF)
    along with specific violation details.
    """
    candidate_keys = find_all_candidate_keys(relation_attrs, fds)
    primes = get_prime_attributes(candidate_keys)
    non_primes = set(relation_attrs) - primes

    violations: Dict[str, List[str]] = {
        "2NF": [],
        "3NF": [],
        "BCNF": [],
    }

    # Verify each non-trivial FD X -> Y where X != Y
    for lhs, rhs in fds:
        non_trivial_rhs = rhs - lhs
        if not non_trivial_rhs:
            continue

        is_super = is_superkey(lhs, relation_attrs, fds)

        # BCNF condition: lhs must be a superkey
        if not is_super:
            violations["BCNF"].append(
                f"{''.join(sorted(lhs))} -> {''.join(sorted(non_trivial_rhs))} (LHS is not superkey)"
            )

            # 3NF condition: each attribute in RHS must be prime, or LHS is superkey
            non_prime_rhs = non_trivial_rhs - primes
            if non_prime_rhs:
                violations["3NF"].append(
                    f"{''.join(sorted(lhs))} -> {''.join(sorted(non_prime_rhs))} "
                    f"(LHS not superkey and RHS attribute(s) not prime)"
                )

            # 2NF condition: no non-prime attribute may depend on proper subset of candidate key
            for ck in candidate_keys:
                if lhs.issubset(ck) and lhs != ck:
                    partial_non_primes = non_trivial_rhs.intersection(non_primes)
                    if partial_non_primes:
                        violations["2NF"].append(
                            f"{''.join(sorted(lhs))} -> {''.join(sorted(partial_non_primes))} "
                            f"(Partial dependency on candidate key {''.join(sorted(ck))})"
                        )

    # Determine highest normal form
    if not violations["2NF"] and not violations["3NF"] and not violations["BCNF"]:
        highest = "BCNF"
    elif not violations["2NF"] and not violations["3NF"]:
        highest = "3NF"
    elif not violations["2NF"]:
        highest = "2NF"
    else:
        highest = "1NF"

    return {
        "candidate_keys": [list(sorted(ck)) for ck in candidate_keys],
        "prime_attributes": list(sorted(primes)),
        "non_prime_attributes": list(sorted(non_primes)),
        "highest_normal_form": highest,
        "violations": violations,
    }


def is_lossless_join(
    relation_attrs: Set[str] | FrozenSet[str],
    decompositions: List[Set[str]],
    fds: List[FDType],
) -> bool:
    """Determine if decomposition of relation_attrs is lossless under fds.

    For 2-relation decomposition (R1, R2): lossless iff (R1 ∩ R2) -> R1 or (R1 ∩ R2) -> R2.
    For n-relation decomposition: executes Chase algorithm matrix test.
    """
    if len(decompositions) < 2:
        return True

    if len(decompositions) == 2:
        r1, r2 = decompositions[0], decompositions[1]
        common = r1.intersection(r2)
        if not common:
            return False
        common_closure = compute_attribute_closure(common, fds)
        return r1.issubset(common_closure) or r2.issubset(common_closure)

    # General n-relation Chase algorithm
    attrs_list = list(relation_attrs)
    attr_idx = {attr: idx for idx, attr in enumerate(attrs_list)}
    m = len(decompositions)
    n = len(attrs_list)

    # Matrix: cell (i, j) is 'a_j' if decomposition i contains attr j, else 'b_ij'
    matrix: List[List[str]] = [
        [f"a_{j}" if attrs_list[j] in decompositions[i] else f"b_{i}_{j}" for j in range(n)]
        for i in range(m)
    ]

    changed = True
    while changed:
        changed = False
        for lhs, rhs in fds:
            lhs_indices = [attr_idx[a] for a in lhs if a in attr_idx]
            rhs_indices = [attr_idx[a] for a in rhs if a in attr_idx]
            if not lhs_indices or not rhs_indices:
                continue

            # Group rows that have matching values for all lhs indices
            groups: Dict[Tuple[str, ...], List[int]] = {}
            for row_idx in range(m):
                key = tuple(matrix[row_idx][col] for col in lhs_indices)
                groups.setdefault(key, []).append(row_idx)

            for matching_rows in groups.values():
                if len(matching_rows) <= 1:
                    continue
                # For each rhs attribute, unify values across matching rows
                for col in rhs_indices:
                    # Prefer distinguished symbol 'a_col'
                    target_val = None
                    for r in matching_rows:
                        if matrix[r][col] == f"a_{col}":
                            target_val = f"a_{col}"
                            break
                    if target_val is None:
                        target_val = matrix[matching_rows[0]][col]

                    for r in matching_rows:
                        if matrix[r][col] != target_val:
                            matrix[r][col] = target_val
                            changed = True

    # Check if any row in the matrix is entirely distinguished symbols [a_0, a_1, ..., a_n-1]
    for row in matrix:
        if all(cell == f"a_{j}" for j, cell in enumerate(row)):
            return True

    return False


def is_dependency_preserving(
    decompositions: List[Set[str]],
    fds: List[FDType],
) -> bool:
    """Determine if decomposition preserves all functional dependencies in fds.

    For each X -> Y in fds, verifies whether Y is contained in the closure of X
    projected across all decomposition components.
    """
    for lhs, rhs in fds:
        result = set(lhs)
        changed = True
        while changed:
            changed = False
            for r in decompositions:
                # Project result onto relation r
                proj = result.intersection(r)
                if proj:
                    # Compute closure under original fds and intersect with r
                    proj_closure = compute_attribute_closure(proj, fds).intersection(r)
                    if not proj_closure.issubset(result):
                        result.update(proj_closure)
                        changed = True

        if not rhs.issubset(result):
            return False

    return True
