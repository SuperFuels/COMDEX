import ast, os
from collections import defaultdict

PROJECT_DIR = "backend"
graph = defaultdict(set)
all_cycles = set()

def collect_imports(filepath, module_name):
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
        except Exception:
            return
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("backend"):
                    graph[module_name].add(node.module)
            elif isinstance(node, ast.Import):
                for name in node.names:
                    if name.name.startswith("backend"):
                        graph[module_name].add(name.name)

def module_name_from_path(path):
    path = path.replace(".py", "").replace("/", ".")
    return path if path.startswith("backend") else f"backend.{path.split('backend.',1)[-1]}"

for root, _, files in os.walk(PROJECT_DIR):
    for file in files:
        if file.endswith(".py"):
            full_path = os.path.join(root, file)
            module = module_name_from_path(full_path)
            collect_imports(full_path, module)

def dfs(node, path, visited):
    path.append(node)
    visited.add(node)
    for neighbor in graph.get(node, []):
        if neighbor in path:
            cycle = tuple(path[path.index(neighbor):] + [neighbor])
            all_cycles.add(cycle)
        elif neighbor not in visited:
            dfs(neighbor, path.copy(), visited.copy())

print("🔍 Scanning for circular imports (deduped)...\n")
for mod in list(graph.keys()):
    dfs(mod, [], set())

# 📦 Output results
sorted_cycles = sorted(all_cycles, key=lambda x: (len(x), x))
for i, cycle in enumerate(sorted_cycles[:25], 1):  # Top 25 only
    print(f"🌀 Cycle {i}:")
    for step in cycle:
        print(f"  -> {step}")
    print()
print(f"✅ Found {len(all_cycles)} unique cycles (showing top 25)")