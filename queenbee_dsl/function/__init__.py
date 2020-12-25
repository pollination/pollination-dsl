"""All function related decorators and objects including inputs and outputs."""
from dataclasses import dataclass
from queenbee.plugin.function import Function as QBFunction
from ._inputs import Inputs  # expose for easy import
from ._outputs import Outputs  # expose for easy import
from queenbee.base.parser import parse_double_quotes_vars


def function(cls: object):
    """Class decorator for queenbee function."""
    # make it a dataclass so it assigns all the inputs to the class
    cls = dataclass(cls)
    name = cls.__name__[0].lower() + \
        ''.join(['-' + x.lower() if x.isupper() else x for x in cls.__name__][1:])
    description = cls.__doc__
    command = None
    inputs = []
    outputs = []
    for method_name, method in cls.__dict__.items():
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

    return QBFunction(
        name=name, description=description, inputs=inputs, command=command,
        outputs=outputs
    )


def command(func):
    """Class method decorator for commands."""

    def _clean_command(command):
        """A helper function to reformat python command to Queenbee command."""
        refs = parse_double_quotes_vars(command)
        for ref in refs:
            command = command.replace(
                ref, ref.replace('self.', 'inputs.').replace('_', '-')
            )
        return command

    func.__decorator__ = 'command'
    func.parse_command = _clean_command
    return func
