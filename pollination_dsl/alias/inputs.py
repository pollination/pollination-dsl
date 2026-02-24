from typing import Any, Dict, List, Union, Optional
from dataclasses import dataclass
from pydantic import field_validator
from queenbee.io.inputs.alias import DAGGenericInputAlias, DAGStringInputAlias, \
    DAGIntegerInputAlias, DAGNumberInputAlias, DAGBooleanInputAlias, \
    DAGJSONObjectInputAlias, DAGArrayInputAlias, DAGFileInputAlias, \
    DAGFolderInputAlias, DAGPathInputAlias, DAGLinkedInputAlias
from queenbee.base.basemodel import BaseModel, Field
from queenbee.io.common import ItemType, IOAliasHandler


__all__ = ('Inputs', )

_inputs_mapper = {
    'GenericInputAlias': DAGGenericInputAlias,
    'StringInputAlias': DAGStringInputAlias,
    'IntegerInputAlias': DAGIntegerInputAlias,
    'NumberInputAlias': DAGNumberInputAlias,
    'BooleanInputAlias': DAGBooleanInputAlias,
    'FolderInputAlias': DAGFolderInputAlias,
    'FileInputAlias': DAGFileInputAlias,
    'PathInputAlias': DAGPathInputAlias,
    'DictInputAlias': DAGJSONObjectInputAlias,
    'ListInputAlias': DAGArrayInputAlias,
    'LinkedInputAlias': DAGLinkedInputAlias
}


class _InputAliasBase(BaseModel):

    name: str = Field(...)
    annotations: Optional[Dict] = None
    description: Optional[str] = None
    default: Any = None
    spec: Optional[Dict] = None
    optional: bool = False
    platform: List[str] = Field(
        ...,
        description='Name of the client platform (e.g. Grasshopper, Revit, etc). The '
        'value can be any strings as long as it has been agreed between client-side '
        'developer and author of the recipe.'
    )

    handler: Optional[List[IOAliasHandler]] = Field(
        default=None,
        description='List of process actions to process the input or output value.',
        validate_default=True
    )

    @field_validator('handler', mode='before')
    @classmethod
    def create_empty_list(cls, v):
        return [] if v is None else v

    @property
    def required(self):
        if self.optional:
            return False
        elif self.default is not None:
            return False
        else:
            return True

    def to_queenbee(self):
        """Convert this input to a Queenbee input alias."""
        func = _inputs_mapper[self.__class__.__name__]
        data = {
            'required': self.required,
            'name': self.name,
            'default': self.default,
            'description': self.description,
            'annotations': self.annotations,
            'spec': self.spec,
            'platform': self.platform,
            'handler': [h.model_dump() for h in self.handler]
        }

        if hasattr(self, 'extensions'):
            data['extensions'] = self.extensions

        if hasattr(self, 'items_type'):
            data['items_type'] = self.items_type

        return func.model_validate(data)

    @property
    def is_artifact(self):
        return False


class GenericInputAlias(_InputAliasBase):
    """ A generic input alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


class StringInputAlias(GenericInputAlias):
    """ A string input alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    default: Optional[str] = None

    @field_validator('default', mode='before')
    @classmethod
    def coerce_default_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class LinkedInputAlias(StringInputAlias):
    """ A linked input alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


class IntegerInputAlias(StringInputAlias):
    """ A integer input alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    default: Optional[int] = None


class NumberInputAlias(StringInputAlias):
    """ A number input alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    default: Optional[float] = None


class BooleanInputAlias(StringInputAlias):
    """ A boolean input alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    default: Optional[bool] = None


class DictInputAlias(StringInputAlias):
    """ A dictionary input alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    default: Optional[Dict] = None


class ListInputAlias(StringInputAlias):
    """ A list input alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        items_type: Type of items in list. All the items in an array must be from
            the same type.
        spec: A JSONSchema specification to validate input values.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    default: Optional[List] = None

    items_type: ItemType = Field(
        default=ItemType.String,
        description='Type of items in an array. All the items in an array must be from '
        'the same type.'
    )


class FolderInputAlias(StringInputAlias):
    """ A folder input alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        spec: A JSONSchema specification to validate input values.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    @property
    def is_artifact(self):
        return True


class FileInputAlias(FolderInputAlias):
    """ A file input alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        extensions: An optional list of valid extensions for input file.
        spec: A JSONSchema specification to validate input values.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    extensions: Optional[List[str]] = None


class PathInputAlias(FileInputAlias):
    """ A path input alias. A path can be a file or a folder.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        default: Default value.
        extensions: An optional list of valid extensions for input file.
        spec: A JSONSchema specification to validate input values.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


@dataclass
class Inputs:
    """inputs alias enumeration."""
    any = GenericInputAlias
    str = StringInputAlias
    int = IntegerInputAlias
    float = NumberInputAlias
    bool = BooleanInputAlias
    file = FileInputAlias
    folder = FolderInputAlias
    path = PathInputAlias
    dict = DictInputAlias
    list = ListInputAlias
    linked = LinkedInputAlias


InputAliasTypes = Union[
    GenericInputAlias, StringInputAlias, IntegerInputAlias, NumberInputAlias,
    BooleanInputAlias, FileInputAlias, FolderInputAlias, PathInputAlias, DictInputAlias,
    ListInputAlias, LinkedInputAlias
]
