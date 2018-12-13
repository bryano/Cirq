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

from typing import Iterable, Optional

from cirq import circuits, devices, ops, value, schedules

from cirq.devices import hypergraph


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


class _UnconstrainedUndirectedGraphDeviceEdge(UndirectedGraphDeviceEdge):
    """A device edge that allows everything."""

    def duration_of(self, operation: ops.Operation) -> value.Duration:
        return value.Duration(picos=0)

    def validate_operation(self, operation: ops.Operation) -> None:
        pass


UnconstrainedUndirectedGraphDeviceEdge = (
        _UnconstrainedUndirectedGraphDeviceEdge())


def is_undirected_device_graph(graph: hypergraph.UndirectedHypergraph) -> bool:
    if not isinstance(graph, hypergraph.UndirectedHypergraph):
        return False
    if not all(isinstance(v, ops.QubitId) for v in graph.vertices):
        return False
    for _, label in graph.labelled_edges.items():
        if not (label is None or isinstance(label, UndirectedGraphDeviceEdge)):
            return False
    return True


def is_crosstalk_graph(graph: hypergraph.UndirectedHypergraph) -> bool:
    if not isinstance(graph, hypergraph.UndirectedHypergraph):
        return False
    for vertex in graph.vertices:
        if not isinstance(vertex, frozenset):
            return False
        if not all(isinstance(v, ops.QubitId) for v in vertex):
            return False
    for edge, label in graph.labelled_edges.items():
        if len(edge) < 2:
            return False
        if not ((label is None) or callable(label)):
            return False
    return True


def raise_crosstalk_error(*ops: ops.Operation):
    raise ValueError('crosstalk on {}'.format(ops))


class UndirectedGraphDevice(devices.Device):
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
                 device_graph: hypergraph.UndirectedHypergraph,
                 crosstalk_graph:
                     Optional[hypergraph.UndirectedHypergraph]=None
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

        if not is_undirected_device_graph(device_graph):
            raise TypeError('not is_undirected_device_graph(' +
                             str(device_graph) + ')')
        if crosstalk_graph is None:
            crosstalk_graph = hypergraph.UndirectedHypergraph()
        if not is_crosstalk_graph(crosstalk_graph):
            raise TypeError('not is_crosstalk_graph(' +
                             str(crosstalk_graph) + ')')

        self.device_graph = device_graph
        self.crosstalk_graph = crosstalk_graph

    @property
    def qubits(self):
        return sorted(self.device_graph.vertices)

    @property
    def edges(self):
        return sorted(self.device_graph.edges)

    def get_device_edge_from_op(self, operation: ops.Operation
                        ) -> UndirectedGraphDeviceEdge:
        return self.device_graph.labelled_edges[frozenset(operation.qubits)]

    def duration_of(self, operation: ops.Operation) -> value.Duration:
        return self.get_device_edge_from_op(operation).duration_of(operation)

    def validate_operation(self, operation: ops.Operation) -> None:
        try:
            device_edge = self.get_device_edge_from_op(operation)
        except Exception as error:
            if frozenset(operation.qubits) not in self.device_graph.edges:
                error =  ValueError('{} not in device graph edges'.format(
                    operation.qubits))
            raise error
        device_edge.validate_operation(operation)

    def validate_crosstalk(self,
                           operation: ops.Operation,
                           other_operations: Iterable[ops.Operation]
                           ) -> None:
        adjacent_crosstalk_edges = frozenset(
                self.crosstalk_graph._adjacency_lists.get(
                    frozenset(operation.qubits), ()))
        for crosstalk_edge in adjacent_crosstalk_edges:
            label = self.crosstalk_graph.labelled_edges[crosstalk_edge]
            validator = (raise_crosstalk_error(operation, *other_operations)
                         if (label is None) else label)
            for crosstalk_operations in itertools.combinations(
                    other_operations, len(crosstalk_edge) - 1):
                validator(operation, *crosstalk_operations)

    def validate_moment(self, moment: circuits.Moment):
        super().validate_moment(moment)
        ops = moment.operations
        for i, op in enumerate(ops):
            other_ops = ops[:i] + ops[i + 1:]
            self.validate_crosstalk(op, other_ops)

    def validate_scheduled_operation(
            self,
            schedule: schedules.Schedule,
            scheduled_operation: schedules.ScheduledOperation
            ) -> None:
        operation = scheduled_operation.operation
        self.validate_operation(operation)

        other_operations = (
                scheduled_operation.operation for scheduled_operation in
                schedule.operations_happening_at_same_time_as(
                    scheduled_operation))
        self.validate_crosstalk(operation, other_operations)

    def validate_schedule(self, schedule: schedules.Schedule) -> None:
        for scheduled_operation in schedule.scheduled_operations:
            self.validate_scheduled_operation(schedule, scheduled_operation)