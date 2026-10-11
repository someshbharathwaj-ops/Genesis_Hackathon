"""Curriculum dependency validation and DAG cycle detection service."""

from collections import defaultdict

from app.core.errors import RecallException
from app.models.curriculum import LearningObjective


class CurriculumValidator:
    """Deterministic, course-scoped curriculum prerequisite graph validator."""

    PROPOSED_NODE_ID = "__PROPOSED_OBJECTIVE__"

    @staticmethod
    def detect_cycle_in_graph(graph: dict[str, list[str]]) -> list[str] | None:
        """Detect any directed cycle of arbitrary length using deterministic 3-color DFS.

        Edge direction:
            If u requires v, then edge u -> v is present in the graph.

        Returns:
            The cycle path (e.g. ['id_A', 'id_B', 'id_C', 'id_A']) if a cycle exists, else None.
        """
        # Colors: 0 = unvisited (white), 1 = visiting (gray), 2 = visited (black)
        color: dict[str, int] = defaultdict(int)
        current_path: list[str] = []

        all_nodes = sorted(graph.keys())

        def dfs(node: str) -> list[str] | None:
            color[node] = 1
            current_path.append(node)

            for neighbor in sorted(graph.get(node, [])):
                neighbor_color = color[neighbor]
                if neighbor_color == 1:
                    if neighbor in current_path:
                        cycle_start_idx = current_path.index(neighbor)
                        return current_path[cycle_start_idx:] + [neighbor]
                    return [neighbor, node, neighbor]
                elif neighbor_color == 0:
                    cycle = dfs(neighbor)
                    if cycle is not None:
                        return cycle

            current_path.pop()
            color[node] = 2
            return None

        for start_node in all_nodes:
            if color[start_node] == 0:
                detected_cycle = dfs(start_node)
                if detected_cycle is not None:
                    return detected_cycle

        return None

    @classmethod
    def validate_new_objective(
        cls,
        course_id: str,
        topic_id: str,
        proposed_code: str,
        proposed_prerequisites: list[str],
        existing_objectives: list[LearningObjective],
    ) -> None:
        """Validate prerequisites for a proposed learning objective.

        Enforces:
        1. Duplicate code rejection within the target topic.
        2. Self-cycle rejection (length-1 cycle).
        3. Course-scoped prerequisite resolution with ambiguity detection.
        4. Integrity of pre-existing dependency edges.
        5. Arbitrary-length cycle detection across the curriculum DAG.
        """
        # 1. Reject duplicate code in the target topic (per UniqueConstraint(topic_id, code))
        for lo in existing_objectives:
            if lo.topic_id == topic_id and lo.code == proposed_code:
                raise RecallException(
                    status_code=409,
                    code="OBJECTIVE_ALREADY_EXISTS",
                    title="Objective Code Conflict",
                    detail=(
                        f"Learning objective with code '{proposed_code}' "
                        f"already exists in this topic."
                    ),
                )

        # 2. Reject self-cycle
        if proposed_code in proposed_prerequisites:
            raise RecallException(
                status_code=400,
                code="CYCLIC_PREREQUISITE",
                title="Cyclic Prerequisite Rejected",
                detail=(
                    f"Learning objective '{proposed_code}' cannot declare "
                    f"itself as a prerequisite."
                ),
            )

        # 3. Index existing objectives by ID and by code
        lo_by_id: dict[str, LearningObjective] = {lo.id: lo for lo in existing_objectives}
        los_by_code: dict[str, list[LearningObjective]] = defaultdict(list)
        for lo in existing_objectives:
            los_by_code[lo.code].append(lo)

        # Build display label mapping for readable cycle formatting
        node_display_name: dict[str, str] = {}
        for lo in existing_objectives:
            if len(los_by_code[lo.code]) == 1:
                node_display_name[lo.id] = lo.code
            else:
                node_display_name[lo.id] = f"{lo.code} ({lo.id})"
        node_display_name[cls.PROPOSED_NODE_ID] = proposed_code

        def resolve_ref(ref: str, context: str) -> str:
            """Resolve a reference string (ID or code) to a unique node ID."""
            # Direct ID match
            if ref in lo_by_id:
                return ref

            # Reference to proposed objective code
            if ref == proposed_code:
                return cls.PROPOSED_NODE_ID

            # Code match
            if ref in los_by_code:
                matching = los_by_code[ref]
                if len(matching) == 1:
                    return matching[0].id
                matched_details = ", ".join(
                    f"'{m.code}' in topic '{m.topic_id}' (id={m.id})" for m in matching
                )
                raise RecallException(
                    status_code=400,
                    code="AMBIGUOUS_PREREQUISITE",
                    title="Ambiguous Prerequisite Reference",
                    detail=(
                        f"{context} code '{ref}' is ambiguous in course '{course_id}': "
                        f"matches multiple objectives: {matched_details}. "
                        f"Disambiguate by specifying the objective UUID."
                    ),
                )

            # Unresolved reference
            raise RecallException(
                status_code=400,
                code="UNRESOLVED_PREREQUISITE",
                title="Unresolved Prerequisite Rejected",
                detail=(
                    f"{context} '{ref}' cannot be resolved to an existing "
                    f"learning objective in course '{course_id}'."
                ),
            )

        # 4. Construct directed graph using stable primary IDs as nodes
        # Edge direction: u -> v means u requires v
        graph: dict[str, list[str]] = defaultdict(list)

        # Initialize all existing nodes and proposed node
        for lo in existing_objectives:
            graph[lo.id] = []
        graph[cls.PROPOSED_NODE_ID] = []

        # Validate and add pre-existing edges (ensures no silently omitted broken edges)
        for lo in existing_objectives:
            for p_ref in lo.prerequisite_objective_ids:
                resolved_id = resolve_ref(
                    p_ref,
                    context=f"Existing objective '{lo.code}' ({lo.id}) prerequisite",
                )
                graph[lo.id].append(resolved_id)

        # Validate and add proposed edges
        for p_ref in proposed_prerequisites:
            resolved_id = resolve_ref(
                p_ref,
                context=f"Proposed objective '{proposed_code}' prerequisite",
            )
            graph[cls.PROPOSED_NODE_ID].append(resolved_id)

        # 5. Detect cycles of arbitrary length
        cycle = cls.detect_cycle_in_graph(graph)
        if cycle:
            # Canonically rotate cycle: start at PROPOSED_NODE_ID if present,
            # or at the lexicographically lowest display name
            unique_nodes = cycle[:-1]
            if cls.PROPOSED_NODE_ID in unique_nodes:
                start_idx = unique_nodes.index(cls.PROPOSED_NODE_ID)
            else:
                start_idx = min(
                    range(len(unique_nodes)),
                    key=lambda i: node_display_name.get(unique_nodes[i], unique_nodes[i]),
                )
            rotated = (
                unique_nodes[start_idx:] + unique_nodes[:start_idx] + [unique_nodes[start_idx]]
            )
            cycle_str = " -> ".join(node_display_name.get(nid, nid) for nid in rotated)
            raise RecallException(
                status_code=400,
                code="CYCLIC_PREREQUISITE",
                title="Cyclic Prerequisite Rejected",
                detail=f"Cyclic dependency detected in prerequisite graph: {cycle_str}.",
            )
