# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_dbt_cellmagic.ipynb (unless otherwise specified).

__all__ = ['nbdbt_config', 'clear_cache', 'config_dbt', 'DbtMagicObject', 'schema', 'write_dbt']

# Internal Cell

import IPython
from IPython.core import magic_arguments
from IPython.core.magic import register_cell_magic, register_line_magic

# Internal Cell
from pathlib import Path
from typing import Union, List, Dict, Optional
import os
import shutil

# Internal Cell
IN_NBDBT_TEST = os.environ.get("IN_NBDBT_TEST", "False").lower() == "true"
NBDBT_DEBUG = False

# Internal Cell
from fastcore.all import patch

# Internal Cell
from dbt.main import parse_args, adapter_management
from dbt.task.compile import CompileTask
from dbt.contracts.results import RunExecutionResult
import dbt.flags
import dbt.tracking

# Internal Cell
dbt.tracking.active_user = dbt.tracking.User(None)
dbt.flags.INDIRECT_SELECTION = "eager"
dbt.flags.WRITE_JSON = True
dbt.flags.QUIET = True  # silent

# Internal Cell

from fal import FalDbt
import faldbt.lib as fallib

# Internal Cell

import pandas as pd

# Cell
nbdbt_config = {
    "profiles_dir": "~/.dbt"
    if os.environ.get("DBT_PROFILES_DIR") is None
    else os.environ.get("DBT_PROFILES_DIR"),
    "project_dir": None,
    "notebook": None,
    "limit_default": 1000,
}

# Internal Cell
# Add cache
import json
import hashlib

CACHE_DIR = ".nbdbt"


def load_cache(cache_name):

    cache_path = Path(nbdbt_config["project_dir"]) / CACHE_DIR / cache_name
    if cache_path.exists():
        with open(cache_path, "r") as f:
            cache_contents = f.read()
            try:
                cache_info = json.loads(cache_contents)
            except json.JSONDecodeError as e:
                if NBDBT_DEBUG:
                    raise json.JSONDecodeError(e.msg, e.doc, e.pos)
                else:
                    return None
            else:
                return cache_info

    else:
        return None


def update_cache(dmo):
    if dmo._compiled_path is None:
        raise ValueError("Could not update cache as compiled path is not set")

    cache_name = dmo.file
    cache_path = Path(nbdbt_config["project_dir"]) / CACHE_DIR / cache_name
    if not cache_path.exists():
        cache_dir = cache_path.parent
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            raise FileExistsError(
                f"cache parent path exists as a file (delete it first): {cache_dir}"
            )
    compiled_path = Path(dmo.project_dir) / dmo._compiled_path
    cache_info = {
        "formatted_sql_hash": hashlib.sha1(dmo._formatted_sql.encode()).hexdigest(),
        "compiled_path": dmo._compiled_path,
        "compiled_sql_mtime": compiled_path.stat().st_mtime,
    }
    with open(cache_path, "w") as f:
        cache_contents = json.dumps(cache_info)
        f.write(cache_contents)


def check_cache(dmo, cache):
    cache_formatted_sql_hash = cache["formatted_sql_hash"]
    formatted_sql_hash = hashlib.sha1(dmo._formatted_sql.encode()).hexdigest()
    if cache_formatted_sql_hash != formatted_sql_hash:
        return ["update_sql"]

    compiled_path = Path(dmo.project_dir) / cache["compiled_path"]
    if not compiled_path.exists():
        return ["update_model"]
    compiled_path_mtime = compiled_path.stat().st_mtime
    cache_compiled_path_mtime = cache["compiled_sql_mtime"]
    if compiled_path_mtime != cache_compiled_path_mtime:
        return ["update_model"]
    return []


def update_dmo(dmo, cache):
    dmo._compiled_path = cache["compiled_path"]

# Cell
def clear_cache(project_dir=None):
    """Removes all existing nbdbt cache entries"""
    project_dir = nbdbt_config["project_dir"] if project_dir is None else project_dir

    if project_dir is None:
        raise ValueError(
            "Please specify the dbt project dir as a parameter or as a %dbtconfig line magic"
        )
    cache_path = Path(project_dir) / CACHE_DIR
    if not cache_path.exists():
        return
    if cache_path.is_file():
        cache_path.unlink()
        return
    shutil.rmtree(cache_path, ignore_errors=True)

# Cell


@magic_arguments.magic_arguments()
@magic_arguments.argument(
    "-d",
    "--profile",
    type=str,
    default=None,
    help=("If provided, override the dbt profiles directory (default: '~/.dbt')"),
)
@magic_arguments.argument(
    "-p",
    "--project",
    type=str,
    default=None,
    help=("Set the dbt project directory"),
)
@magic_arguments.argument(
    "-n",
    "--notebook",
    type=str,
    default=None,
    help=("Set the notebook path"),
)
@magic_arguments.argument(
    "-l",
    "--limit",
    type=int,
    default=1000,
    help=("Set the default sql row limit"),
)
@register_line_magic("dbtconfig")
def config_dbt(line):
    if IN_NBDBT_TEST:
        return None
    try:
        from dbt.main import parse_args
    except ImportError:
        return "'dbt-core' not installed. Did you run 'pip install dbt-core'?"
    line_args = magic_arguments.parse_argstring(config_dbt, line)
    if line_args.profile is not None:
        nbdbt_config["profiles_dir"] = line_args.profile
    if line_args.project is not None:
        nbdbt_config["project_dir"] = line_args.project
    if line_args.notebook is not None:
        nbdbt_config["notebook"] = line_args.notebook

    nbdbt_config["limit"] = line_args.limit

# Cell


class DbtMagicObject:
    def __init__(
        self,
        raw_sql: str,  # sql string
        file: str,  # path to sql file (relative to dbt project dir)
        limit: int,  # limit row default
        project_dir: Optional[Union[str, Path]] = None,  # dbt project dir
        notebook_name: Optional[str] = None,  # name of notebook
        profile_dir: Optional[Union[str, Path]] = None,  # dbt profiles dir
    ):
        """Create a holder of dbt cell magic parameters"""
        self.raw_sql = raw_sql
        self.file = file
        self.limit = nbdbt_config["limit"] if limit == -1 else limit
        project_dir = (
            nbdbt_config["project_dir"] if project_dir is None else project_dir
        )
        if project_dir is None:
            raise ValueError("Missing value for  --project")
        self.project_dir = (
            Path(project_dir) if type(project_dir) == str else project_dir
        )

        notebook_name = (
            nbdbt_config["notebook"] if notebook_name is None else notebook_name
        )
        self.notebook_name = notebook_name

        profile_dir = (
            nbdbt_config["profiles_dir"] if profile_dir is None else profile_dir
        )
        self.profile_dir = (
            Path(profile_dir) if type(profile_dir) == str else profile_dir
        )

        # dynamic runtime attributes
        self._compiled_path: Optional[str] = None
        self._df_result: Optional[pd.DataFrame] = None

# Cell
@patch(as_prop=True)
def _formatted_sql(self: DbtMagicObject) -> str:
    """Add auto generated notice for nbdbt generated sql"""
    if not self.notebook_name:
        contents = "-- AUTOGENERATED! DO NOT EDIT!\n" + self.raw_sql
    else:
        contents = (
            f"-- AUTOGENERATED! DO NOT EDIT! File to edit: {self.notebook_name} (unless otherwise specified).\n"
            + self.raw_sql
        )
    return contents

# Cell
@patch(as_prop=True)
def _compiled_sql(self: DbtMagicObject) -> str:
    """Add auto generated notice for nbdbt generated sql"""
    if self._compiled_path is None:
        return None
    compiled_path = Path(self.project_dir) / self._compiled_path
    if not compiled_path.exists():
        return None
    with open(compiled_path, "r") as f:
        contents = f.read()
        return contents
    return None

# Cell
@patch
def _write_sql(self: DbtMagicObject) -> None:
    """Write sql to file"""
    path = self.project_dir / self.file
    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        raise FileExistsError(
            f"Sql file write failure: Existing file in parent path ${parent}"
        )

    with open(path, "w") as f:
        f.write(self._formatted_sql)

# Cell
@patch
def _compile_model(self: DbtMagicObject) -> None:
    """Compile model and store compile result"""
    parsed = parse_args(
        ["compile", "--select", self.file, "--project-dir", str(self.project_dir)]
    )
    with adapter_management():
        task = CompileTask.from_args(args=parsed)
        compile_result = task.run()
        self._compiled_path = compile_result.results[0].node.compiled_path

# Cell
@patch
def _exec_faldbt_ref(self: DbtMagicObject, limit) -> None:
    """Execute sql and return df"""
    if self._compiled_sql is None:
        raise ValueError("Model compilation step has not been executed")

    faldbt = FalDbt(
        profiles_dir=str(self.profile_dir), project_dir=str(self.project_dir)
    )
    profile_target = faldbt._profile_target
    # adapter_response, result
    limit = self.limit if limit == -1 else limit
    if limit is None:
        exec_sql = self._compiled_sql
    else:
        ctx_name = "xxx_yyy_zzz"
        exec_sql = f"""with {ctx_name} as
        (
          {self._compiled_sql}
        )
        select * from {ctx_name}
        limit {limit}
        """

    _, result = fallib._execute_sql(
        str(self.project_dir), str(self.profile_dir), exec_sql, profile_target
    )
    df_result = result
    self._df_result = df_result

# Cell
@patch
def ref(self: DbtMagicObject, limit=-1) -> pd.DataFrame:
    self._exec_faldbt_ref(limit)
    return self._df_result

# Internal Cell
from faldbt.project import _DbtTestableNode

# Cell

@patch(as_prop=True)
def schema(self: _DbtTestableNode) -> pd.DataFrame:
    profiles_dir = nbdbt_config["profiles_dir"]
    project_dir = self.node.root_path
    faldbt = FalDbt(profiles_dir=profiles_dir, project_dir=project_dir)
    profile_target = faldbt._profile_target

    node = self.node

    adapter = fallib._get_adapter(
        faldbt.project_dir, faldbt.profiles_dir, profile_target
    )

    # adapter.type() == 'bigquery'
    if adapter.type() != "bigquery":
        raise NotImplementError("No support yet for any other adapter except BigQuery")
        return None

    relation = fallib._get_target_relation(
        node,
        faldbt.project_dir,
        faldbt.profiles_dir,
        profile_target=faldbt._profile_target,
    )

    info_schema = relation.information_schema()

    column_schema = info_schema.from_relation(relation, "COLUMNS")

    column_table = column_schema.render()

    table_name = relation.table

    fetch_schema_sql = f"""
    with schema_columns as
    ( select *
    from {column_table}
    where table_name = '{table_name}'
    )
    select *
    from schema_columns
    """

    _, result = fallib._execute_sql(
        project_dir, profiles_dir, fetch_schema_sql, faldbt._profile_target
    )
    return result

# Cell
@magic_arguments.magic_arguments()
@magic_arguments.argument(
    "-a",
    "--assign",
    type=str,
    default=None,
    help=("If provided, save the output to this variable instead of displaying it."),
)
@magic_arguments.argument(
    "-p",
    "--project",
    type=str,
    default=None,
    help=("dbt project directory"),
)
@magic_arguments.argument(
    "-n",
    "--notebook",
    type=str,
    default=None,
    help=("notebook source file"),
)
@magic_arguments.argument(
    "-l",
    "--limit",
    type=int,
    default=-1,
    help=("sql limit default"),
)
@magic_arguments.argument(
    "file",
    type=str,
    help=("file path to write to"),
)
@register_cell_magic("dbt")
def write_dbt(line, cell):
    if IN_NBDBT_TEST:
        return None
    try:
        from dbt.main import parse_args
    except ImportError:
        return "'dbt-core' not installed. Did you run 'pip install dbt-core'?"
    line_args = magic_arguments.parse_argstring(write_dbt, line)
    dmo = DbtMagicObject(
        cell, line_args.file, line_args.limit, line_args.project, line_args.notebook
    )
    cache = load_cache(line_args.file)
    if cache is None:
        dmo._write_sql()
        dmo._compile_model()
        update_cache(dmo)
    else:
        check_results = check_cache(dmo, cache)
        if "update_sql" in check_results:
            dmo._write_sql()
            dmo._compile_model()
        elif "update_model" in check_results:
            dmo._compile_model()
        if len(check_results) > 0:
            update_cache(dmo)
        else:
            update_dmo(dmo, cache)

    if line_args.assign:
        IPython.get_ipython().push({line_args.assign: dmo})
        return None
    results = dmo.ref()
    return results