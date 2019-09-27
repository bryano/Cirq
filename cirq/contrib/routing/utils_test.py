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

import cirq
import cirq.contrib.routing as ccr


def test_ops_are_consistent_with_device_graph():
    device_graph = ccr.get_linear_device_graph(3)
    qubits = cirq.LineQubit.range(3)
    circuit = cirq.Circuit(cirq.ZZ(qubits[0], qubits[2]))
    assert not ccr.ops_are_consistent_with_device_graph(
        circuit.all_operations(), device_graph)
    assert not ccr.ops_are_consistent_with_device_graph(
        [cirq.X(cirq.GridQubit(0, 0))], device_graph)


def test_is_valid_routing_on_unmapped_qubits():
    p, q, r = cirq.LineQubit.range(3)
    x, y = cirq.NamedQubit('x'), cirq.NamedQubit('y')
    circuit = cirq.Circuit([cirq.CNOT(x, y), cirq.CZ(x, y)])
    routed_circuit = cirq.Circuit([cirq.CNOT(p, q), cirq.CZ(q, r)])
    swap_network = ccr.SwapNetwork(routed_circuit, initial_mapping)
    assert not ccr.is_valid_routing(circuit, swap_network)
