"""Queenbee DSL command line interface."""
import pathlib
import os
import sys
import importlib
import tempfile

import click
from click.exceptions import ClickException

from queenbee.config import Config as QBConfig
from queenbee.plugin.plugin import Plugin
import yaml


from queenbee_dsl.package import translate, load


@click.group(help='interact with queenbee python DSL packages.')
@click.version_option()
@click.pass_context
def dsl(ctx):
    """Queenbee Python DSL plugin."""
    try:
        import queenbee_pollination
    except ImportError:
        # no queenbee pollination installed
        pass
    else:
        from queenbee_pollination.cli.context import Context
        ctx.obj = Context()


@dsl.command('translate')
@click.argument('recipe_name')
@click.argument(
    'target-folder',
    type=click.Path(exists=False, file_okay=False, resolve_path=True, dir_okay='True'),
    default='.'
)
@click.option(
    '--queenbee/--luigi', is_flag=True, default=True, help='Switch between a baked '
    'Queenbee recipe and a luigi pipeline. To translate to a luigi pipeline you must '
    'have queenbee-luigi package installed.'
)
@click.pass_context
def translate_recipe(ctx, recipe_name, target_folder, queenbee):
    """Translate a queenbee recipe to a luigi pipeline.

    Use queenbee local run command to run the pipline after export.

    \b
    Args:\b
        recipe-name: Recipe name. Recipe must be installed as a Python package.\b
        target-folder: Path to target folder to translate the recipe.\b

    """
    folder = pathlib.Path(target_folder)
    folder.mkdir(exist_ok=True)

    if queenbee:
        recipe_folder = translate(recipe_name, target_folder=target_folder, baked=True)
        print(f'Success: {recipe_folder}', file=sys.stderr)
        return sys.exit(0)

    else:
        try:
            from queenbee_luigi.recipe import Recipe
        except ImportError:
            raise ClickException(
                'Failed to find queenbee-luigi. To translate a recipe to luigi pipeline '
                'you must have queenbee-luigi installed.'
            )

        recipe = load(recipe_name, baked=True)
        try:
            rep = Recipe(recipe)
            recipe_folder = rep.write(target_folder=target_folder)
        except Exception as e:
            print(f'Failed to translate the recipe:\n{e}', file=sys.stderr)
            return sys.exit(1)
        else:
            print(f'Success: {recipe_folder}', file=sys.stderr)
            return sys.exit(0)


@dsl.command('push')
@click.argument('resource_name')
@click.option('-o', '--owner', help='A pollination account name.')
@click.option(
    '-e', '--endpoint', help='Endpoint to push the resource.', show_default=True,
    default='https://api.pollination.cloud'
)
# TODO: Add better support for mapping dependencies to sources. For now it is all
# set to the same value which is fine for our use cases.
@click.option(
    '-src', '--source', help='A link to source the dependencies. This value will '
    'overwrite the source value in recipe\'s dependencies files.'
)
@click.option(
    '--public/--private', help='Indicate if the recipe or plugin should be created as '
    'a public or a private resource. This option does not change the visibility of a '
    'resource if it already exist.', is_flag=True, default=True
)
@click.pass_context
def push_resource(ctx, resource_name, owner, endpoint, source, public):
    """Push a queenbee DSL recipe or plugin to Pollination.

    To run this command you need queenbee-pollination[cli] installed. You can also
    get these libraries by running ``pip install queenbee-dsl[pollination]`` command.

    \b
    Args:
        resource_name: The name of the recipe or plugin. Recipe must be installed as a
            Python package.

    """
    try:
        from queenbee_pollination.cli.push import recipe, plugin
    except ImportError:
        raise ImportError(
            'Failed to import queenbee_pollination. Try running '
            '`pip install queenbee-dsl[pollination]` command.'
        )
    # set the config vars
    ctx.obj.config.endpoint = endpoint
    ctx.obj.config.token = os.getenv('QB_POLLINATION_TOKEN')
    assert ctx.obj.config.token is not None, \
        'Pollination token is not set. Use QB_POLLINATION_TOKEN to set it as an env ' \
        'variable. You can generate an API key under settings from your Pollination ' \
        'profile.'

    if ctx.obj.queenbee is None:
        ctx.obj.queenbee = QBConfig()

    resource = load(resource_name, False)

    if isinstance(resource, Plugin):
        cmd = plugin
        resource_type = 'plugin'
    else:
        cmd = recipe
        resource_type = 'recipe'

    py_module = importlib.import_module(resource_name.replace('-', '_'))
    tag = py_module.__queenbee__['tag']

    # write to a folder
    temp_dir = tempfile.mkdtemp()
    folder = pathlib.Path(temp_dir, py_module.__queenbee__['name'])
    resource.to_folder(folder_path=folder)
    # overwite resources in dependencies
    if resource_type == 'recipe' and source is not None:
        # update the value for source in dependencies.yaml file
        dep_file = pathlib.Path(folder, 'dependencies.yaml')
        data = yaml.safe_load(dep_file.read_bytes())
        for dep in data['dependencies']:
            dep['source'] = source
        yaml.dump(data, dep_file.open('w'))

    ctx.invoke(
        cmd, path=folder, owner=owner, tag=tag, create_repo=True, public=public
    )
