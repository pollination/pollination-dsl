from dataclasses import dataclass
from typing import NamedTuple
import inspect
from collections import namedtuple

from queenbee.plugin.function import Function as QBFunction
from queenbee.base.parser import parse_double_quotes_vars

from ..common import camel_to_snake, _BaseClass


@dataclass
class Function(_BaseClass):
    """Baseclass for DSL Function classes.

    Every Queenbee DAG must subclass from this class.

    Attributes:
        queenbee
        _dependencies
        _inputs
        _outputs
        _package
        _python_package

    """
    __decorator__ = 'function'

    @property
    def queenbee(self) -> QBFunction:
        """Convert this class to a Queenbee Function."""
        # cache the Function since it always stays the same for each instance
        if self._cached_queenbee:
            return self._cached_queenbee

        cls = self.__class__

        name = camel_to_snake(cls.__name__)
        description = cls.__doc__
        command = None
        inputs = []
        outputs = []

        for method_name, method in inspect.getmembers(cls):
            # try to get decorator
            qb_dec = getattr(method, '__decorator__', None)
            if qb_dec is None:
                continue
            if qb_dec == 'command':
                # TODO: improve find and replace
                command = method.parse_command(method(cls))
            elif qb_dec == 'input':
                inputs.append(method.to_queenbee(name=method_name))
            elif qb_dec == 'output':
                outputs.append(method.to_queenbee(name=method_name))
            else:
                raise ValueError(f'Unsupported __decorator__: {qb_dec}')

        self._cached_queenbee = QBFunction(
            name=name, description=description, inputs=inputs, command=command,
            outputs=outputs
        )

        return self._cached_queenbee

    @property
    def _outputs(self) -> NamedTuple:
        """Return function outputs as a simple object with dot notation.

        Use this property to access the outputs when creating a DAG.

        The name starts with a _ not to conflict with a possible member of the class
        with the name outputs.
        """
        if self._cached_outputs:
            return self._cached_outputs
        cls_name = camel_to_snake(self.__class__.__name__)
        mapper = {
            out.name.replace('-', '_'): {
                'name': out.name.replace('-', '_'),
                'parent': cls_name, 'value': out
            } for out in self.queenbee.outputs
        }
        outputs = namedtuple('Outputs', list(mapper.keys()))
        self._cached_outputs = outputs(*list(mapper.values()))

        return self._cached_outputs


def command(func):
    """Command decorator for a task.

    A method that is decorated by a command must return a string. Use ``{{}}`` to
    template the command with command arguments (e.g. {{self.name}}).

    """

    def _clean_command(command: str) -> str:
        """A helper function to reformat python command to Queenbee function commands."""
        refs = parse_double_quotes_vars(command)
        for ref in refs:
            command = command.replace(
                ref, ref.replace('self.', 'inputs.').replace('_', '-')
            )
        return command

    func.__decorator__ = 'command'
    func.parse_command = _clean_command
    return func
