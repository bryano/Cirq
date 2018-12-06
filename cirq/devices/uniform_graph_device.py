# Copyright 2018 The Cirq Developers
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

from typing import Hashable, Iterable, Mapping, Optional, TYPE_CHECKING

from cirq import devices, line, ops

if TYPE_CHECKING:
    # pylint: disable=unused-import
    from typing import Any, Dict


def uniform_undirected_graph_device(
        edges: Iterable[Iterable[ops.QubitId]],
        edge_label: Optional[devices.UndirectedGraphDeviceEdge]=None
        ) -> devices.UndirectedGraphDevice:
    """An undirected graph device all of whose edges are the same.

    Args:
        edges: The edges.
        edge_label: The label to apply to all edges. Defaults to None.
    """

    labelled_edges = {frozenset(edge): edge_label for edge in edges
            } # type: Dict[Iterable[Hashable], Any]
    device_graph = devices.UndirectedHypergraph(labelled_edges=labelled_edges)
    return devices.UndirectedGraphDevice(device_graph=device_graph)


def uniform_undirected_linear_device(
        n_qubits: int,
        edge_labels: Mapping[int,
                             Optional[devices.UndirectedGraphDeviceEdge]]
        ) -> devices.UndirectedGraphDevice:
    """A uniform , undirected graph device whose qubits are arranged
    on a line.

    Uniformity refers to the fact that all edges of the same size have the same
    label.

    Args:
        n_qubits: The number of qubits.
        edge_labels: The labels to apply to all edges of a given size.

    Raises:
        ValueError: keys to edge_labels are not all at least 1.
    """

    if edge_labels and (min(edge_labels) < 1):
        raise ValueError('edge sizes {} must be at least 1.'.format(
            tuple(edge_labels.keys())))

    device = devices.UndirectedGraphDevice(devices.UndirectedHypergraph())
    for arity, label in edge_labels.items():
        edges = (line.LineQubit.range(i, i + arity)
                 for i in range(n_qubits - arity + 1))
        device += uniform_undirected_graph_device(edges, label)
    return device
