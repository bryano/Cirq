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

"""QCircuit support for acquaintance module."""

from typing import Iterable, Optional

from cirq import ops, protocols
from cirq.contrib import qcircuit
from cirq.contrib.acquaintance.gates import (
        AcquaintanceOpportunityGate, SwapNetworkGate)
from cirq.contrib.acquaintance.executor import AcquaintanceOperation
from cirq.contrib.acquaintance.permutation import PermutationGate
from cirq.contrib.acquaintance.shift import CircularShiftGate


def acquaintance_qcircuit_diagram_info(
        op: ops.Operation,
        args: protocols.CircuitDiagramInfoArgs
        ) -> Optional[protocols.CircuitDiagramInfo]:
    if not (isinstance(op, AcquaintanceOperation) or
            (isinstance(op, ops.GateOperation) and
             isinstance(op.gate, AcquaintanceOpportunityGate))):
        return None
    multigate_parameters = qcircuit.get_multigate_parameters(args)
    if multigate_parameters is not None:
        min_index, n_qubits = multigate_parameters
        box = qcircuit.multigate_macro(n_qubits, '')
        ghost = qcircuit.ghost_macro('')
        assert args.qubit_map is not None
        assert args.known_qubits is not None
        symbols = tuple(box if (args.qubit_map[q] == min_index) else
                        ghost for q in args.known_qubits)
        return protocols.CircuitDiagramInfo(symbols, vconnected=False)
    n_qubits = max(args.known_qubit_count or 0, len(args.known_qubits or ()))
    return protocols.CircuitDiagramInfo((r'\gate{}',) * n_qubits)

GROUPING_LINE_THICKNESS = 5

def get_vertical_grouping_lines(
        part_lens: Iterable[int],
        dx: int = 0,
        thickness: int = 1):
    part_lens = tuple(part_lens)
    if part_lens == (1, 1):
        return ('', '')
    return (qcircuit.line_macro((dx, part_len - 1),
                                thickness=thickness, start=(dx, 0))
            if not dl else ''
            for part_len in part_lens for dl in range(part_len))


def permutation_qcircuit_diagram_info(
        op: ops.Operation,
        args: protocols.CircuitDiagramInfoArgs
        ) -> Optional[protocols.CircuitDiagramInfo]:

    if not (isinstance(op, ops.GateOperation) and
            isinstance(op.gate, PermutationGate)):
        return None
    if args.qubit_map is None or args.known_qubits is None:
        return None

    multigate_parameters = qcircuit.get_multigate_parameters(args)

    if isinstance(op.gate, SwapNetworkGate):
        if multigate_parameters is None:
            return None
        _, n_qubits = multigate_parameters
        start_lines = get_vertical_grouping_lines(op.gate.part_lens,
                thickness=GROUPING_LINE_THICKNESS)
        end_lines = get_vertical_grouping_lines(reversed(op.gate.part_lens),
                thickness=GROUPING_LINE_THICKNESS, dx=1)
        join_lines = (
            '' if dl else
            ' '.join(qcircuit.line_macro((dx, n_qubits -1), start=(dx, 0),
                                         style='.', thickness=2)
                     for dx in (0, 1))
            for dl in range(n_qubits))
        wire_symbol_groups = [start_lines, end_lines, join_lines]
    elif isinstance(op.gate, CircularShiftGate):
        if multigate_parameters is None:
            return None
        _, n_qubits = multigate_parameters
        part_lens = (op.gate.shift, n_qubits - op.gate.shift)
        start_lines = get_vertical_grouping_lines(part_lens,
            thickness=GROUPING_LINE_THICKNESS)
        end_lines = get_vertical_grouping_lines(reversed(part_lens),
            thickness=GROUPING_LINE_THICKNESS, dx=1)
        wire_symbol_groups = [start_lines, end_lines]
    else:
        wire_symbol_groups = []

    permutation = op.gate.permutation(len(args.known_qubits))
    new_map = {q: args.qubit_map[args.known_qubits[permutation.get(i, i)]]
               for i, q in enumerate(args.known_qubits)}
    dys = (new_map[q] - args.qubit_map[q] for q in args.known_qubits)
    permutation_lines = (qcircuit.line_macro((1, dy)) for dy in dys)
    wire_symbol_groups.append(permutation_lines)

    wire_symbols = tuple(' '.join(lines) for lines in zip(*wire_symbol_groups))
    return protocols.CircuitDiagramInfo(
            wire_symbols=wire_symbols,
            hconnected=False,
            vconnected=False)


def get_qcircuit_diagram_info(
        op: ops.Operation,
        args: protocols.CircuitDiagramInfoArgs
        ) -> protocols.CircuitDiagramInfo:
    info = acquaintance_qcircuit_diagram_info(op, args)
    if info is None:
        info = acquaintance_qcircuit_diagram_info(op, args)
    if info is None:
        info = permutation_qcircuit_diagram_info(op, args)
    if info is None:
        info = qcircuit.get_qcircuit_diagram_info(op, args)
    return info


def permutation_followed_by_non_permutation(
        first_op: ops.Operation, second_op: Optional[ops.Operation]) -> bool:
    return (
        ((second_op is None) or 
         (set(first_op.qubits) & set(second_op.qubits))) and 
        isinstance(first_op, ops.GateOperation) and
        isinstance(first_op.gate, PermutationGate) and
        not (isinstance(second_op, ops.GateOperation) and 
             isinstance(second_op.gate, PermutationGate)))

PadAfterPermutationGates = qcircuit.PadBetweenOps(
        permutation_followed_by_non_permutation)

def contains_swap_network_gate(
        first_op: ops.Operation, second_op: Optional[ops.Operation]) -> bool:
    return ((second_op is not None) and
             any(isinstance(op, ops.GateOperation) and
                 isinstance(op.gate, SwapNetworkGate)
                 for op in (first_op, second_op)))

PadAroundSwapNetworkGates = qcircuit.PadBetweenOps(contains_swap_network_gate)

qcircuit_optimizers = ((PadAfterPermutationGates, PadAroundSwapNetworkGates) +
        qcircuit.default_optimizers)

default_qcircuit_kwargs = {
    'get_circuit_diagram_info': get_qcircuit_diagram_info,
    'optimizers': qcircuit_optimizers,
}
