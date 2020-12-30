from dataclasses import dataclass
from typing import NamedTuple
import inspect
from collections import namedtuple
import importlib

from queenbee.recipe.dag import DAG as QBDAG

from ..common import camel_to_snake


@dataclass
class DAG:
    """Baseclass for DSL DAG classes."""
    __decorator__ = 'dag'
    _cached_queenbee = None
    _cached_inputs = None
    _cached_outputs = None
    _cached_package = None

    @property
    def queenbee(self) -> QBDAG:
        """Convert this class to a Queenbee class."""
        # cache the DAG since it always stays the same for each instance
        if self._cached_queenbee:
            return self._cached_queenbee

        cls = self.__class__

        name = cls.__name__[0].lower() + \
            ''.join(['-' + x.lower() if x.isupper() else x for x in cls.__name__][1:])

        # create a mapper for inputs and use it to track back the name of the inputs
        # when creating a task reference by using the id of the assigned item.
        inputs_dict = {}
        for method_name, method in inspect.getmembers(cls):
            # try to get decorator
            qb_dec = getattr(method, '__decorator__', None)
            if qb_dec is None or qb_dec != 'input':
                continue
            inputs_dict[id(method)] = method_name.replace('_', '-')

        tasks = []
        inputs = []
        outputs = []

        for method_name, method in inspect.getmembers(cls):
            # try to get decorator
            qb_dec = getattr(method, '__decorator__', None)
            if qb_dec is None:
                continue
            if qb_dec == 'task':
                tasks.append(
                    method.to_queenbee(method, method(cls), inputs_dict)
                )
            elif qb_dec == 'input':
                inputs.append(method.to_queenbee(name=method_name))
            elif qb_dec == 'output':
                outputs.append(method.to_queenbee(name=method_name))
            else:
                raise ValueError(f'Unsupported __decorator__: {qb_dec}')

        self._cached_queenbee = QBDAG(
            name=name, inputs=inputs, tasks=tasks, outputs=outputs
        )
        return self._cached_queenbee

    @property
    def _inputs(self) -> NamedTuple:
        """Return function inputs as a simple object with dot notation.

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
    def _outputs(self) -> NamedTuple:
        """Return dag outputs as a simple object with dot notation.

        Use this property to access the outputs when creating a DAG.

        The name starts with a _ not to conflict with a possible member of the class
        with the name outputs.
        """
        if self._cached_outputs:
            return self._cached_outputs

        mapper = {out.name: out for out in self.queenbee.outputs}
        outputs = namedtuple('Outputs', list(mapper.keys()))
        self._cached_outputs = outputs(*list(mapper.values()))

        return self._cached_outputs

    @property
    def _package(self) -> dict:
        """Queenbee package information.

        This information will only be available if the dag is part of a Python
        package.
        """
        if self._cached_package:
            return self._cached_package

        module = importlib.import_module(self._python_package)
        assert hasattr(module, '__queenbee__'), \
            f'Failed to find __queenbee__ info in {module.__name__}\'s __init__.py'
        self._cached_package = getattr(module, '__queenbee__')
        return self._cached_package

    @property
    def _python_package(self) -> str:
        """Python package information for this dag.

        This information will only be available if the dag is part of a Python
        package.
        """
        return self.__module__.split('.')[0]
