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

import cirq
import cirq.contrib.qcircuit as ccq
import cirq.testing as ct


def assert_has_qcircuit_diagram(
        actual: cirq.Circuit,
        desired: str,
        **kwargs) -> None:
    """Determines if a given circuit has the desired qcircuit diagram.

    Args:
        actual: The circuit that was actually computed by some process.
        desired: The desired qcircuit diagram as a string. Newlines at the
            beginning and whitespace at the end are ignored.
        **kwargs: Keyword arguments to be passed to
            circuit_to_latex_using_qcircuit.
    """
    actual_diagram = ccq.circuit_to_latex_using_qcircuit(actual, **kwargs
            ).lstrip('\n').rstrip()
    desired_diagram = desired.lstrip("\n").rstrip()
    assert actual_diagram == desired_diagram, (
        "Circuit's qcircuit diagram differs from the desired diagram.\n"
        '\n'
        'Diagram of actual circuit:\n'
        '{}\n'
        '\n'
        'Desired qcircuit diagram:\n'
        '{}\n'
        '\n'
        'Highlighted differences:\n'
        '{}\n'.format(actual_diagram, desired_diagram,
                      ct.highlight_text_differences(actual_diagram,
                                                 desired_diagram))
    )


def test_fallback_diagram():
    class MagicGate(cirq.Gate):
        def __str__(self):
            return 'MagicGate'

    class MagicOp(cirq.Operation):
        def __init__(self, *qubits):
            self._qubits = qubits

        def with_qubits(self, *new_qubits):
            return MagicOp(*new_qubits)

        @property
        def qubits(self):
            return self._qubits

        def __str__(self):
            return 'MagicOperate'

    circuit = cirq.Circuit.from_ops(
        MagicOp(cirq.NamedQubit('b')),
        MagicGate().on(cirq.NamedQubit('b'),
                       cirq.NamedQubit('a'),
                       cirq.NamedQubit('c')))
    expected_diagram = r"""
\Qcircuit @R=1em @C=0.75em {
 \\
 &\lstick{\text{a}}& \qw&                                                                                                                       \qw&*+<.6em>{\text{\#2}} \POS ="i","i"+UR;"i"+UL **\dir{-};"i"+DL **\dir{-};"i"+DR **\dir{-};"i"+UR **\dir{-},"i"       \qw    & \qw\\
 &\lstick{\text{b}}& \qw&*+<.6em>{\text{MagicOperate}} \POS ="i","i"+UR;"i"+UL **\dir{-};"i"+DL **\dir{-};"i"+DR **\dir{-};"i"+UR **\dir{-},"i" \qw&*+<.6em>{\text{MagicGate}} \POS ="i","i"+UR;"i"+UL **\dir{-};"i"+DL **\dir{-};"i"+DR **\dir{-};"i"+UR **\dir{-},"i" \qw\qwx& \qw\\
 &\lstick{\text{c}}& \qw&                                                                                                                       \qw&*+<.6em>{\text{\#3}} \POS ="i","i"+UR;"i"+UL **\dir{-};"i"+DL **\dir{-};"i"+DR **\dir{-};"i"+UR **\dir{-},"i"       \qw\qwx& \qw\\
 \\
}""".strip()
    assert_has_qcircuit_diagram(circuit, expected_diagram)


def test_teleportation_diagram():
    ali = cirq.NamedQubit('alice')
    car = cirq.NamedQubit('carrier')
    bob = cirq.NamedQubit('bob')

    circuit = cirq.Circuit.from_ops(
        cirq.H(car),
        cirq.CNOT(car, bob),
        cirq.X(ali)**0.5,
        cirq.CNOT(ali, car),
        cirq.H(ali),
        [cirq.measure(ali), cirq.measure(car)],
        cirq.CNOT(car, bob),
        cirq.CZ(ali, bob))

    expected_diagram = r"""
\Qcircuit @R=1em @C=0.75em {
 \\
 &\lstick{\text{alice}}&   \qw&                                                                                                            \qw&*+<.6em>{\text{X}^{0.5}} \POS ="i","i"+UR;"i"+UL **\dir{-};"i"+DL **\dir{-};"i"+DR **\dir{-};"i"+UR **\dir{-},"i" \qw    &\control \qw    &*+<.6em>{\text{H}} \POS ="i","i"+UR;"i"+UL **\dir{-};"i"+DL **\dir{-};"i"+DR **\dir{-};"i"+UR **\dir{-},"i" \qw&\meter \qw&         \qw    &\control \qw    & \qw\\
 &\lstick{\text{carrier}}& \qw&*+<.6em>{\text{H}} \POS ="i","i"+UR;"i"+UL **\dir{-};"i"+DL **\dir{-};"i"+DR **\dir{-};"i"+UR **\dir{-},"i" \qw&\control                                                                                                          \qw    &\targ    \qw\qwx&                                                                                                            \qw&\meter \qw&\control \qw    &         \qw\qwx& \qw\\
 &\lstick{\text{bob}}&     \qw&                                                                                                            \qw&\targ                                                                                                             \qw\qwx&         \qw    &                                                                                                            \qw&       \qw&\targ    \qw\qwx&\control \qw\qwx& \qw\\
 \\
}""".strip()
    assert_has_qcircuit_diagram(circuit, expected_diagram,
            qubit_order=cirq.QubitOrder.explicit([ali, car, bob]))


def test_other_diagram():
    a, b, c = cirq.LineQubit.range(3)

    circuit = cirq.Circuit.from_ops(
        cirq.X(a),
        cirq.Y(b),
        cirq.Z(c))

    expected_diagram = r"""
\Qcircuit @R=1em @C=0.75em {
 \\
 &\lstick{\text{0}}& \qw&\targ                                                                                                       \qw& \qw\\
 &\lstick{\text{1}}& \qw&*+<.6em>{\text{Y}} \POS ="i","i"+UR;"i"+UL **\dir{-};"i"+DL **\dir{-};"i"+DR **\dir{-};"i"+UR **\dir{-},"i" \qw& \qw\\
 &\lstick{\text{2}}& \qw&*+<.6em>{\text{Z}} \POS ="i","i"+UR;"i"+UL **\dir{-};"i"+DL **\dir{-};"i"+DR **\dir{-};"i"+UR **\dir{-},"i" \qw& \qw\\
 \\
}""".strip()
    assert_has_qcircuit_diagram(circuit, expected_diagram)

def test_swap_diagram():
    a, b, c = cirq.LineQubit.range(3)
    circuit = cirq.Circuit.from_ops((cirq.SWAP(a, b), cirq.SWAP(b, c)))
    expected_diagram = r"""
\Qcircuit @R=1em @C=0.75em {
 \\
 &\lstick{\text{0}}& \qw&\ar @{-} [1, 1]  \qw&                    & \qw& \qw\\
 &\lstick{\text{1}}& \qw&\ar @{-} [-1, 1] \qw&\ar @{-} [1, 1]     &    & \qw\\
 &\lstick{\text{2}}& \qw&                 \qw&\ar @{-} [-1, 1] \qw&    & \qw\\
 \\
}""".strip()
    assert_has_qcircuit_diagram(circuit, expected_diagram)

    a, b, c = cirq.LineQubit.range(3)
    circuit = cirq.Circuit.from_ops((cirq.SWAP(a, b), cirq.XX(b, c)))
    expected_diagram = r"""
\Qcircuit @R=1em @C=0.75em {
 \\
 &\lstick{\text{0}}& \qw&\ar @{-} [1, 1]  \qw&    &                         \qw& \qw\\
 &\lstick{\text{1}}& \qw&\ar @{-} [-1, 1] \qw&    &\multigate{1}{\text{XX}} \qw& \qw\\
 &\lstick{\text{2}}& \qw&                 \qw& \qw&\ghost{\text{XX}}        \qw& \qw\\
 \\
}""".strip()
    assert_has_qcircuit_diagram(circuit, expected_diagram)

    a, b, c = cirq.LineQubit.range(3)
    circuit = cirq.Circuit(
            [cirq.Moment([cirq.SWAP(a, b)]), cirq.Moment([cirq.X(c)])])
    expected_diagram = r"""
\Qcircuit @R=1em @C=0.75em {
 \\
 &\lstick{\text{0}}& \qw&\ar @{-} [1, 1]  \qw&         & \qw\\
 &\lstick{\text{1}}& \qw&\ar @{-} [-1, 1] \qw&         & \qw\\
 &\lstick{\text{2}}& \qw&                 \qw&\targ \qw& \qw\\
 \\
}""".strip()
    assert_has_qcircuit_diagram(circuit, expected_diagram)
