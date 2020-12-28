from typing import NamedTuple
import re
import inspect
from collections import namedtuple
from typing import Dict, List

from queenbee.recipe.dag import DAGTask
from queenbee.io.outputs.task import TaskReturn, TaskPathReturn
from queenbee.io.inputs.task import TaskArguments, TaskArgument, TaskPathArgument

from ._inputs import _InputBase as RecipeInput
from ._inputs import Inputs as RecipeInputs
from ..function._outputs import Outputs as TaskOutputs


def camel_to_snake(name: str) -> str:
    """Change name from CamelCase to snake-case."""
    return name[0].lower() + \
        ''.join(['-' + x.lower() if x.isupper() else x for x in name][1:])


def _validate_task_args(func) -> None:
    """Validate task arguments."""
    func_args = inspect.getfullargspec(func)
    arg_names = func_args.args[1:]  # first arg is self
    defaults = func_args.defaults  # default values
    if len(arg_names) == 0:
        # no input arguments
        return
    # all args must have default values - raise an error if one is missing
    elif len(arg_names) != len(defaults):
        # number of arguments with missing values
        count = len(arg_names) - len(defaults)
        args = arg_names[: count]
        raise ValueError(
            f'Missing value for argument(s) in task "{func.__name__}" -> '
            f'{", ".join(args)}.\nAll the arguments should have an assigned value.'
        )


def _add_sub_path(arg: Dict, sub_paths: Dict) -> Dict:
    """Add the sub_path field to an argument."""
    if arg['name'] in sub_paths:
        arg['sub_path'] = sub_paths[arg['name']]

    return arg


def _get_task_arguments(func, inputs_info, sub_paths) -> List[TaskArguments]:
    """Get task arguments as Queenbee task arguments."""
    task_args = []
    template = func.__task_template__
    func_args = inspect.getfullargspec(func)
    # print(func_args)
    # print('-----------\n')
    names = func_args.args[1:]  # first arg is self
    if not names:
        # no arguments
        return task_args

    values = func_args.defaults

    for name, value_info in zip(names, values):
        if isinstance(value_info, RecipeInput):
            variable = inputs_info[id(value_info)]
            if value_info.is_artifact:
                # file, folder, path
                type_mapper = {
                    RecipeInputs.file: 'InputFileReference',
                    RecipeInputs.folder: 'InputFolderReference',
                    RecipeInputs.path: 'InputPathReference'
                }
                arg_dict = {
                    'name': name,
                    'type': 'TaskPathArgument',
                    'from': {
                        'type': type_mapper[type(value_info)],
                        'variable': variable
                    }
                }
                arg_dict = _add_sub_path(arg_dict, sub_paths)
                arg = TaskPathArgument.parse_obj(arg_dict)
            else:
                arg_dict = {
                    'name': name,
                    'type': 'TaskArgument',
                    'from': {
                        'type': 'InputReference',
                        'variable': variable
                    }
                }
                arg_dict = _add_sub_path(arg_dict, sub_paths)
                arg = TaskArgument.parse_obj(arg_dict)
        else:
            # task or value
            try:
                parent = value_info['parent']
            except TypeError:
                # value
                assert False, f'value not implemeneted: {name}'
            else:
                # tasks
                value = value_info['value']
                variable = value_info['name']
                if value.is_artifact:
                    # file, folder or path - TaskPathArgument
                    # TODO: add these values as a property to function output types
                    type_mapper = {
                        TaskOutputs.file: 'TaskFileReference',
                        TaskOutputs.folder: 'TaskFolderReference',
                        TaskOutputs.path: 'TaskPathReference'
                    }
                    arg_dict = {
                        'name': name,
                        'type': 'TaskPathArgument',
                        'from': {
                            'type': type_mapper[type(value)],
                            'name': parent,
                            'variable': variable
                        }
                    }
                    arg_dict = _add_sub_path(arg_dict, sub_paths)
                    arg = TaskPathArgument.parse_obj(arg_dict)
                else:
                    # parameter
                    arg_dict = {
                        'name': name, 'type': 'TaskArgument',
                        'from': {
                            'type': 'TaskReference',
                            'name': parent,
                            'variable': variable
                        }
                    }
                    arg_dict = _add_sub_path(arg_dict, sub_paths)
                    arg = TaskArgument.parse_obj(arg_dict)

        task_args.append(arg)

    return task_args


def _get_task_returns(func) -> NamedTuple:
    """Set task returns based on template outputs and returns."""
    template = func.__task_template__
    pattern = r'[\'\"]from[\'\"]\s*:\s*.*\._outputs\.(\S*)\s*[,}]'
    parent = func.__name__.replace('_', '-')
    src = inspect.getsource(func)
    matches = re.findall(pattern, src)
    mapper = {
        match: {
            'name': match.replace('_', '-'),
            'parent': parent,
            'value': getattr(template, match)
        } for match in matches
    }
    outputs = namedtuple('Outputs', list(mapper.keys()))
    return outputs(*list(mapper.values()))


def task(template, needs=None, loop=None, sub_folder=None, sub_paths: Dict = None,
         annotations=None):
    """A decorator for task methods in a DAG."""

    sub_paths = sub_paths or {}
    sub_paths = {key.replace('-', '_'): value for key, value in sub_paths.items()}

    def task_func(func):
        # add __decorator___ so I can find the tasks later in the class decorator
        func.__decorator__ = 'task'
        # set up task information
        # a template can only be from type recipe or task
        assert hasattr(template, '__decorator__') and \
            getattr(template, '__decorator__') in {'function', 'recipe'}, \
            f'Invalid input type for template: {template}\n' \
            'A template must be either a Function or a Recipe.'
        func.__task_template__ = template()

        # technically a task should have _returns but I _felt_ it will be easier
        # for user to use _outputs here to keep it similar to Function and Recipe.
        func._outputs = _get_task_returns(func)

        # check tasks that this task relies on
        func.__task_needs__ = needs or []
        for need in func.__task_needs__:
            assert hasattr(need, '__decorator__') and \
                getattr(need, '__decorator__') == 'task', \
                f'Invalid input type for needs: {need}. A task can only rely on ' \
                'another task in the same recipe.'

        # TODO: Add checks for loop object
        func.__task_loop__ = loop

        func.__task_annotations__ = annotations or {}
        func.__task_subfolder__ = sub_folder

        # double check task arguments
        _validate_task_args(func)

        # assign to_queenbee function to task as an inner function
        # this functions will be called when Recipe object generates DAGTasks
        def to_queenbee(method, returns: List[Dict], dag_inputs: Dict[int, str]):
            """Convert a task method to a Queenbee DAGTask."""
            name = method.__name__.replace('_', '-')
            tt = method.__task_template__
            template = f'{tt._package["name"]}/{camel_to_snake(tt.__class__.__name__)}'
            task_needs = [
                need.__name__.replace('_', '-') for need in method.__task_needs__
            ]
            # TODO: validate arguments against needs to ensure all the task names are
            # included in needs.
            task_arguments = _get_task_arguments(method, dag_inputs, sub_paths)
            task_returns = []
            for out in returns:
                from_ = out.get('from', None)
                from_ = from_['value'] if from_ else from_
                to_ = out.get('to', None)
                description = out.get('description', None)
                if from_.is_artifact:
                    assert to_ is not None, 'Missing \'to\' key for {from_.name}. ' \
                        'All file and folder returns must provide a target path using ' \
                        'the `to` key.'
                    return_ = TaskPathReturn(
                        name=from_.name, description=description, path=to_
                    )
                else:
                    # returning a parameter
                    return_ = TaskReturn(name=from_.name, description=description)
                task_returns.append(return_)

            return DAGTask(
                name=name, template=template, needs=task_needs, arguments=task_arguments,
                returns=task_returns
            )

        func.to_queenbee = to_queenbee

        return func

    return task_func
