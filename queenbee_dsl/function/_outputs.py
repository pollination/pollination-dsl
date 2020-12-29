from typing import Dict
from dataclasses import dataclass
from queenbee.io.outputs.function import (
    FunctionStringOutput, FunctionIntegerOutput, FunctionNumberOutput,
    FunctionBooleanOutput, FunctionFolderOutput, FunctionFileOutput,
    FunctionPathOutput, FunctionJSONObjectOutput
)
from queenbee.base.basemodel import BaseModel
from queenbee.base.parser import parse_double_quotes_vars

from pydantic import validator


__all__ = ('Outputs', )

_outputs_mapper = {
    'StringOutput': FunctionStringOutput,
    'IntegerOutput': FunctionIntegerOutput,
    'NumberOutput': FunctionNumberOutput,
    'BooleanOutput': FunctionBooleanOutput,
    'FolderOutput': FunctionFolderOutput,
    'FileOutput': FunctionFileOutput,
    'PathOutput': FunctionPathOutput,
    'DictOutput': FunctionJSONObjectOutput
}


class _OutputBase(BaseModel):

    @property
    def __decorator__(self) -> str:
        """Queenbee decorator for outputs."""
        return 'output'

    def to_queenbee(self, name):
        """Convert this output to a Queenbee output."""
        func = _outputs_mapper[self.__class__.__name__]
        data = {
            'name': name.replace('_', '-'),
            'path': self.path,
            'description': self.description,
            'annotations': self.annotations
        }
        return func.parse_obj(data)

    @property
    def is_artifact(self):
        return False

    @property
    def reference_type(self):
        return 'TaskReference'


class StringOutput(_OutputBase):
    path: str
    annotations: Dict = None
    description: str = None

    @validator('path')
    def change_self_to_inputs(cls, v):
        refs = parse_double_quotes_vars(v)
        for ref in refs:
            v = v.replace(
                ref, ref.replace('self.', 'inputs.').replace('_', '-')
            )
        return v


class IntegerOutput(StringOutput):
    ...


class NumberOutput(StringOutput):
    ...


class BooleanOutput(StringOutput):
    ...


class DictOutput(StringOutput):
    ...


class FolderOutput(StringOutput):

    @property
    def is_artifact(self):
        return True

    @property
    def reference_type(self):
        return 'TaskFolderReference'


class FileOutput(FolderOutput):
    @property
    def reference_type(self):
        return 'TaskFileReference'


class PathOutput(FolderOutput):
    @property
    def reference_type(self):
        return 'TaskPathReference'


@dataclass
class Outputs:
    """Function outputs."""
    str = StringOutput
    int = IntegerOutput
    float = NumberOutput
    bool = BooleanOutput
    file = FileOutput
    folder = FolderOutput
    path = PathOutput
    dict = DictOutput
