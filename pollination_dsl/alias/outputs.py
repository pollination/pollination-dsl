from typing import Dict, List, Union
from dataclasses import dataclass

# Add alias to everything
from queenbee.io.outputs.alias import (
    DAGGenericOutputAlias, DAGStringOutputAlias, DAGIntegerOutputAlias,
    DAGNumberOutputAlias, DAGBooleanOutputAlias, DAGFolderOutputAlias,
    DAGFileOutputAlias, DAGPathOutputAlias, DAGJSONObjectOutputAlias,
    DAGArrayOutputAlias, DAGLinkedOutputAlias
)
from queenbee.base.basemodel import BaseModel
from queenbee.io.common import ItemType, IOAliasHandler

from pydantic import Field


__all__ = ('Outputs', )

_outputs_mapper = {
    'GenericOutputAlias': DAGGenericOutputAlias,
    'StringOutputAlias': DAGStringOutputAlias,
    'IntegerOutputAlias': DAGIntegerOutputAlias,
    'NumberOutputAlias': DAGNumberOutputAlias,
    'BooleanOutputAlias': DAGBooleanOutputAlias,
    'FolderOutputAlias': DAGFolderOutputAlias,
    'FileOutputAlias': DAGFileOutputAlias,
    'PathOutputAlias': DAGPathOutputAlias,
    'DictOutputAlias': DAGJSONObjectOutputAlias,
    'ListOutputAlias': DAGArrayOutputAlias,
    'LinkedOutputAlias': DAGLinkedOutputAlias
}


def _get_from(value, reference):
    try:
        # only TaskReference has parent
        parent = value['parent']
    except TypeError:
        # value
        return {'type': reference, 'path': value}
    else:
        # Task reference values and names are nested
        variable = value['name']
        value = value['value']
        return {'type': reference, 'name': parent, 'variable': variable}


class _OutputAliasBase(BaseModel):
    name: str = Field(...)
    annotations: Dict = None
    description: str = None
    platform: List[str] = Field(
        ...,
        description='Name of the client platform (e.g. Grasshopper, Revit, etc). The '
        'value can be any strings as long as it has been agreed between client-side '
        'developer and author of the recipe.'
    )
    handler: List[IOAliasHandler] = Field(
        ...,
        description='List of process actions to process the input or output value.'
    )

    def to_queenbee(self):
        """Convert this output to a Queenbee DAG output."""
        func = _outputs_mapper[self.__class__.__name__]
        data = {
            'name': self.name,
            'description': self.description,
            'annotations': self.annotations,
            'platform': self.platform,
            'handler': [h.dict() for h in self.handler]
        }

        if hasattr(self, 'items_type'):
            data['items_type'] = self.items_type

        return func.parse_obj(data)

    @property
    def is_artifact(self):
        return False


class GenericOutputAlias(_OutputAliasBase):
    """ A DAG generic output alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


class LinkedOutputAlias(GenericOutputAlias):
    """ A DAG linked output alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


class StringOutputAlias(GenericOutputAlias):
    """ A DAG string output alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


class IntegerOutputAlias(StringOutputAlias):
    """ A DAG integer output alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


class NumberOutputAlias(StringOutputAlias):
    """ A DAG number output alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


class BooleanOutputAlias(StringOutputAlias):
    """ A DAG boolean output alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


class DictOutputAlias(StringOutputAlias):
    """ A DAG dictionary output alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


class ListOutputAlias(StringOutputAlias):
    """ A DAG list output alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    items_type: ItemType = Field(
        ItemType.String,
        description='Type of items in this array. All the items in an array must be '
        'from the same type.'
    )


class FolderOutputAlias(StringOutputAlias):
    """ A DAG folder output alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """

    @property
    def is_artifact(self):
        return True


class FileOutputAlias(FolderOutputAlias):
    """ A DAG file output alias.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


class PathOutputAlias(FolderOutputAlias):
    """ A DAG path output alias. A path can be a file or a folder.

    Args:
        name: Alias input name.
        annotations: An optional annotation dictionary.
        description: Input description.
        platform: A list of names for the client platform (e.g. Grasshopper, Revit, etc).
            The value can be any strings as long as it has been agreed between
            client-side developer and author of the recipe.
        handler: List of process actions to process the input or output value.

    """
    ...


@dataclass
class Outputs:
    """DAG outputs enumeration."""
    any = GenericOutputAlias
    str = StringOutputAlias
    int = IntegerOutputAlias
    float = NumberOutputAlias
    bool = BooleanOutputAlias
    file = FileOutputAlias
    folder = FolderOutputAlias
    path = PathOutputAlias
    dict = DictOutputAlias
    list = ListOutputAlias
    link = LinkedOutputAlias


OutputAliasTypes = Union[
    GenericOutputAlias, StringOutputAlias, IntegerOutputAlias, NumberOutputAlias,
    BooleanOutputAlias, FileOutputAlias, FolderOutputAlias, PathOutputAlias,
    DictOutputAlias, ListOutputAlias, LinkedOutputAlias
]
