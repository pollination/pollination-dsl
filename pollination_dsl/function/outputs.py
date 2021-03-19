from typing import Dict, Any
from dataclasses import dataclass
from queenbee.io.outputs.function import (
    FunctionStringOutput, FunctionIntegerOutput, FunctionNumberOutput,
    FunctionBooleanOutput, FunctionFolderOutput, FunctionFileOutput,
    FunctionPathOutput, FunctionJSONObjectOutput, FunctionArrayOutput
)
from queenbee.io.common import ItemType
from queenbee.base.basemodel import BaseModel
from queenbee.base.parser import parse_double_quotes_vars

from pydantic import validator, Field


__all__ = ('Outputs', )

_outputs_mapper = {
    'StringOutput': FunctionStringOutput,
    'IntegerOutput': FunctionIntegerOutput,
    'NumberOutput': FunctionNumberOutput,
    'BooleanOutput': FunctionBooleanOutput,
    'FolderOutput': FunctionFolderOutput,
    'FileOutput': FunctionFileOutput,
    'PathOutput': FunctionPathOutput,
    'DictOutput': FunctionJSONObjectOutput,
    'ListOutput': FunctionArrayOutput
}


class _OutputBase(BaseModel):

    path: str
    annotations: Dict = None
    description: str = None
    optional: bool = False

    @validator('path')
    def change_self_to_inputs(cls, v):
        refs = parse_double_quotes_vars(v)
        for ref in refs:
            v = v.replace(
                ref, ref.replace('self.', 'inputs.').replace('_', '-')
            )
        return v

    @property
    def __decorator__(self) -> str:
        """Queenbee decorator for outputs."""
        return 'output'

    @property
    def required(self):
        if self.optional:
            return False
        else:
            return True

    def to_queenbee(self, name):
        """Convert this output to a Queenbee output."""
        func = _outputs_mapper[self.__class__.__name__]
        data = {
            'name': name.replace('_', '-'),
            'required': self.required,
            'path': self.path,
            'description': self.description,
            'annotations': self.annotations
        }

        if hasattr(self, 'items_type'):
            data['items_type'] = self.items_type

        return func.parse_obj(data)

    @property
    def is_artifact(self):
        return False

    @property
    def reference_type(self):
        return 'TaskReference'


class StringOutput(_OutputBase):
    """ A Function string output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        path: Path to the source file for this output.

    """
    ...


class IntegerOutput(StringOutput):
    """ A Function integer output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        path: Path to the source file for this output.

    """
    ...


class NumberOutput(StringOutput):
    """ A Function number output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        path: Path to the source file for this output.

    """
    ...


class BooleanOutput(StringOutput):
    """ A Function boolean output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        path: Path to the source file for this output.

    """
    ...


class DictOutput(StringOutput):
    """ A Function dictionary output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        path: Path to the source file for this output.

    """
    ...


class ListOutput(StringOutput):
    """ A Function list output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        path: Path to the source file for this output.

    """
    items_type: ItemType = Field(
        ItemType.String,
        description='Type of items in this array. All the items in an array must be '
        'from the same type.'
    )


class FolderOutput(StringOutput):
    """ A Function folder output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        path: Path to the source folder for this output.

    """
    @property
    def is_artifact(self):
        return True

    @property
    def reference_type(self):
        return 'TaskFolderReference'


class FileOutput(FolderOutput):
    """ A Function file output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        path: Path to the source file for this output.

    """
    @property
    def reference_type(self):
        return 'TaskFileReference'


class PathOutput(FolderOutput):
    """ A Function path output. A path can be a file or a folder.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        path: Path to the source file or folder for this output.

    """
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
    list = ListOutput
