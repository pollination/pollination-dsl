from typing import NamedTuple
import re
import inspect
from collections import namedtuple
from typing import Dict, List

from queenbee.recipe.task import DAGTask, DAGTaskLoop
from queenbee.io.outputs.task import TaskReturn, TaskPathReturn
from queenbee.io.inputs.task import TaskArguments, TaskArgument, TaskPathArgument
from queenbee.base.parser import parse_double_quotes_vars

from .inputs import _InputBase as DAGInput
from ..common import camel_to_snake


def _validate_task_args(func) -> None:
    """Validate task arguments.

    This function ensures that the value for all the task arguments are provided.
    """
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
    name = arg['name'].replace('-', '_')
    if name in sub_paths:
        arg['sub_path'] = sub_paths[name]

    return arg


def _get_from(value, inputs_info) -> Dict:
    """Return a Queenbee From value dictionary.

    The output will be an InputReference, TaskReference or a ValueReference or a
    ValueListReference.

    Args:
        value: Reference object.
        inputs_info: DAG inputs info to get the information for DAGInput types.

    Returns:
        Dict - a Queenbee From value dictionary.
    """
    if isinstance(value, DAGInput):
        variable = inputs_info[id(value)]
        return {'type': value.reference_type, 'variable': variable}
    try:
        # only TaskReference has parent
        parent = value['parent']
    except TypeError:
        # value
        return {}
    else:
        # Task reference values and names are nested
        variable = value['name']
        value = value['value']
        return {'type': value.reference_type, 'name': parent, 'variable': variable}


def _get_task_arguments(func, inputs_info, sub_paths) -> List[TaskArguments]:
    """Get task input arguments in Python method as Queenbee task arguments."""
    task_args = []
    template = func.__task_template__
    func_args = inspect.getfullargspec(func)

    names = func_args.args[1:]  # first arg is self
    if not names:
        # no arguments
        return task_args

    values = func_args.defaults

    for name, value_info in zip(names, values):
        from_ = _get_from(value_info, inputs_info)
        arg_dict = {'name': name.replace('_', '-'), 'from': from_}
        arg_dict = _add_sub_path(arg_dict, sub_paths)
        if isinstance(value_info, DAGInput):
            if value_info.is_artifact:
                # file, folder, path
                arg = TaskPathArgument.parse_obj(arg_dict)
            else:
                arg = TaskArgument.parse_obj(arg_dict)
        elif from_ != {}:
            # task or value
            # tasks
            value = value_info['value']
            if value.is_artifact:
                arg = TaskPathArgument.parse_obj(arg_dict)
            else:
                # parameter
                arg = TaskArgument.parse_obj(arg_dict)
        else:
            # value reference
            func_input = getattr(template._inputs, name)['value']
            if func_input.is_artifact:

                arg_dict['from']['path'] = value_info

                if func_input.type == 'FunctionFolderInput':
                    # folder
                    arg_dict['from']['type'] = 'ValueFolderReference'
                else:
                    # file
                    arg_dict['from']['type'] = 'ValueFileReference'

                arg = TaskPathArgument.parse_obj(arg_dict)
            else:
                # value reference
                arg_dict['from']['value'] = value_info
                arg_dict['from']['type'] = 'ValueReference'
                arg = TaskArgument.parse_obj(arg_dict)

        task_args.append(arg)

    return task_args


def _get_task_loop(value, inputs_info) -> DAGTaskLoop:
    """Get TaskLoop as a queenbee TaskLoop."""
    if not value:
        return None
    from_ = _get_from(value, inputs_info)
    return DAGTaskLoop.parse_obj({'from': from_})


def _get_task_returns(func) -> NamedTuple:
    """Get task returns based on template outputs and returns."""
    template = func.__task_template__
    pattern = r'[\'\"]from[\'\"]\s*:\s*.*\._outputs\.(\S*)\s*[,}]'
    parent = func.__name__.replace('_', '-')
    src = inspect.getsource(func)
    # remove the last } which happens in case of parameters input. Somene who
    # knows regex better than I do should be able to fix this by changing the pattern
    # here is an example to recreate the issue.
    #   return [
    #       {'from': SplitGrid()._outputs.grids_list},
    #       {'from': SplitGrid()._outputs.output_folder, 'to': 'sub_grids'}
    #  ]
    matches = [match.replace('}', '') for match in re.findall(pattern, src)]
    mapper = {
        match: {
            'name': match.replace('_', '-'),
            'parent': parent,
            'value': getattr(template, match)
        } for match in matches
    }
    outputs = namedtuple('Outputs', list(mapper.keys()))
    return outputs(*list(mapper.values()))


def task(template, needs=None, loop=None, sub_folder: str = None, sub_paths: Dict = None,
         annotations: Dict = None):
    """Task decorator for methods in a DAG.

        @task(template=Template, ...)

        Args:
            template: A pollination-dsl Function or DAG.
            needs: A list of methods that this should be executed before this task.
                This task will only be executed after these tasks are executed
                successfully.
            loop: An iterator to loop over. The task will be executed for each item
                in this iterator.
            sub_folder: An optional sub_folder for execution of this task. If sub_folder
                is provided all the outputs from this task will be copied under the
                sub_folder. Sub_folder is usually used with loops and named based on
                the loop item to keep the results of each iteration in a separate folder.
            sub_paths: A dictionary to provide sub_path for input arguments. Sub_path is
                useful when a task only needs a file or a sub folder from the provided
                argument.
            annotations: An optional dictionary to annotate a task.

    """

    sub_paths = sub_paths or {}
    sub_paths = {key.replace('-', '_'): value for key, value in sub_paths.items()}

    def task_func(func):
        # add __decorator___ so I can find the tasks later in the class decorator
        func.__decorator__ = 'task'
        # set up task information
        # a template can only be from type dag or task
        assert hasattr(template, '__decorator__') and \
            getattr(template, '__decorator__') in {'function', 'dag'}, \
            f'Invalid input type for template: {template}\n' \
            'A template must be either a Function or a DAG.'
        func.__task_template__ = template()

        # technically a task should have _returns but I _felt_ it will be easier
        # for user to use _outputs here to keep it similar to Function and DAG.
        func._outputs = _get_task_returns(func)

        # check tasks that this task relies on
        func.__task_needs__ = needs or []
        for need in func.__task_needs__:
            assert hasattr(need, '__decorator__') and \
                getattr(need, '__decorator__') == 'task', \
                f'Invalid input type for needs: {need}. A task can only rely on ' \
                'another task in the same dag.'

        func.__task_loop__ = loop

        func.__task_annotations__ = annotations or {}
        func.__task_subfolder__ = sub_folder

        # double check task arguments
        _validate_task_args(func)

        # assign to_queenbee function to task as an inner function
        # this functions will be called when DAG object generates DAGTasks
        def to_queenbee(
                method, returns: List[Dict], dag_inputs: Dict[int, str], dag_package: str
                ):
            """Convert a task method to a Queenbee DAGTask."""
            name = method.__name__.replace('_', '-')
            tt = method.__task_template__
            if tt.__decorator__ == 'dag' and tt._package == dag_package:
                # template is another dag in the same plugin (AKA package)
                template = f'{camel_to_snake(tt.__class__.__name__)}'
            else:
                template = \
                    f'{tt._package["name"]}/{camel_to_snake(tt.__class__.__name__)}'

            task_needs = [
                need.__name__.replace('_', '-') for need in method.__task_needs__
            ]
            # TODO: validate arguments against needs to ensure all the task names are
            # included in needs.
            task_arguments = _get_task_arguments(method, dag_inputs, sub_paths)
            task_loop = _get_task_loop(method.__task_loop__, dag_inputs)
            task_returns = []
            for out in returns or []:
                from_ = out.get('from', None)
                from_ = from_['value'] if from_ else from_
                to_ = out.get('to', None)
                description = out.get('description', None)
                if from_.is_artifact:
                    assert to_ is not None, 'Missing \'to\' key for {from_.name}. ' \
                        'All file and folder returns must provide a target path using ' \
                        'the `to` key.'
                    if to_:
                        # find and replace referenced values
                        refs = parse_double_quotes_vars(to_)
                        for ref in refs:
                            to_ = to_.replace(
                                ref, ref.replace('self.', 'inputs.').replace('_', '-')
                            )
                    return_ = TaskPathReturn(
                        name=from_.name, description=description, path=to_
                    )
                else:
                    # returning a parameter
                    return_ = TaskReturn(name=from_.name, description=description)
                task_returns.append(return_)

            annotations = method.__task_annotations__
            sub_folder = method.__task_subfolder__
            return DAGTask(
                name=name, template=template, needs=task_needs, arguments=task_arguments,
                returns=task_returns, loop=task_loop, sub_folder=sub_folder,
                annotations=annotations
            )

        func.to_queenbee = to_queenbee

        return func

    return task_func
