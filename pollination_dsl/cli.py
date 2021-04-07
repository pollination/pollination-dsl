"""Pollination DSL command line interface."""
import pathlib
import os
import sys
import tempfile
import shutil

import click
from click.exceptions import ClickException
from queenbee.cli.context import Context as QueenbeeContext
from queenbee.plugin.plugin import Plugin
import yaml

from queenbee_pollination.cli.push import recipe, plugin
from queenbee_local.cli import run_recipe
from pollination_dsl.package import translate, load, _init_repo
from pollination_dsl.common import _get_package_readme, _get_package_owner, \
    name_to_pollination


@click.group()
@click.version_option()
def main():
    pass


@click.group(help='interact with pollination python DSL packages.')
@click.version_option()
@click.pass_context
def dsl(ctx):
    """Pollination python DSL plugin."""
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
def translate_recipe(ctx, recipe_name, target_folder, queenbee, no_exit=False):
    """Translate a Pollination recipe to a Queenbee recipe or a Luigi pipeline.

    You can use queenbee local run command to run the pipline after export.

    \b
    Args:\b
        recipe-name: Recipe name. Recipe must be installed as a Python package.\b
        target-folder: Path to target folder to translate the recipe.\b

    """
    folder = pathlib.Path(target_folder)
    folder.mkdir(exist_ok=True)
    if not recipe_name.startswith('pollination'):
        recipe_name = f'pollination-{recipe_name}'

    if queenbee:
        recipe_folder = translate(recipe_name, target_folder=target_folder, baked=True)
        print(f'Success: {recipe_folder}', file=sys.stderr)
        if no_exit:
            return
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
            if no_exit:
                return
            return sys.exit(0)


@dsl.command('push')
@click.argument('package_name')
@click.option(
    '-e', '--endpoint', help='Endpoint to push the resource.', show_default=True,
    default='https://api.pollination.cloud'
)
# TODO: Add better support for mapping different dependencies to different sources. For
# now it is all set to the same value which is fine for our use cases.
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
    '--tag', '-t', help='An optional tag to enforce tag number. By default the tag will '
    'be extracted from package version.',
)
@click.option(
    '--dry-run', '-dr', help='An option to test the command and export the package to '
    'a folder without pushing it to endpoint.', is_flag=True, default=False
)
@click.option(
    '--push-dependencies', '-pd', help='An option to push any dependencies the package '
    'might have to the same endpoint.', is_flag=True, default=False
)
@click.pass_context
def push_resource(ctx, package_name, endpoint, source, public, tag, dry_run, push_dependencies):
    """Push a pollination dsl recipe or plugin to Pollination.

    To run this command you need queenbee-pollination[cli] installed. You can also
    get these libraries by running ``pip install pollination-dsl[pollination]`` command.

    \b
    Args:
        package_name: The name of the recipe or plugin. Recipe must be installed as a
            Python package.

    """
    # set the config vars
    ctx.obj.config.endpoint = endpoint
    ctx.obj.config.token = os.getenv('QB_POLLINATION_TOKEN')
    if not dry_run:
        assert ctx.obj.config.token is not None, \
            'Pollination token is not set. Use QB_POLLINATION_TOKEN to set it as an ' \
            'env variable. You can generate an API key under settings from your ' \
            'Pollination profile.'

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

    if resource_type == 'recipe' and push_dependencies:
        # recuresively push dependencies 
        for dependency in resource.dependencies:
            ctx.invoke(
                push_resource,
                package_name=dependency.name, endpoint=endpoint, source=source,
                dry_run=dry_run, push_dependencies=True,
            )

    sub_folder = package_name.replace('_', '-').replace('pollination-', '')

    # write to a folder
    temp_dir = tempfile.mkdtemp()
    folder = pathlib.Path(temp_dir, sub_folder)

    resource.to_folder(
        folder_path=folder,
        readme_string=_get_package_readme(package_name)
    )

    if tag is None:
        tag = resource.metadata.tag

    # overwite resources in dependencies
    if resource_type == 'recipe':
        source = source or 'https://api.pollination.cloud/registries'
        # update the value for source in dependencies.yaml file
        dep_file = pathlib.Path(folder, 'dependencies.yaml')
        data = yaml.safe_load(dep_file.read_bytes())
        for dep in data['dependencies']:
            dep_name = name_to_pollination(dep['name'])
            dep_owner = _get_package_owner(dep_name)
            dep['source'] = os.path.join(source, dep_owner).replace('\\', '/')
        yaml.dump(data, dep_file.open('w'))

    print(f'pushing {owner}/{sub_folder}:{tag} to {endpoint}')

    if dry_run:
        print(folder, file=sys.stderr)
    else:
        ctx.invoke(
            cmd, path=folder, owner=owner, tag=tag, create_repo=True, public=public
        )


@dsl.command('run')
@click.argument('recipe_name')
@click.argument(
    'project_folder',
    type=click.Path(exists=True, file_okay=False, resolve_path=True, dir_okay=True),
    default='.'
)
@click.option(
    '-i', '--inputs',
    type=click.Path(exists=True, file_okay=True, resolve_path=True, dir_okay=False),
    default=None, show_default=True, help='Path to the JSON file to'
    ' overwrite inputs for this recipe.'
)
@click.option(
    '-w', '--workers', type=int, default=1, show_default=True,
    help='Number of workers to execute tasks in parallel.'
)
@click.option(
    '-e', '--env', multiple=True, help='An option to pass environmental variables to '
    'commands. Use = to separate key and value. RAYPATH=/usr/local/lib/ray'
)
@click.option('-n', '--name', help='Simulation name for this run.')
@click.option(
    '-f', '--force', help='By default run command reuses the results from a previous '
    'simulation if they exist. This option will ignore any previous results by trying '
    'to delete the folder and running a new simulation.', is_flag=True
)
@click.option(
    '-d', '--debug',
    type=click.Path(exists=False, file_okay=False, resolve_path=True, dir_okay=True),
    help='Optional path to a debug folder. If debug folder is provided all the steps '
    'of the simulation will be executed inside the debug folder which can be used for '
    'furthur inspection.'
)
@click.pass_context
def run(ctx, recipe_name, project_folder, inputs, workers, env, name, force, debug):
    """Execute a recipe against a project folder.

    \b
    Args:
        recipe_name: Name of the recipe (e.g. pollination-daylight-factor)
        project_folder: Path to project folder. Project folder includes the input files
            and folders for the recipe.

    """
    # translate the recipe if it hasn't been translated already
    target_folder = _init_repo().parent / 'pollination-luigi'
    # TODO: Check for the recipe from the same version and don't generate it every
    # time. Add an overwrite option to the command.
    ctx.invoke(
        translate_recipe,
        recipe_name=recipe_name,
        target_folder=target_folder.as_posix(),
        queenbee=False,
        no_exit=True
    )
    # get clean recipe name
    recipe_name = recipe_name.replace('-', '_').replace('pollination_', '') \
        .replace('pollination.', '')

    recipe_folder = target_folder / recipe_name

    # run the recipe using queenbee-local
    ctx.invoke(
        run_recipe, recipe=recipe_folder, project_folder=project_folder, inputs=inputs,
        workers=workers, env=env, name=name, debug=debug, force=force
    )


main.add_command(dsl)
