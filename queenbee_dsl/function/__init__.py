"""All function related decorators and objects including inputs and outputs."""
from dataclasses import dataclass
from ._inputs import Inputs  # expose for easy import
from ._outputs import Outputs  # expose for easy import
from ._base import Function
from queenbee.base.parser import parse_double_quotes_vars


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
