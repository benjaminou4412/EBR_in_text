"""
Valley map graph utilities for route-finding.

Loads the valley map from JSON and provides route-finding between locations,
intended as a scaffolding tool for LLM benchmark play.
"""

import json
from collections import deque
from pathlib import Path


def _load_map() -> dict[str, list[dict[str, str]]]:
    """Load the valley map JSON and return the locations dict."""
    map_path = Path(__file__).parent.parent / "reference JSON" / "valley_map.json"
    with open(map_path, encoding="utf-8") as f:
        data = json.load(f)
    return data["locations"]


_MAP: dict[str, list[dict[str, str]]] | None = None


def _get_map() -> dict[str, list[dict[str, str]]]:
    global _MAP
    if _MAP is None:
        _MAP = _load_map()
    return _MAP


def get_neighbors(location: str) -> list[dict[str, str]]:
    """Return the adjacent locations and their terrains for a given location."""
    graph = _get_map()
    if location not in graph:
        raise ValueError(f"Unknown location: '{location}'")
    return graph[location]["adj"]


def get_routes(
    origin: str,
    destination: str,
    max_extra_hops: int = 2,
) -> list[dict]:
    """Find all routes from origin to destination, up to max_extra_hops beyond the shortest.

    Returns a list of route dicts sorted by length, each containing:
        - "path": list of location names from origin to destination (inclusive)
        - "terrains": list of terrain types for each step
        - "steps": number of steps (len(terrains))
        - "has_river": whether any step crosses River terrain

    River edges are included in results (annotated) since the player may have
    a card that allows river crossing.
    """
    graph = _get_map()
    if origin not in graph:
        raise ValueError(f"Unknown origin: '{origin}'")
    if destination not in graph:
        raise ValueError(f"Unknown destination: '{destination}'")
    if origin == destination:
        return [{"path": [origin], "terrains": [], "steps": 0, "has_river": False}]

    # BFS to find shortest distance first
    shortest = _bfs_shortest(graph, origin, destination)
    if shortest is None:
        return []

    max_steps = shortest + max_extra_hops

    # DFS to enumerate all paths up to max_steps
    routes = []
    _dfs_all_paths(graph, origin, destination, max_steps, [origin], [], set([origin]), routes)

    routes.sort(key=lambda r: (r["steps"], r["has_river"], tuple(r["terrains"])))
    return routes


def _bfs_shortest(
    graph: dict[str, list[dict[str, str]]], origin: str, destination: str
) -> int | None:
    """BFS to find shortest path length (number of edges)."""
    queue = deque([(origin, 0)])
    visited = {origin}
    while queue:
        current, dist = queue.popleft()
        for edge in graph[current]["adj"]:
            neighbor = edge["to"]
            if neighbor == destination:
                return dist + 1
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return None


def _dfs_all_paths(
    graph: dict[str, list[dict[str, str]]],
    current: str,
    destination: str,
    max_steps: int,
    path: list[str],
    terrains: list[str],
    visited: set[str],
    results: list[dict],
) -> None:
    """DFS to find all simple paths up to max_steps."""
    if len(terrains) > max_steps:
        return
    if current == destination:
        has_river = "River" in terrains
        results.append({
            "path": list(path),
            "terrains": list(terrains),
            "steps": len(terrains),
            "has_river": has_river,
        })
        return
    if len(terrains) == max_steps:
        return
    for edge in graph[current]["adj"]:
        neighbor = edge["to"]
        if neighbor not in visited:
            visited.add(neighbor)
            path.append(neighbor)
            terrains.append(edge["terrain"])
            _dfs_all_paths(graph, neighbor, destination, max_steps, path, terrains, visited, results)
            terrains.pop()
            path.pop()
            visited.remove(neighbor)


def _select_diverse_routes(routes: list[dict], max_routes: int) -> list[dict]:
    """Greedily select routes that maximize location diversity.

    Always picks the shortest route first, then prefers routes whose intermediate
    locations (excluding origin/destination) overlap least with already-selected routes.
    Among equally diverse candidates, shorter routes are preferred.
    """
    if len(routes) <= max_routes:
        return routes

    selected: list[dict] = [routes[0]]
    seen_locations: set[str] = set(routes[0]["path"][1:-1])

    for _ in range(max_routes - 1):
        best = None
        best_score = (-1, 0)  # (new_count, -steps)
        for route in routes:
            if route in selected:
                continue
            intermediates = set(route["path"][1:-1])
            new_count = len(intermediates - seen_locations)
            score = (new_count, -route["steps"])
            if score > best_score:
                best_score = score
                best = route
        if best is None:
            break
        selected.append(best)
        seen_locations.update(best["path"][1:-1])

    selected.sort(key=lambda r: (r["steps"], r["has_river"], tuple(r["terrains"])))
    return selected


def format_routes(
    origin: str,
    destination: str,
    max_extra_hops: int = 2,
    can_cross_river: bool = False,
    max_routes: int = 10,
) -> str:
    """Human/LLM-readable route summary between two locations.

    If can_cross_river is False (default), river routes are filtered out
    before capping. A note is appended if any river routes were excluded.
    Always shows up to max_routes results.
    """
    routes = get_routes(origin, destination, max_extra_hops)

    if not routes:
        return f"No routes found from {origin} to {destination}."

    river_count = sum(1 for r in routes if r["has_river"])
    if not can_cross_river:
        routes = [r for r in routes if not r["has_river"]]

    if not routes:
        return (f"No routes found from {origin} to {destination} without River crossings.\n"
                f"({river_count} route(s) available if you can cross rivers.)")

    routes = _select_diverse_routes(routes, max_routes)

    lines = [f"Routes from {origin} to {destination} (showing {len(routes)}):\n"]
    for i, route in enumerate(routes, 1):
        if route["steps"] == 0:
            lines.append(f"  Route {i}: You are already at {destination}.\n")
            continue

        header = f"  Route {i} ({route['steps']} step{'s' if route['steps'] != 1 else ''}"
        if route["has_river"]:
            header += ", has River crossing"
        header += "):"
        lines.append(header)

        # Format as location (terrain) pairs
        stops = [route["path"][0]]
        for loc, terrain in zip(route["path"][1:], route["terrains"]):
            stops.append(f"{loc} ({terrain})")
        lines.append(f"    {' → '.join(stops)}")
        lines.append("")

    if not can_cross_river and river_count > 0:
        lines.append(f"  ({river_count} additional route(s) available with River crossing.)")
        lines.append("")

    return "\n".join(lines)
