"""
research_ops/utils/lineage.py

血缘 DAG 工具。
节点：任意资源 ID（Dataset / Feature / Strategy / Model / Experiment...）
边：有向，表示「下游依赖上游」。

用法：
    g = LineageGraph()
    g.add_node("DS-001", label="HS300日线", node_type="dataset")
    g.add_node("FT-001", label="20日动量",  node_type="feature")
    g.add_edge("DS-001", "FT-001")          # FT-001 依赖 DS-001
    g.upstream("FT-001")   → ["DS-001"]
    g.downstream("DS-001") → ["FT-001"]
    g.ancestors("FT-001")  → {"DS-001"}     # 递归所有祖先
"""
from __future__ import annotations
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set


class LineageNode:
    __slots__ = ("node_id", "label", "node_type", "metadata")

    def __init__(
        self,
        node_id:   str,
        label:     str = "",
        node_type: str = "unknown",
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> None:
        self.node_id   = node_id
        self.label     = label or node_id
        self.node_type = node_type
        self.metadata  = metadata or {}

    def to_dict(self) -> dict:
        return {
            "node_id":   self.node_id,
            "label":     self.label,
            "node_type": self.node_type,
        }


class LineageGraph:
    """
    有向无环图（DAG）血缘追踪。
    内部使用邻接表（出边 + 入边）保证 O(1) 邻居查询。
    """

    def __init__(self) -> None:
        self._nodes:      Dict[str, LineageNode] = {}
        self._out_edges:  Dict[str, Set[str]]    = defaultdict(set)  # src → {dst}
        self._in_edges:   Dict[str, Set[str]]    = defaultdict(set)  # dst → {src}

    # ------------------------------------------------------------------
    # 节点管理
    # ------------------------------------------------------------------

    def add_node(
        self,
        node_id:   str,
        label:     str = "",
        node_type: str = "unknown",
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> LineageNode:
        if node_id not in self._nodes:
            self._nodes[node_id] = LineageNode(node_id, label, node_type, metadata)
        else:
            node = self._nodes[node_id]
            if label:      node.label     = label
            if node_type:  node.node_type = node_type
            if metadata:   node.metadata.update(metadata)
        return self._nodes[node_id]

    def get_node(self, node_id: str) -> Optional[LineageNode]:
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> None:
        """删除节点及其所有关联边。"""
        if node_id not in self._nodes:
            return
        for dst in list(self._out_edges.get(node_id, [])):
            self._in_edges[dst].discard(node_id)
        for src in list(self._in_edges.get(node_id, [])):
            self._out_edges[src].discard(node_id)
        self._out_edges.pop(node_id, None)
        self._in_edges.pop(node_id, None)
        del self._nodes[node_id]

    def all_nodes(self) -> List[LineageNode]:
        return list(self._nodes.values())

    def node_count(self) -> int:
        return len(self._nodes)

    # ------------------------------------------------------------------
    # 边管理
    # ------------------------------------------------------------------

    def add_edge(self, src_id: str, dst_id: str) -> None:
        """
        添加有向边 src → dst（dst 依赖 src）。
        如果节点不存在则自动创建 stub。
        会拒绝形成环的边（避免死锁）。
        """
        if src_id not in self._nodes:
            self.add_node(src_id)
        if dst_id not in self._nodes:
            self.add_node(dst_id)
        if dst_id in self.ancestors(src_id):
            raise ValueError(
                f"Adding edge {src_id} → {dst_id} would create a cycle."
            )
        self._out_edges[src_id].add(dst_id)
        self._in_edges[dst_id].add(src_id)

    def remove_edge(self, src_id: str, dst_id: str) -> None:
        self._out_edges[src_id].discard(dst_id)
        self._in_edges[dst_id].discard(src_id)

    def has_edge(self, src_id: str, dst_id: str) -> bool:
        return dst_id in self._out_edges.get(src_id, set())

    def edge_count(self) -> int:
        return sum(len(v) for v in self._out_edges.values())

    # ------------------------------------------------------------------
    # 一跳查询
    # ------------------------------------------------------------------

    def upstream(self, node_id: str) -> List[str]:
        """直接上游（node_id 依赖的节点）。"""
        return list(self._in_edges.get(node_id, set()))

    def downstream(self, node_id: str) -> List[str]:
        """直接下游（依赖 node_id 的节点）。"""
        return list(self._out_edges.get(node_id, set()))

    # ------------------------------------------------------------------
    # 递归查询（BFS）
    # ------------------------------------------------------------------

    def ancestors(self, node_id: str) -> Set[str]:
        """所有祖先节点（递归上游）。"""
        visited: Set[str] = set()
        queue = deque(self._in_edges.get(node_id, set()))
        while queue:
            nid = queue.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            queue.extend(self._in_edges.get(nid, set()))
        return visited

    def descendants(self, node_id: str) -> Set[str]:
        """所有后代节点（递归下游）。"""
        visited: Set[str] = set()
        queue = deque(self._out_edges.get(node_id, set()))
        while queue:
            nid = queue.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            queue.extend(self._out_edges.get(nid, set()))
        return visited

    def full_lineage(self, node_id: str) -> Dict[str, Set[str]]:
        """返回 {"ancestors": {...}, "descendants": {...}}。"""
        return {
            "ancestors":   self.ancestors(node_id),
            "descendants": self.descendants(node_id),
        }

    # ------------------------------------------------------------------
    # 拓扑排序（Kahn 算法）
    # ------------------------------------------------------------------

    def topological_sort(self) -> List[str]:
        """
        返回拓扑排序后的节点 ID 列表。
        如存在环则抛出 ValueError。
        """
        in_degree = {nid: len(self._in_edges.get(nid, set()))
                     for nid in self._nodes}
        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        result: List[str] = []
        while queue:
            nid = queue.popleft()
            result.append(nid)
            for dst in self._out_edges.get(nid, set()):
                in_degree[dst] -= 1
                if in_degree[dst] == 0:
                    queue.append(dst)
        if len(result) != len(self._nodes):
            raise ValueError("Cycle detected in lineage graph.")
        return result

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [
                {"src": src, "dst": dst}
                for src, dsts in self._out_edges.items()
                for dst in dsts
            ],
        }

    def clear(self) -> None:
        self._nodes.clear()
        self._out_edges.clear()
        self._in_edges.clear()
