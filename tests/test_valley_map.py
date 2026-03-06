"""Tests for the valley map route-finding utility."""

import unittest
from ebr.valley_map import get_neighbors, get_routes, format_routes


class GetNeighborsTests(unittest.TestCase):
    def test_lone_tree_station_neighbors(self):
        neighbors = get_neighbors("Lone Tree Station")
        dest_names = {n["to"] for n in neighbors}
        self.assertEqual(dest_names, {
            "Atrox Mountain", "Boulder Field", "Ancestor's Grove", "White Sky"
        })

    def test_neighbor_terrain_included(self):
        neighbors = get_neighbors("Lone Tree Station")
        bf_edge = next(n for n in neighbors if n["to"] == "Boulder Field")
        self.assertEqual(bf_edge["terrain"], "Woods")

    def test_unknown_location_raises(self):
        with self.assertRaises(ValueError):
            get_neighbors("Nonexistent Place")

    def test_marsh_of_rebirth_has_no_neighbors(self):
        neighbors = get_neighbors("Marsh of Rebirth")
        self.assertEqual(neighbors, [])


class GetRoutesTests(unittest.TestCase):
    def test_same_location_returns_zero_step_route(self):
        routes = get_routes("Spire", "Spire")
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0]["steps"], 0)
        self.assertEqual(routes[0]["path"], ["Spire"])

    def test_adjacent_locations_one_step(self):
        routes = get_routes("Lone Tree Station", "Boulder Field")
        shortest = routes[0]
        self.assertEqual(shortest["steps"], 1)
        self.assertEqual(shortest["path"], ["Lone Tree Station", "Boulder Field"])
        self.assertEqual(shortest["terrains"], ["Woods"])

    def test_shortest_route_found_first(self):
        routes = get_routes("Lone Tree Station", "Spire")
        self.assertEqual(routes[0]["steps"], 2)

    def test_river_crossing_annotated(self):
        routes = get_routes("Lone Tree Station", "Spire")
        river_route = next(r for r in routes if r["path"] == [
            "Lone Tree Station", "White Sky", "Spire"
        ])
        self.assertTrue(river_route["has_river"])

    def test_non_river_routes_not_flagged(self):
        routes = get_routes("Lone Tree Station", "Spire")
        non_river = [r for r in routes if not r["has_river"]]
        self.assertTrue(len(non_river) > 0)
        for route in non_river:
            self.assertNotIn("River", route["terrains"])

    def test_no_route_to_isolated_location(self):
        routes = get_routes("Lone Tree Station", "Marsh of Rebirth")
        self.assertEqual(routes, [])

    def test_unknown_origin_raises(self):
        with self.assertRaises(ValueError):
            get_routes("Nowhere", "Spire")

    def test_unknown_destination_raises(self):
        with self.assertRaises(ValueError):
            get_routes("Spire", "Nowhere")

    def test_max_extra_hops_zero_gives_only_shortest(self):
        routes = get_routes("Lone Tree Station", "Spire", max_extra_hops=0)
        shortest_len = routes[0]["steps"]
        self.assertTrue(all(r["steps"] == shortest_len for r in routes))

    def test_results_not_capped_in_get_routes(self):
        routes = get_routes("Lone Tree Station", "The Cypress Citadel", max_extra_hops=2)
        self.assertGreater(len(routes), 10)

    def test_all_paths_are_simple(self):
        """No location should appear twice in any route."""
        routes = get_routes("Lone Tree Station", "Spire")
        for route in routes:
            self.assertEqual(len(route["path"]), len(set(route["path"])),
                             f"Cycle detected in route: {route['path']}")


class GraphIntegrityTests(unittest.TestCase):
    """Verify the valley_map.json graph is well-formed."""

    def test_graph_is_symmetric(self):
        """Every edge A->B should have a matching B->A with same terrain."""
        from ebr.valley_map import _get_map
        graph = _get_map()
        for loc, info in graph.items():
            for edge in info["adj"]:
                dest = edge["to"]
                self.assertIn(dest, graph,
                    f"{loc} references unknown location {dest}")
                reverse = [e for e in graph[dest]["adj"] if e["to"] == loc]
                self.assertTrue(len(reverse) > 0,
                    f"{loc} -> {dest} has no reverse edge")
                self.assertEqual(reverse[0]["terrain"], edge["terrain"],
                    f"{loc} -> {dest} terrain mismatch: {edge['terrain']} vs {reverse[0]['terrain']}")

    def test_no_duplicate_edges(self):
        from ebr.valley_map import _get_map
        graph = _get_map()
        for loc, info in graph.items():
            dests = [e["to"] for e in info["adj"]]
            self.assertEqual(len(dests), len(set(dests)),
                f"{loc} has duplicate edges")

    def test_expected_location_count(self):
        from ebr.valley_map import _get_map
        graph = _get_map()
        self.assertEqual(len(graph), 37)


class FormatRoutesTests(unittest.TestCase):
    def test_format_uses_location_terrain_pairs(self):
        output = format_routes("Lone Tree Station", "Boulder Field")
        self.assertIn("Boulder Field (Woods)", output)

    def test_format_no_routes(self):
        output = format_routes("Marsh of Rebirth", "Spire")
        self.assertIn("No routes found", output)

    def test_format_same_location(self):
        output = format_routes("Spire", "Spire")
        self.assertIn("already at", output)

    def test_format_filters_river_routes_by_default(self):
        output = format_routes("Lone Tree Station", "Spire")
        self.assertNotIn("has River crossing", output)
        self.assertIn("additional route(s) available with River crossing", output)

    def test_format_shows_river_routes_when_allowed(self):
        output = format_routes("Lone Tree Station", "Spire", can_cross_river=True)
        self.assertIn("has River crossing", output)
        self.assertNotIn("additional route(s) available", output)

    def test_format_all_river_routes_filtered_shows_message(self):
        """White Sky -> Spire is only 1 step but it's River."""
        output = format_routes("White Sky", "Spire", max_extra_hops=0)
        self.assertIn("without River crossings", output)
        self.assertIn("available if you can cross rivers", output)

    def test_format_caps_at_max_routes(self):
        output = format_routes("Lone Tree Station", "The Cypress Citadel", can_cross_river=True)
        self.assertEqual(output.count("Route "), 10)

    def test_format_fills_10_after_river_filter(self):
        """Should show up to 10 non-river routes, not filter from a pre-capped 10."""
        output = format_routes("Lone Tree Station", "Tumbledown")
        route_count = output.count("Route ")
        self.assertGreater(route_count, 2)
        self.assertLessEqual(route_count, 10)


if __name__ == "__main__":
    unittest.main()
