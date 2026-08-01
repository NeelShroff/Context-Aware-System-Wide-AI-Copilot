import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.knowledge_graph import KnowledgeGraph
from src.history_manager import HistoryManager

def main():
    print("=" * 60)
    print("      SYSTEM-WIDE AI COPILOT - KNOWLEDGE GRAPH VIEWER")
    print("=" * 60)
    print()

    kg = KnowledgeGraph()
    if kg.neo4j_driver:
        print(" [STATUS] Connected to Native Neo4j Server (bolt://localhost:7687)")
    else:
        print(" [STATUS] Using Embedded Local Graph Engine (data/knowledge_graph.json)")
    print()

    # Query Graph Contents
    graph = kg._read_local_graph()
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", [])

    print(f"--- LEARNED GRAPH NODES ({len(nodes)} total) ---")
    for name, meta in nodes.items():
        node_type = meta.get("type", "CONCEPT")
        freq = meta.get("frequency", 1)
        last_seen = meta.get("last_seen", "")[:19].replace("T", " ")
        print(f" • [{node_type}] {name} (Used {freq}x, Last active: {last_seen})")

    print()
    print(f"--- GRAPH RELATIONSHIPS ({len(edges)} total) ---")
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        rel = edge.get("relation")
        weight = edge.get("weight", 1)
        print(f" • {src} ==[{rel} (x{weight})]==> {tgt}")

    print()
    print("=" * 60)
    print("--- APPLICATION HISTORY SUMMARY ---")
    history_mgr = HistoryManager()
    index_file = history_mgr.index_file
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            idx = json.load(f)
            print(f" Total Rewrites Logged: {idx.get('total_entries', 0)}")
            print(" Per-Application Logs:")
            for app, meta in idx.get("applications", {}).items():
                cnt = meta.get("count", 0)
                scen = meta.get("last_scenario", "")
                print(f"   - {app}: {cnt} interactions (Last scenario: {scen})")
    print("=" * 60)

if __name__ == "__main__":
    main()
