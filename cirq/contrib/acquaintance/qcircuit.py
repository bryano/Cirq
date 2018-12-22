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

import itertools

from typing import cast, FrozenSet, Iterable, Optional, Tuple

from cirq import circuits, ops, protocols
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
        thickness: int = 1,
        upward: bool = True):
    part_lens = tuple(part_lens)
    if part_lens == (1, 1):
        return ('', '')
    dy = 1 if upward else -1
    return (qcircuit.line_macro((dx, dy* (part_len - 1)),
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


    if isinstance(op.gate, SwapNetworkGate):
        multigate_parameters = qcircuit.get_multigate_parameters(args, True)
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
        for s in (-1, 1):
            qubits = args.known_qubits and tuple(args.known_qubits[::s])
            parameters = qcircuit.get_multigate_parameters(
                    args.with_args(known_qubits=qubits), True)
            if parameters is not None:
                break
        else:
            return None
        _, n_qubits = parameters
        part_lens = (op.gate.shift, n_qubits - op.gate.shift)
        start_lines = get_vertical_grouping_lines(part_lens,
            thickness=GROUPING_LINE_THICKNESS, upward=(s > 0))
        end_lines = get_vertical_grouping_lines(reversed(part_lens),
            thickness=GROUPING_LINE_THICKNESS, dx=1, upward=(s > 0))
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

def swap_qcircuit_diagram_info(
        op: ops.Operation,
        args: protocols.CircuitDiagramInfoArgs
        ) -> Optional[protocols.CircuitDiagramInfo]:
    if not (isinstance(op, ops.GateOperation) and
            op.gate == ops.SWAP):
        return None
    return protocols.CircuitDiagramInfo(
            wire_symbols = ('{\\times}',) * 2,
            vconnected = True,
            hconnected = True)


def get_qcircuit_diagram_info(
        op: ops.Operation,
        args: protocols.CircuitDiagramInfoArgs
        ) -> protocols.CircuitDiagramInfo:
    info = acquaintance_qcircuit_diagram_info(op, args)
    if info is None:
        info = swap_qcircuit_diagram_info(op, args)
    if info is None:
        info = permutation_qcircuit_diagram_info(op, args)
    if info is None:
        info = qcircuit.get_qcircuit_diagram_info(op, args)
    return info


def qubit_grouping(
        op: ops.GateOperation,
        reverse: bool=False
        ) -> Optional[Tuple[FrozenSet[ops.QubitId], ...]]:
    if isinstance(op.gate, SwapNetworkGate):
        i = 0
        groups = []
        part_lens = (reversed(op.gate.part_lens)
                if reverse else op.gate.part_lens)
        for part_len in part_lens:
            groups.append(frozenset(op.qubits[i: i + part_len]))
            i += part_len
        return tuple(groups)
    if isinstance(op.gate, CircularShiftGate):
        threshold = ((len(op.qubits) - op.gate.shift)
                if reverse else op.gate.shift)
        return (frozenset(op.qubits[:threshold]),
                frozenset(op.qubits[threshold:]))
    return None


def padding_needed_after_permutation(
        first_op: ops.Operation, second_op: Optional[ops.Operation]) -> int:
    if not (isinstance(first_op, ops.GateOperation) and
            isinstance(first_op.gate, PermutationGate)):
        return 0
    if second_op is None:
        return 2
    if not (set(first_op.qubits) & set(second_op.qubits)):
        return 0
    if (isinstance(second_op, ops.GateOperation) and
        isinstance(second_op.gate, PermutationGate)):
        first_grouping = qubit_grouping(first_op, reverse=True)
        second_grouping = qubit_grouping(second_op)
        if (first_grouping is None) or (second_grouping is None):
            return 0
        if any((first_group & second_group) and (first_group ^ second_group)
                for first_group, second_group in
                itertools.product(first_grouping, second_grouping)):
            return 1
        return 0
    return 1

PadAfterPermutationGates = qcircuit.PadBetweenOps(
        padding_needed_after_permutation)

qcircuit_optimizers = (
        (cast(circuits.OptimizationPass, PadAfterPermutationGates),) +
        qcircuit.default_optimizers)

default_qcircuit_kwargs = {
    'get_circuit_diagram_info': get_qcircuit_diagram_info,
    'optimizers': qcircuit_optimizers,
}
