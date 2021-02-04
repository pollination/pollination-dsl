"""Pollination DSL command line interface."""
import pathlib
import os
import sys
import tempfile

import click
from click.exceptions import ClickException

from queenbee.cli.context import Context as QueenbeeContext
from queenbee.plugin.plugin import Plugin
import yaml


from pollination_dsl.package import translate, load, _get_package_readme, \
    _get_package_owner


@click.group()
@click.version_option()
def main():
    pass


@click.group(help='interact with pollination python DSL packages.')
@click.version_option()
@click.pass_context
def dsl(ctx):
    """Pollination python DSL plugin."""
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
    'Queenbee recipe or a luigi pipeline. To translate to a luigi pipeline you must '
    'have queenbee-luigi package installed.'
)
@click.pass_context
def translate_recipe(ctx, recipe_name, target_folder, queenbee):
    """Translate a Pollination recipe to a Queenbee recipe or a Luigi pipeline.

    You can use queenbee local run command to run the pipline after export.

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
@click.argument('package_name')
@click.option(
    '-e', '--endpoint', help='Endpoint to push the resource.', show_default=True,
    default='https://api.pollination.cloud'
)
# TODO: Add better support for mapping dependencies to sources. For now it is all
# set to the same value which is fine for our use cases.
@click.option(
    '-src', '--source', help='A link to replace the source for dependencies. This value '
    'will overwrite the source value in recipe\'s dependencies files. By default it '
    'will be set to https://api.pollination.cloud/registries'
)
@click.option(
    '--public/--private', help='Indicate if the recipe or plugin should be created as '
    'a public or a private resource. This option does not change the visibility of a '
    'resource if it already exist.', is_flag=True, default=True
)
@click.option(
    '--dry-run', '-dr', help='An option to test the command and export the package to '
    'a folder without pushing it to endpoint.', is_flag=True, default=False
)
@click.pass_context
def push_resource(ctx, package_name, owner, endpoint, source, public, dry_run):
    """Push a pollination dsl recipe or plugin to Pollination.

    To run this command you need queenbee-pollination[cli] installed. You can also
    get these libraries by running ``pip install pollination-dsl[pollination]`` command.

    \b
    Args:
        package_name: The name of the recipe or plugin. Recipe must be installed as a
            Python package.

    """
    try:
        from queenbee_pollination.cli.push import recipe, plugin
    except ImportError:
        raise ImportError(
            'Failed to import queenbee_pollination. Try running '
            '`pip install pollination-dsl[pollination]` command.'
        )
    # set the config vars
    ctx.obj.config.endpoint = endpoint
    ctx.obj.config.token = os.getenv('QB_POLLINATION_TOKEN')
    assert ctx.obj.config.token is not None, \
        'Pollination token is not set. Use QB_POLLINATION_TOKEN to set it as an env ' \
        'variable. You can generate an API key under settings from your Pollination ' \
        'profile.'

    if ctx.obj.queenbee is None:
        ctx.obj.queenbee = QueenbeeContext()

    resource = load(package_name, False)

    # get package owner
    owner = _get_package_owner(package_name)

    if isinstance(resource, Plugin):
        cmd = plugin
        resource_type = 'plugin'
    else:
        cmd = recipe
        resource_type = 'recipe'

    sub_folder = package_name.replace('_', '-').replace('pollination-', '')

    # write to a folder
    temp_dir = tempfile.mkdtemp()
    folder = pathlib.Path(temp_dir, sub_folder)
    resource.to_folder(
        folder_path=folder,
        readme_string=_get_package_readme(package_name)
    )
    tag = resource.metadata.tag
    # overwite resources in dependencies
    if resource_type == 'recipe':
        source = source or 'https://api.pollination.cloud/registries'
        # update the value for source in dependencies.yaml file
        dep_file = pathlib.Path(folder, 'dependencies.yaml')
        data = yaml.safe_load(dep_file.read_bytes())
        for dep in data['dependencies']:
            owner = _get_package_owner(dep['name'])
            dep['source'] = pathlib.Path(source, owner).as_posix()
        yaml.dump(data, dep_file.open('w'))

    if dry_run:
        print(folder, file=sys.stderr)
    else:
        ctx.invoke(
            cmd, path=folder, owner=owner, tag=tag, create_repo=True, public=public
        )


main.add_command(dsl)
