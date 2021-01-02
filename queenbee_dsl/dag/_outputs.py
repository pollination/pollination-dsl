from typing import Any, Dict
from dataclasses import dataclass

from queenbee.io.outputs.dag import (
    DAGGenericOutput, DAGStringOutput, DAGIntegerOutput, DAGNumberOutput,
    DAGBooleanOutput, DAGFolderOutput, DAGFileOutput, DAGPathOutput,
    DAGJSONObjectOutput, DAGArrayOutput
)
from queenbee.base.basemodel import BaseModel
from queenbee.io.common import ItemType
from queenbee.base.parser import parse_double_quotes_vars

from pydantic import validator, Field


__all__ = ('Outputs', )

_outputs_mapper = {
    'GenericOutput': DAGGenericOutput,
    'StringOutput': DAGStringOutput,
    'IntegerOutput': DAGIntegerOutput,
    'NumberOutput': DAGNumberOutput,
    'BooleanOutput': DAGBooleanOutput,
    'FolderOutput': DAGFolderOutput,
    'FileOutput': DAGFileOutput,
    'PathOutput': DAGPathOutput,
    'DictOutput': DAGJSONObjectOutput,
    'ListOutput': DAGArrayOutput
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


class _OutputBase(BaseModel):

    @property
    def __decorator__(self) -> str:
        """Queenbee decorator for outputs."""
        return 'output'

    def to_queenbee(self, name):
        """Convert this output to a Queenbee DAG output."""
        func = _outputs_mapper[self.__class__.__name__]
        data = {
            'name': name.replace('_', '-'),
            'from': _get_from(self.source, self.reference_type),
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


class GenericOutput(_OutputBase):
    """ A DAG generic output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        source: Source for this output. A source is usually from one of the template
            outputs but it can also be declared as a relative path.

    """

    source: Any  # this field will be translated to from_
    annotations: Dict = None
    description: str = None

    @validator('source')
    def change_self_to_inputs(cls, v):
        refs = parse_double_quotes_vars(v)
        for ref in refs:
            v = v.replace(
                ref, ref.replace('self.', 'inputs.').replace('_', '-')
            )
        return v


class StringOutput(_OutputBase):
    """ A DAG string output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        source: Source for this output. A source is usually from one of the template
            outputs but it can also be declared as a relative path.

    """

    source: Any  # this field will be translated to from_
    annotations: Dict = None
    description: str = None

    @validator('source')
    def change_self_to_inputs(cls, v):
        refs = parse_double_quotes_vars(v)
        for ref in refs:
            v = v.replace(
                ref, ref.replace('self.', 'inputs.').replace('_', '-')
            )
        return v


class IntegerOutput(StringOutput):
    """ A DAG integer output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        source: Source for this output. A source is usually from one of the template
            outputs but it can also be declared as a relative path.

    """
    ...


class NumberOutput(StringOutput):
    """ A DAG number output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        source: Source for this output. A source is usually from one of the template
            outputs but it can also be declared as a relative path.

    """
    ...


class BooleanOutput(StringOutput):
    ...


class DictOutput(StringOutput):
    """ A DAG dictionary output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        source: Source for this output. A source is usually from one of the template
            outputs but it can also be declared as a relative path.

    """
    ...


class ListOutput(StringOutput):
    """ A DAG list output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        source: Source for this output. A source is usually from one of the template
            outputs but it can also be declared as a relative path.

    """
    items_type: ItemType = Field(
        ItemType.String,
        description='Type of items in this array. All the items in an array must be '
        'from the same type.'
    )


class FolderOutput(StringOutput):
    """ A DAG folder output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        source: Source for this output. A source is usually from one of the template
            outputs but it can also be declared as a relative path.

    """

    @property
    def is_artifact(self):
        return True

    @property
    def reference_type(self):
        return 'FolderReference'


class FileOutput(FolderOutput):
    """ A DAG file output.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        source: Source for this output. A source is usually from one of the template
            outputs but it can also be declared as a relative path.

    """

    @property
    def reference_type(self):
        return 'FileReference'


class PathOutput(FolderOutput):
    """ A DAG path output. A path can be a file or a folder.

    Args:
        annotations: An optional annotation dictionary.
        description: Input description.
        source: Source for this output. A source is usually from one of the template
            outputs but it can also be declared as a relative path.

    """
    ...


@dataclass
class Outputs:
    """DAG outputs enumeration."""
    any = GenericOutput
    str = StringOutput
    int = IntegerOutput
    float = NumberOutput
    bool = BooleanOutput
    file = FileOutput
    folder = FolderOutput
    path = PathOutput
    dict = DictOutput
    list = ListOutput
