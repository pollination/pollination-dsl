from typing import Dict
from dataclasses import dataclass
from queenbee.io.inputs.function import (
    FunctionStringInput, FunctionIntegerInput, FunctionNumberInput,
    FunctionBooleanInput, FunctionFolderInput, FunctionFileInput,
    FunctionPathInput, FunctionJSONObjectInput
)
from queenbee.base.basemodel import BaseModel

__all__ = ('Inputs', )

_inputs_mapper = {
    'StringInput': FunctionStringInput,
    'IntegerInput': FunctionIntegerInput,
    'NumberInput': FunctionNumberInput,
    'BooleanInput': FunctionBooleanInput,
    'FolderInput': FunctionFolderInput,
    'FileInput': FunctionFileInput,
    'PathInput': FunctionPathInput,
    'DictInput': FunctionJSONObjectInput
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

        if hasattr(self, 'path'):
            data['path'] = self.path

        return func.parse_obj(data)


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
    path: str


class FileInput(FolderInput):
    ...


class PathInput(FolderInput):
    ...


@dataclass
class Inputs:
    """Function inputs."""
    str = StringInput
    int = IntegerInput
    float = NumberInput
    bool = BooleanInput
    file = FileInput
    folder = FolderInput
    path = PathInput
    dict = DictInput
