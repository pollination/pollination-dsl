from typing import Dict, List
from dataclasses import dataclass
from queenbee.io.inputs.dag import (
    DAGStringInput, DAGIntegerInput, DAGNumberInput,
    DAGBooleanInput, DAGFolderInput, DAGFileInput,
    DAGPathInput, DAGJSONObjectInput
)
from queenbee.base.basemodel import BaseModel

__all__ = ('Inputs', )

_inputs_mapper = {
    'StringInput': DAGStringInput,
    'IntegerInput': DAGIntegerInput,
    'NumberInput': DAGNumberInput,
    'BooleanInput': DAGBooleanInput,
    'FolderInput': DAGFolderInput,
    'FileInput': DAGFileInput,
    'PathInput': DAGPathInput,
    'DictInput': DAGJSONObjectInput
}


class _InputBase(BaseModel):

    @property
    def __decorator__(self) -> str:
        """Queenbee decorator for inputs."""
        return 'input'

    def to_queenbee(self, name):
        """Convert this input to a Queenbee input."""
        func = _inputs_mapper[self.__class__.__name__]
        data = {
            'required': True if self.default is None else False,
            'name': name.replace('_', '-'),
            'default': self.default,
            'description': self.description,
            'annotations': self.annotations,
            'spec': self.spec
        }

        if hasattr(self, 'extensions'):
            data['extensions'] = self.extensions

        return func.parse_obj(data)

    @property
    def is_artifact(self):
        return False


class StringInput(_InputBase):
    annotations: Dict = None
    description: str = None
    default: str = None
    spec: Dict = None


class IntegerInput(StringInput):
    default: int = None


class NumberInput(StringInput):
    default: float = None


class BooleanInput(StringInput):
    default: bool = None


class DictInput(StringInput):
    default: Dict = None


class FolderInput(StringInput):

    @property
    def is_artifact(self):
        return True


class FileInput(FolderInput):
    extensions: List[str] = None


class PathInput(FileInput):
    ...


@dataclass
class Inputs:
    """DAG inputs."""
    str = StringInput
    int = IntegerInput
    float = NumberInput
    bool = BooleanInput
    file = FileInput
    folder = FolderInput
    path = PathInput
    dict = DictInput
