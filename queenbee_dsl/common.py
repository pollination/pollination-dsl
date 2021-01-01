from dataclasses import dataclass
from typing import NamedTuple
import importlib
from collections import namedtuple


def camel_to_snake(name: str) -> str:
    """Change name from CamelCase to snake-case."""
    return name[0].lower() + \
        ''.join(['-' + x.lower() if x.isupper() else x for x in name][1:])


@dataclass
class _BaseClass:
    """Base class for Queenbee DSL Function and DAG.

    Do not use this class directly.
    """
    _cached_queenbee = None
    _cached_outputs = None
    _cached_package = None
    _cached_inputs = None

    @property
    def queenbee(self):
        raise NotImplementedError

    @property
    def _outputs(self) -> NamedTuple:
        raise NotImplementedError

    @property
    def _inputs(self) -> NamedTuple:
        """Return inputs as a simple object with dot notation.

        Use this property to access the inputs when creating a DAG.

        The name starts with a _ not to conflict with a possible member of the class
        with the name inputs.
        """
        if self._cached_inputs:
            return self._cached_inputs
        cls_name = camel_to_snake(self.__class__.__name__)
        mapper = {
            inp.name.replace('-', '_'): {
                'name': inp.name.replace('-', '_'),
                'parent': cls_name,
                'value': inp
            } for inp in self.queenbee.inputs
        }

        inputs = namedtuple('Inputs', list(mapper.keys()))
        self._cached_inputs = inputs(*list(mapper.values()))

        return self._cached_inputs

    @property
    def _package(self) -> dict:
        """Queenbee package information.

        This information will only be available if the function is part of a Python
        package.
        """
        if self._cached_package:
            return self._cached_package

        module = importlib.import_module(self._python_package)
        assert hasattr(module, '__queenbee__'), \
            'Failed to find __queenbee__ info in __init__.py'
        self._cached_package = getattr(module, '__queenbee__')
        return self._cached_package

    @property
    def _python_package(self) -> str:
        """Python package information for this function.

        This information will only be available if the function is part of a Python
        package.
        """
        return self.__module__.split('.')[0]
