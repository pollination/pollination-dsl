from dataclasses import dataclass
from queenbee.plugin.function import Function as QBFunction
import inspect


@dataclass
class Function:
    """Baseclass for DSL Function classes."""
    __decorator__ = 'function'
    _cached_queenbee = None

    @property
    def queenbee(self):
        """Convert this class to a Queenbee class."""
        # cache the Function since it always stays the same for each instance
        if self._cached_queenbee:
            return self._cached_queenbee

        cls = self.__class__

        name = cls.__name__[0].lower() + \
            ''.join(['-' + x.lower() if x.isupper() else x for x in cls.__name__][1:])
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
