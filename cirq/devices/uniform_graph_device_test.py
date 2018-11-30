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

import cirq.devices as cd


def test_empty_uniform_undirected_linear_device():
    n_qubits = 4
    edge_labels = {}
    device = cd.uniform_undirected_linear_device(n_qubits, edge_labels)
    assert device.qubits == tuple()
    assert device.edges == tuple()


@pytest.mark.parametrize('arity', range(1, 5))
def test_regular_uniform_undirected_linear_device(arity):
    n_qubits = 10
    edge_labels = {arity: None}
    device = cd.uniform_undirected_linear_device(n_qubits, edge_labels)
    assert device.qubits == tuple(range(n_qubits))
    assert len(device.edges) == n_qubits - arity
    for edge, label in device.labelled_edges.items():
        assert label == UnconstrainedUndirectedGraphDeviceEdge
        assert len(edge) == arity