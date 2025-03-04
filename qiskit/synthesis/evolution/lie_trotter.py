# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""The Lie-Trotter product formula."""

from typing import List, Callable, Optional, Union
import numpy as np
from qiskit.circuit.parameterexpression import ParameterExpression
from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit.quantum_info.operators import SparsePauliOp, Pauli

from .product_formula import ProductFormula


class LieTrotter(ProductFormula):
    r"""The Lie-Trotter product formula.

    The Lie-Trotter formula approximates the exponential of two non-commuting operators
    with products of their exponentials up to a first order error:

    .. math::

        e^{A + B} \approx e^{A}e^{B}.

    In this implementation, the operators are provided as sum terms of a Pauli operator.
    For example, we approximate

    .. math::

        e^{-it(XX + ZZ)} = e^{-it XX}e^{-it ZZ} + \mathcal{O}(t).

    References:

        [1]: D. Berry, G. Ahokas, R. Cleve and B. Sanders,
        "Efficient quantum algorithms for simulating sparse Hamiltonians" (2006).
        `arXiv:quant-ph/0508139 <https://arxiv.org/abs/quant-ph/0508139>`_
    """

    def __init__(
        self,
        reps: int = 1,
        insert_barriers: bool = False,
        cx_structure: str = "chain",
        atomic_evolution: Optional[
            Callable[[Union[Pauli, SparsePauliOp], float], QuantumCircuit]
        ] = None,
    ) -> None:
        """
        reps: The number of time steps.
        insert_barriers: Whether to insert barriers between the atomic evolutions.
        cx_structure: How to arrange the CX gates for the Pauli evolutions, can be
            "chain", where next neighbor connections are used, or "fountain", where all
            qubits are connected to one.
        atomic_evolution: A function to construct the circuit for the evolution of single
            Pauli string. Per default, a single Pauli evolution is decomopsed in a CX chain
            and a single qubit Z rotation.
        """
        super().__init__(1, reps, insert_barriers, cx_structure, atomic_evolution)

    def synthesize(self, evolution):
        # get operators and time to evolve
        operators = evolution.operator
        time = evolution.time

        # construct the evolution circuit
        evo = QuantumCircuit(operators[0].num_qubits)
        first_barrier = False

        if not isinstance(operators, list):
            pauli_list = [(Pauli(op), np.real(coeff)) for op, coeff in operators.to_list()]
        else:
            pauli_list = [(op, 1) for op in operators]

        # if we only evolve a single Pauli we don't need to additionally wrap it
        wrap = not (len(pauli_list) == 1 and self.reps == 1)

        for _ in range(self.reps):
            for op, coeff in pauli_list:
                # add barriers
                if first_barrier:
                    if self.insert_barriers:
                        evo.barrier()
                else:
                    first_barrier = True

                evo.compose(
                    self.atomic_evolution(op, coeff * time / self.reps), wrap=wrap, inplace=True
                )

        return evo
