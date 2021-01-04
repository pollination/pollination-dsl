"""Queenbee DSL command line interface."""
import pathlib
import sys

import click
from click.exceptions import ClickException

from queenbee.cli import Context

from queenbee_dsl.package import translate, load


@click.group(help='interact with queenbee python DSL packages.')
@click.version_option()
@click.pass_context
def dsl(ctx):
    """Queenbee Python DSL plugin."""
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
