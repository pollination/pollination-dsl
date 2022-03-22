import inspect
import os
import subprocess
import tempfile

from dataclasses import dataclass
from typing import Any, Dict

from queenbee.plugin.function import Function as QBFunction
from queenbee.base.parser import parse_double_quotes_vars
from queenbee_local import _copy_artifacts

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

    def _try(self, inputs: Dict[str, Any], folder: str = None) -> str:
        """Try running a function locally for testing.

        This method does not return the output values. See the folder to validate the
        outputs.

        Args:
            inputs: A dictionary that maps input names to values
                (e.g. {'input_one': 5, ...}).
            folder: An optional folder to run the function. A temporary folder
                will be created if this folder is not provided.

        Returns:
            str -- path to run_folder.
        """
        func = self.queenbee
        # check all the required inputs are provided
        for inp in func.inputs:
            name = inp.name.replace('-', '_')
            if inp.required:
                assert name in inputs, f'Required input "{name}" is missing from inputs.'
                continue
            # see if default value should be used
            if name not in inputs:
                inputs[name] = inp.default

        dst = folder or tempfile.TemporaryDirectory().name

        command = ' '.join(func.command.split())

        refs = parse_double_quotes_vars(command)
        command = command.replace('{{', '{').replace('}}', '}')
        for ref in refs:
            assert ref.startswith('inputs.'), \
                'All referenced values must start with {{inputs followed with' \
                f' variable name. Invalid referenced value: {ref}'
            var = ref.replace('inputs.', '').replace('-', '_')
            command = command.replace('{%s}' % ref, str(inputs[var]))

        for art in func.artifact_inputs:
            print(f"copying input artifact: {art.name}...")
            name = art.name.replace('-', '_')
            _copy_artifacts(inputs[name], os.path.join(dst, art.path))

        cur_dir = os.getcwd()
        os.chdir(dst)

        print(f'command: {command}')

        p = subprocess.Popen(
            command, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True, env=os.environ
        )

        stdout, stderr = p.communicate()

        if p.returncode != 0 and stderr != b'':
            raise RuntimeError(stderr.decode('utf-8'))

        if stderr.decode('utf-8'):
            print(stderr.decode('utf-8'))

        if stdout.decode('utf-8'):
            print(stdout.decode('utf-8'))

        # change back to initial directory
        os.chdir(cur_dir)

        return dst


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
            # add additional check in case self in the refrence has been already replaced
            # by inputs because of a reference with a similar but shorter name.
            command = command.replace(
                ref.replace('self.', 'inputs.'),
                ref.replace('self.', 'inputs.').replace('_', '-')
            )
        return command

    func.__decorator__ = 'command'
    func.parse_command = _clean_command
    return func
