"""Contrato base de uma operação de imagem.

Toda operação é uma classe que declara metadados (nome, categoria, resumo), o modelo
de parâmetros e quantas entradas aceita, além de implementar ``run``.

Operações de entrada única (``min_inputs <= 1`` e ``max_inputs == 1``) ganham fan-out
automático: ao receber N entradas, ``execute`` roda a operação uma vez por entrada e
agrega os artefatos num único resultado (metadados por entrada em ``meta["per_input"]``).
Operações de aridade fixa (``watermark``, 1/2) ou ilimitada (``batch-convert``) nunca
disparam o fan-out — o contrato ``min_inputs``/``max_inputs`` continua mandando.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import PurePosixPath
from typing import Any, ClassVar, Generic, TypeVar

from pngtoolkit.core.errors import ImageToolkitError, InvalidInputError
from pngtoolkit.core.io import Artifact, ImageInput, OperationResult
from pngtoolkit.core.params import OperationParams

P = TypeVar("P", bound=OperationParams)


def _dedupe(filename: str, seen: set[str]) -> str:
    """Garante nome único entre os artefatos agregados pelo fan-out."""
    candidate, path, n = filename, PurePosixPath(filename), 2
    while candidate in seen:
        candidate = str(path.with_name(f"{path.stem}-{n}{path.suffix}"))
        n += 1
    seen.add(candidate)
    return candidate


class ImageOperation(ABC, Generic[P]):
    """Unidade de trabalho do toolkit.

    Subclasses fixam o tipo de parâmetro via ``ImageOperation[MeuParams]`` e definem
    os atributos de classe abaixo.
    """

    name: ClassVar[str]
    category: ClassVar[str]
    summary: ClassVar[str]
    params_model: ClassVar[type[OperationParams]]
    min_inputs: ClassVar[int] = 1
    max_inputs: ClassVar[int | None] = 1
    fan_out: ClassVar[bool] = True

    def check_inputs(self, inputs: Sequence[ImageInput]) -> None:
        """Valida a quantidade de entradas."""
        count = len(inputs)
        if count < self.min_inputs:
            raise InvalidInputError(
                f"operação {self.name!r} exige ao menos {self.min_inputs} arquivo(s), "
                f"recebeu {count}"
            )
        if self.max_inputs is not None and count > self.max_inputs:
            raise InvalidInputError(
                f"operação {self.name!r} aceita no máximo {self.max_inputs} arquivo(s), "
                f"recebeu {count}"
            )

    @abstractmethod
    def run(self, inputs: Sequence[ImageInput], params: P) -> OperationResult:
        """Executa a operação e devolve o resultado."""

    def _wants_fan_out(self, inputs: Sequence[ImageInput]) -> bool:
        return (
            self.fan_out
            and self.min_inputs <= 1
            and self.max_inputs == 1
            and len(inputs) > 1
        )

    def _execute_fan_out(self, inputs: Sequence[ImageInput], params: P) -> OperationResult:
        artifacts: list[Artifact] = []
        per_input: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in inputs:
            self.check_inputs([item])
            try:
                result = self.run([item], params)
            except ImageToolkitError as exc:
                raise type(exc)(f"{item.name}: {exc}") from exc
            prefix = PurePosixPath(item.name).parent
            for artifact in result.artifacts:
                name = artifact.filename
                if prefix != PurePosixPath("."):
                    name = (prefix / name).as_posix()
                artifact.filename = _dedupe(name, seen)
                artifacts.append(artifact)
            per_input.append({"name": item.name, "meta": result.meta})
        return OperationResult(
            artifacts=artifacts,
            meta={"fan_out": True, "inputs": len(inputs), "per_input": per_input},
        )

    def execute(self, inputs: Sequence[ImageInput], params: P) -> OperationResult:
        """Valida as entradas e chama :meth:`run` (uma vez, ou por entrada em fan-out)."""
        if self._wants_fan_out(inputs):
            return self._execute_fan_out(inputs, params)
        self.check_inputs(inputs)
        return self.run(inputs, params)
