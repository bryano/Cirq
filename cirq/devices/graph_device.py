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

import abc
import itertools

from typing import (
        cast, FrozenSet, Hashable, Iterable, Optional, TYPE_CHECKING)

from cirq import ops, value
from cirq.devices.device import Device
from cirq.devices.hypergraph import UndirectedHypergraph

if TYPE_CHECKING:
    # pylint: disable=unused-import
    import cirq


class HashQubit(ops.QubitId):
    """A qubit identified by a hashable value."""

    def __init__(self, value: Hashable) -> None:
        if not isinstance(value, Hashable):
            raise TypeError('not isinstance({}, Hashable)'.format(value))
        self.value = value

    def _comparison_key(self):
        return self.value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return 'cirq.devices.HashQubit({})'.format(
                repr(self.value))


class UndirectedGraphDeviceEdge(metaclass=abc.ABCMeta):
    """An edge of an undirected graph device.
    """

    @abc.abstractmethod
    def duration_of(self, operation: ops.Operation) -> value.Duration:
        pass

    @abc.abstractmethod
    def validate_operation(self, operation: ops.Operation) -> None:
        pass


class FixedDurationUndirectedGraphDeviceEdge(UndirectedGraphDeviceEdge):
    """An edge of an undirected graph device on which every operation is
    allowed and has the same duration."""

    def __init__(self, duration: value.Duration):
        self._duration = duration

    def duration_of(self, operation: ops.Operation) -> value.Duration:
        return self._duration

    def validate_operation(self, operation: ops.Operation) -> None:
        pass

    def __eq__(self, other):
        return self._duration == other._duration


class _UnconstrainedUndirectedGraphDeviceEdge(UndirectedGraphDeviceEdge):
    """A device edge that allows everything."""

    def duration_of(self, operation: ops.Operation) -> value.Duration:
        return value.Duration(picos=0)

    def validate_operation(self, operation: ops.Operation) -> None:
        pass

    def __eq__(self, other):
        return self.__class__ == other.__class__


UnconstrainedUndirectedGraphDeviceEdge = (
        _UnconstrainedUndirectedGraphDeviceEdge())


def is_undirected_device_graph(graph: UndirectedHypergraph) -> bool:
    if not isinstance(graph, UndirectedHypergraph):
        return False
    for _, label in graph.labelled_edges.items():
        if not (label is None or isinstance(label, UndirectedGraphDeviceEdge)):
            return False
    return True

def is_crosstalk_graph(graph: UndirectedHypergraph) -> bool:
    if not isinstance(graph, UndirectedHypergraph):
        return False
    for vertex in graph.vertices:
        if not isinstance(vertex, frozenset):
            return False
    for edge, label in graph.labelled_edges.items():
        if len(edge) < 2:
            return False
        if not ((label is None) or callable(label)):
            return False
    return True


def raise_crosstalk_error(*ops: ops.Operation):
    raise ValueError('crosstalk on {}'.format(ops))


class UndirectedGraphDevice(Device):
    """A device whose properties are represented by an edge-labelled graph.

    Each (undirected) edge of the device graph is labelled by an
    UndirectedGraphDeviceEdge or None. None indicates that any operation is
    allowed and has zero duration.

    Each (undirected) edge of the constraint graph is labelled either by a
    function or None. The function takes as arguments operations on the
    adjacent device edges and raises an error if they are not simultaneously
    executable. If None, no such operations are allowed.

    Note that
        * the crosstalk graph is allowed to have vertices (i.e. device edges)
            that do not exist in the graph device.
        * duration_of does not check that operation is valid.
    """

    def __init__(self,
                 device_graph: Optional[UndirectedHypergraph]=None,
                 crosstalk_graph:
                     Optional[UndirectedHypergraph]=None
                 ) -> None:
        """

        Args:
            device_graph: An undirected hypergraph whose vertices correspond to
                qubits and whose edges determine allowable operations and their
                durations.
            crosstalk_graph: An undirected hypergraph whose vertices are edges
                of device_graph and whose edges give simultaneity constraints
                thereon.
        """

        if device_graph is None:
            device_graph = UndirectedHypergraph()
        if not is_undirected_device_graph(device_graph):
            raise TypeError('not is_undirected_device_graph(' +
                             str(device_graph) + ')')
        if crosstalk_graph is None:
            crosstalk_graph = UndirectedHypergraph()
        if not is_crosstalk_graph(crosstalk_graph):
            raise TypeError('not is_crosstalk_graph(' +
                             str(crosstalk_graph) + ')')

        self.device_graph = device_graph
        self.crosstalk_graph = crosstalk_graph

    @property
    def vertices(self):
        return sorted(self.device_graph.vertices)

    @property
    def qubits(self):
        return tuple(HashQubit(v) for v in self.vertices)

    @property
    def edges(self):
        return tuple(sorted(self.device_graph.edges))

    @property
    def labelled_edges(self):
        return self.device_graph.labelled_edges

    def get_vertices(self, operation: ops.Operation) -> FrozenSet[Hashable]:
        return frozenset(cast(HashQubit, qubit).value
                         for qubit in operation.qubits)

    def get_device_edge_from_op(self, operation: ops.Operation
                        ) -> UndirectedGraphDeviceEdge:
        return self.device_graph.labelled_edges[self.get_vertices(operation)]

    def duration_of(self, operation: ops.Operation) -> value.Duration:
        return self.get_device_edge_from_op(operation).duration_of(operation)

    def validate_operation(self, operation: ops.Operation) -> None:
        try:
            device_edge = self.get_device_edge_from_op(operation)
        except Exception as error:
            vertices = self.get_vertices(operation)
            if vertices not in self.device_graph.edges:
                error =  ValueError('{} not in device graph edges'.format(
                    vertices))
            raise error
        device_edge.validate_operation(operation)

    def validate_crosstalk(self,
                           operation: ops.Operation,
                           other_operations: Iterable[ops.Operation]
                           ) -> None:
        vertices = self.get_vertices(operation)
        adjacent_crosstalk_edges = frozenset(
                self.crosstalk_graph._adjacency_lists.get(vertices, ()))
        for crosstalk_edge in adjacent_crosstalk_edges:
            label = self.crosstalk_graph.labelled_edges[crosstalk_edge]
            validator = (raise_crosstalk_error(operation, *other_operations)
                         if (label is None) else label)
            for crosstalk_operations in itertools.combinations(
                    other_operations, len(crosstalk_edge) - 1):
                validator(operation, *crosstalk_operations)

    def validate_moment(self, moment: 'cirq.Moment'):
        super().validate_moment(moment)
        ops = moment.operations
        for i, op in enumerate(ops):
            other_ops = ops[:i] + ops[i + 1:]
            self.validate_crosstalk(op, other_ops)

    def validate_scheduled_operation(
            self,
            schedule: 'cirq.Schedule',
            scheduled_operation: 'cirq.ScheduledOperation'
            ) -> None:
        operation = scheduled_operation.operation
        self.validate_operation(operation)

        other_operations = (
                scheduled_operation.operation for scheduled_operation in
                schedule.operations_happening_at_same_time_as(
                    scheduled_operation))
        self.validate_crosstalk(operation, other_operations)

    def validate_schedule(self, schedule: 'cirq.Schedule') -> None:
        for scheduled_operation in schedule.scheduled_operations:
            self.validate_scheduled_operation(schedule, scheduled_operation)

    def __eq__(self, other):
        return ((self.device_graph == other.device_graph) and
                (self.crosstalk_graph == other.crosstalk_graph))

    def __iadd__(self, other):
        self.device_graph += other.device_graph
        self.crosstalk_graph += other.crosstalk_graph
        return self

    def __copy__(self):
        return self.__class__(device_graph=self.device_graph.__copy__(),
                              crosstalk_graph=self.crosstalk_graph.__copy__())

    def __add__(self, other):
        device_sum = self.__copy__()
        device_sum += other
        return device_sum
