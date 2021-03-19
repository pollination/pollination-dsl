from typing import Dict, List, Any
from dataclasses import dataclass
from pydantic.errors import TupleError
from queenbee.io.inputs.function import (
    FunctionStringInput, FunctionIntegerInput, FunctionNumberInput,
    FunctionBooleanInput, FunctionFolderInput, FunctionFileInput,
    FunctionPathInput, FunctionJSONObjectInput, FunctionArrayInput
)
from queenbee.base.basemodel import BaseModel, Field
from queenbee.io.common import ItemType

__all__ = ('Inputs', )

_inputs_mapper = {
    'StringInput': FunctionStringInput,
    'IntegerInput': FunctionIntegerInput,
    'NumberInput': FunctionNumberInput,
    'BooleanInput': FunctionBooleanInput,
    'FolderInput': FunctionFolderInput,
    'FileInput': FunctionFileInput,
    'PathInput': FunctionPathInput,
    'DictInput': FunctionJSONObjectInput,
    'ListInput': FunctionArrayInput
}


class _InputBase(BaseModel):

    annotations: Dict = None
    description: Any = None
    default: str = None
    spec: Dict = None
    optional: bool = False

    @property
    def __decorator__(self) -> str:
        """Queenbee decorator for inputs."""
        return 'input'

    @property
    def required(self):
        if self.optional:
            return False
        elif self.default is not None:
            return False
        else:
            return True

    def to_queenbee(self, name):
        """Convert this input to a Queenbee input."""
        func = _inputs_mapper[self.__class__.__name__]
        data = {
            'required': self.required,
            'name': name.replace('_', '-'),
            'default': self.default,
            'description': self.description,
            'annotations': self.annotations,
            'spec': self.spec
        }

        if hasattr(self, 'path'):
            data['path'] = self.path

        if hasattr(self, 'extensions'):
            data['extensions'] = self.extensions

        return func.parse_obj(data)


class StringInput(_InputBase):
    """ A Function string input.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.

    """
    default: str = None


class IntegerInput(StringInput):
    """ A Function integer input.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.

    """
    default: int = None


class NumberInput(StringInput):
    """ A Function number input.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.

    """
    default: float = None


class BooleanInput(StringInput):
    """ A Function boolean input.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.

    """
    default: bool = None


class DictInput(StringInput):
    """ A Function dictionary input.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.

    """
    default: Dict = None


class ListInput(StringInput):
    """ A Function list input.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        items_type: 'Type of items in list. All the items in an array must be from '
        'the same type.'
        spec: A JSONSchema specification to validate input values.

    """
    default: List = None

    items_type: ItemType = Field(
        ItemType.String,
        description='Type of items in an array. All the items in an array must be from '
        'the same type.'
    )


class FolderInput(StringInput):
    """ A Function folder input.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        path: Path to source folder.
        spec: A JSONSchema specification to validate input values.

    """
    path: str


class FileInput(FolderInput):
    """ A Function file input.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        extensions: An optional list of valid extensions for input file.
        path: Path to source folder.
        spec: A JSONSchema specification to validate input values.

    """
    extensions: List[str] = None


class PathInput(FileInput):
    """ A Function file input.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        extensions: An optional list of valid extensions for input file.
        path: Path to source folder.
        spec: A JSONSchema specification to validate input values.

    """
    ...


@dataclass
class Inputs:
    """Function inputs enumeration."""
    str = StringInput
    int = IntegerInput
    float = NumberInput
    bool = BooleanInput
    file = FileInput
    folder = FolderInput
    path = PathInput
    dict = DictInput
    list = ListInput
