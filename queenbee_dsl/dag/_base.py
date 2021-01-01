from dataclasses import dataclass
from typing import NamedTuple
import inspect
from collections import namedtuple

from queenbee.recipe.dag import DAG as QBDAG

from ..common import _BaseClass


@dataclass
class DAG(_BaseClass):
    """Baseclass for DSL DAG classes.

    Every Queenbee DAG must subclass from this class.

    Attributes:
        queenbee
        _dependencies
        _inputs
        _outputs
        _package
        _python_package

    """
    __decorator__ = 'dag'
    _cached_queenbee = None
    _cached_inputs = None
    _cached_outputs = None
    _cached_package = None

    @property
    def queenbee(self) -> QBDAG:
        """Convert this class to a Queenbee DAG."""
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
                    method.to_queenbee(method, method(cls), inputs_dict, self._package)
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
    def _dependencies(self):
        """DAG dependencies.

        Dependencies are plugins or other recipes.
        """
        cls = self.__class__
        dag_package = self._package
        dependencies = {'plugin': [], 'recipe': [], 'dag': []}
        for method_name, method in inspect.getmembers(cls):
            # try to get decorator
            qb_dec = getattr(method, '__decorator__', None)
            if qb_dec == 'task':
                # get template
                tt = method.__task_template__
                if tt.__decorator__ == 'dag':
                    if tt._package == dag_package:
                        # it's a DAG in the same package.
                        if tt not in dependencies['dag']:
                            dependencies['dag'].append(tt)
                    else:
                        # dependency is another plugin
                        if tt._package not in dependencies['recipe']:
                            dependencies['recipe'].append(tt._package)
                elif tt.__decorator__ == 'function':
                    if tt._package not in dependencies['plugin']:
                        dependencies['plugin'].append(tt._package)

        return dependencies
