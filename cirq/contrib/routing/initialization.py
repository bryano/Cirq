# Copyright 2019 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools
import random
from typing import cast, Dict, Hashable, List, Set

import networkx as nx

from cirq import ops


def get_center(graph: nx.Graph) -> Hashable:
    centralities = nx.betweenness_centrality(graph)
    return max(centralities, key=centralities.get)


def get_initial_mapping(logical_graph: nx.Graph,
                        device_graph: nx.Graph) -> Dict[ops.Qid, ops.Qid]:
    """Gets an initial mapping of logical to physical qubits for routing.

    Args:
        logical_graph: The graph whose edges correspond to pairs of qubits that
            should be mapped to nearby physical qubits.
        device_graph: The graph of the device.
    """
    unplaced_vertices = set(logical_graph)

    frontier_graph = logical_graph.copy()
    frontier_center = cast(ops.Qid, get_center(frontier_graph))
    device_center = cast(ops.Qid, get_center(device_graph))
    mapping = {device_center: frontier_center}
    unplaced_vertices.remove(frontier_center)

    physical_distances = {
        (a, b): d
        for a, neighbor_distances in nx.shortest_path_length(device_graph)
        for b, d in neighbor_distances.items()
    }
    while len(unplaced_vertices):
        placed_vertices = set(mapping.values())
        placed_neighbors = {
            v: placed_vertices.intersection(frontier_graph[v])
            for v in unplaced_vertices
        }
        nums_placed_neighbors = {v: len(N) for v, N in placed_neighbors.items()}
        max_num_placed_neighbors = max(nums_placed_neighbors.values())
        candidates = [
            v for v, n in nums_placed_neighbors.items()
            if n == max_num_placed_neighbors
        ]

        border = cast(
            Set[ops.Qid],
            set().union(*(device_graph[v]
                          for v in mapping)).difference(mapping))
        total_distances = {}
        for l, p in itertools.product(candidates, border):
            total_distance = 0
            for pp in mapping:
                total_distance += physical_distances[p, pp]
            total_distances[l, p] = total_distance
        max_total_distance = max(total_distances.values())
        best_candidates = [
            lp for lp, d in total_distances.items() if d == max_total_distance
        ]
        l, p = random.choice(best_candidates)
        assert p not in mapping
        assert l not in mapping.values()
        mapping[p] = l
        unplaced_vertices.remove(l)
    return mapping