"""
Contract Schemas for Multi-Agent Orchestration.

Defines the deterministic data contracts between agents and the orchestrator.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator


class AgentType(str, Enum):
    """Explicit enum of allowed downstream LLM agents."""
    RESEARCH = "research"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        # Handle common aliases (e.g. researcher -> research)
        if isinstance(value, str):
            val = value.strip().lower()
            if val in ("researcher", "research"):
                return cls.RESEARCH
            if val in ("coder", "coding", "code", "developer"):
                return cls.CODER
            if val in ("tester", "testing", "test", "qa"):
                return cls.TESTER
            if val in ("reviewer", "review", "audit"):
                return cls.REVIEWER
        return super()._missing_(value)


class PlanSubtask(BaseModel):
    """A discrete, actionable subtask within a plan."""
    id: str | int = Field(..., description="Unique identifier for the subtask")
    agent: AgentType = Field(..., description="The specialized agent assigned to execute this subtask")
    description: str = Field(..., description="Concrete, non-empty description of what this subtask accomplishes")
    dependencies: list[str | int] = Field(default_factory=list, description="IDs of subtasks that must complete before this one")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Subtask description cannot be empty")
        return v.strip()


class PlanContract(BaseModel):
    """
    Deterministic contract for a plan produced by the Planner Agent.
    Enforces strict structural and boundary invariants before any downstream execution.
    """
    task_summary: str = Field(..., description="One-line summary of the overall task")
    task_type: str = Field(default="coding", description="Type of task (coding, research, debugging, etc.)")
    complexity: str = Field(default="medium", description="Complexity estimate (low, medium, high)")
    required_agents: list[AgentType] = Field(..., description="List of agents required for this plan")
    subtasks: list[PlanSubtask] = Field(..., description="Ordered list of discrete subtasks (strictly 3 to 6)")
    execution_order: list[str | int] = Field(default_factory=list, description="Explicit subtask execution sequence")
    required_context: list[str] | str = Field(default="", description="Contextual prerequisites")
    required_tools: list[str] = Field(default_factory=list, description="Tools needed for execution")
    risks_or_unknowns: list[str] | str = Field(default="", description="Identified risks or ambiguities")
    file_manifest: list[str] = Field(default_factory=list, description="Target files to create or modify")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Acceptance criteria for task completion")

    @field_validator("task_summary")
    @classmethod
    def validate_summary(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Task summary cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_plan_invariants(self) -> PlanContract:
        # 1. Subtask count bounds: strictly [3, 6]
        count = len(self.subtasks)
        if count < 3:
            raise ValueError(f"PlanContract violation: Minimum 3 subtasks required, got {count}")
        if count > 6:
            raise ValueError(f"PlanContract violation: Maximum 6 subtasks allowed, got {count}. Plan rejected.")

        # 2. Unique subtask IDs
        seen_ids = set()
        for st in self.subtasks:
            sid = str(st.id)
            if sid in seen_ids:
                raise ValueError(f"PlanContract violation: Duplicate subtask ID '{st.id}' found")
            seen_ids.add(sid)

        # 3. Duplicate subtasks detection (normalized descriptions)
        seen_descriptions = set()
        for st in self.subtasks:
            norm_desc = " ".join(st.description.lower().split())
            if norm_desc in seen_descriptions:
                raise ValueError(f"PlanContract violation: Duplicate subtask detected: '{st.description}'")
            seen_descriptions.add(norm_desc)

        # 4. Validate dependency references
        for st in self.subtasks:
            for dep in st.dependencies:
                dep_str = str(dep)
                if dep_str == str(st.id):
                    raise ValueError(f"PlanContract violation: Subtask '{st.id}' cannot depend on itself")
                if dep_str not in seen_ids:
                    raise ValueError(f"PlanContract violation: Subtask '{st.id}' references non-existent dependency '{dep}'")

        # 5. Validate execution_order references if provided
        if self.execution_order:
            for item in self.execution_order:
                item_str = str(item)
                if item_str not in seen_ids:
                    raise ValueError(f"PlanContract violation: execution_order references unknown subtask ID '{item}'")

        return self

    def to_markdown(self) -> str:
        """Render the validated plan as standardized markdown."""
        lines = [
            f"### Task Summary: {self.task_summary}",
            f"**Task Type**: {self.task_type}",
            f"**Complexity**: {self.complexity}",
            f"**Required Agents**: {', '.join(a.value for a in self.required_agents)}",
            "",
            "### Subtasks:",
        ]
        for st in self.subtasks:
            dep_text = f" (depends on: {', '.join(str(d) for d in st.dependencies)})" if st.dependencies else ""
            lines.append(f"{st.id}. **[{st.agent.value.upper()}]**: {st.description}{dep_text}")

        if self.file_manifest:
            lines.extend(["", "### File Manifest:"])
            for fm in self.file_manifest:
                lines.append(f"- `{fm}`")

        if self.acceptance_criteria:
            lines.extend(["", "### Acceptance Criteria:"])
            for ac in self.acceptance_criteria:
                lines.append(f"- {ac}")

        lines.extend(["", f"REQUIRED_AGENTS: {', '.join(a.value for a in self.required_agents)}"])
        return "\n".join(lines)


class GraphNodeType(str, Enum):
    """Allowed node types in a dynamic workflow graph."""
    PLANNER = "planner"
    RESEARCH = "research"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    CUSTOM = "custom"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            val = value.strip().lower()
            if val in ("planner", "plan"):
                return cls.PLANNER
            if val in ("research", "researcher"):
                return cls.RESEARCH
            if val in ("coder", "code", "coding", "developer"):
                return cls.CODER
            if val in ("tester", "test", "testing", "qa"):
                return cls.TESTER
            if val in ("reviewer", "review", "audit"):
                return cls.REVIEWER
            if val in ("custom", "agent", "fallback"):
                return cls.CUSTOM
        return super()._missing_(value)


class GraphNode(BaseModel):
    """A node in a dynamic workflow graph."""
    id: str = Field(..., description="Unique non-empty identifier for the node")
    type: GraphNodeType = Field(default=GraphNodeType.PLANNER, description="Type of the node agent")
    config: dict[str, Any] = Field(default_factory=dict, description="Optional node-specific configuration")

    @field_validator("id")
    @classmethod
    def validate_node_id(cls, v: Any) -> str:
        if v is None or not str(v).strip():
            raise ValueError("Node ID cannot be empty or null")
        return str(v).strip()


class GraphEdge(BaseModel):
    """A directed edge connecting two nodes in a dynamic workflow graph."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")

    @field_validator("source", "target")
    @classmethod
    def validate_edge_endpoint(cls, v: Any) -> str:
        if v is None or not str(v).strip():
            raise ValueError("Edge source and target must be non-empty strings")
        return str(v).strip()


class GraphContract(BaseModel):
    """
    Deterministic contract for a dynamic workflow graph.
    Enforces non-empty nodes, unique IDs, valid edge endpoints, cycle detection,
    and reachability invariants before compiling a StateGraph.
    """
    nodes: list[GraphNode] = Field(..., description="List of nodes in the graph (1 to 20)")
    edges: list[GraphEdge] = Field(default_factory=list, description="List of directed edges")

    @model_validator(mode="after")
    def validate_graph_invariants(self) -> GraphContract:
        # 1. Reject empty graph
        if not self.nodes:
            raise ValueError("GraphContract violation: Graph must contain at least 1 node")

        # 2. Maximum graph size (20 nodes)
        if len(self.nodes) > 20:
            raise ValueError(f"GraphContract violation: Maximum 20 nodes allowed in dynamic graph, got {len(self.nodes)}")

        # 3. Unique node IDs
        seen_node_ids = set()
        for node in self.nodes:
            if node.id in seen_node_ids:
                raise ValueError(f"GraphContract violation: Duplicate node ID '{node.id}' found")
            seen_node_ids.add(node.id)

        # If edges are provided, validate edge endpoints, uniqueness, self-loops, reachability, and acyclicity
        if self.edges:
            seen_edges = set()
            adj: dict[str, list[str]] = {nid: [] for nid in seen_node_ids}
            in_degree: dict[str, int] = {nid: 0 for nid in seen_node_ids}

            for edge in self.edges:
                # 4 & 5. Source and target existence
                if edge.source not in seen_node_ids:
                    raise ValueError(f"GraphContract violation: Edge references non-existent source node '{edge.source}'")
                if edge.target not in seen_node_ids:
                    raise ValueError(f"GraphContract violation: Edge references non-existent target node '{edge.target}'")

                # Self-loops
                if edge.source == edge.target:
                    raise ValueError(f"GraphContract violation: Self-loop detected on node '{edge.source}'")

                # 6. Duplicate edges
                edge_pair = (edge.source, edge.target)
                if edge_pair in seen_edges:
                    raise ValueError(f"GraphContract violation: Duplicate edge from '{edge.source}' to '{edge.target}'")
                seen_edges.add(edge_pair)

                adj[edge.source].append(edge.target)
                in_degree[edge.target] += 1

            # 7. Cycle detection using Kahn's algorithm
            queue = [nid for nid, deg in in_degree.items() if deg == 0]
            visited_count = 0
            while queue:
                curr = queue.pop(0)
                visited_count += 1
                for neighbor in adj[curr]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            if visited_count < len(self.nodes):
                raise ValueError("GraphContract violation: Directed cycle detected in graph topology")

            # 8. Reachability check from START node (nodes[0].id)
            start_node_id = self.nodes[0].id
            reachable = set()
            dfs_queue = [start_node_id]
            while dfs_queue:
                curr = dfs_queue.pop()
                if curr not in reachable:
                    reachable.add(curr)
                    dfs_queue.extend(adj[curr])

            unreachable = seen_node_ids - reachable
            if unreachable:
                raise ValueError(f"GraphContract violation: Unreachable node(s) detected: {sorted(list(unreachable))}")

        return self
