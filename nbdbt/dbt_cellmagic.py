# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_dbt_cellmagic.ipynb (unless otherwise specified).

__all__ = ['DbtMagicObject', 'write_dbt']

# Internal Cell

import IPython
from IPython.core import magic_arguments
from IPython.core.magic import register_cell_magic, register_line_magic

# Internal Cell
from pathlib import Path
from typing import Union, List, Dict, Optional

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


class DbtMagicObject:
    def __init__(
        self,
        raw_sql: str,  # sql string
        file: str,  # path to sql file (relative to dbt project dir)
        project_dir: Union[str, Path],  # dbt project dir
        notebook_name: Optional[str] = None,  # name of notebook
        profile_dir: Union[str, Path] = "~/.dbt",  # dbt profiles dir
    ):
        """Create a holder of dbt cell magic parameters"""
        self.raw_sql = raw_sql
        self.file = file
        self.project_dir = (
            Path(project_dir) if type(project_dir) == str else project_dir
        )
        self.notebook_name = notebook_name
        self.profile_dir = (
            Path(profile_dir) if type(profile_dir) == str else profile_dir
        )

        # dynamic runtime attributes
        self._formatted_sql: Optional[str] = None
        self._compile_result: Optional[RunExecutionResult] = None
        self._compiled_sql: Optional[str] = None
        self._df_result: Optional[pd.DataFrame] = None

# Cell
@patch
def _reformat_sql(self: DbtMagicObject) -> None:
    """Add auto generated notice for nbdbt generated sql"""
    if not self.notebook_name:
        contents = "-- AUTOGENERATED! DO NOT EDIT!\n" + self.raw_sql
    else:
        contents = (
            f"-- AUTOGENERATED! DO NOT EDIT! File to edit: {self.notebook_name} (unless otherwise specified).\n"
            + self.raw_sql
        )
    self._formatted_sql = contents

# Cell
@patch
def _write_sql(self: DbtMagicObject) -> None:
    """Write sql to file"""
    path = self.project_dir / self.file
    self._reformat_sql()
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
        self._compile_result = task.run()
        self._compiled_sql = self._compile_result.results[0].node.compiled_sql

# Cell
@patch
def _exec_faldbt_ref(self: DbtMagicObject) -> None:
    """Execute sql and return df"""
    if self._compiled_sql is None:
        raise ValueError("Model compilation step has not been executed")

    faldbt = FalDbt(
        profiles_dir=str(self.profile_dir), project_dir=str(self.project_dir)
    )
    profile_target = faldbt._profile_target
    # adapter_response, result
    _, result = fallib._execute_sql(
        str(self.project_dir), str(self.profile_dir), self._compiled_sql, profile_target
    )
    self._exec_sql_result = result
    df_result = pd.DataFrame.from_records(
        result.table.rows, columns=result.table.column_names, coerce_float=True
    )
    self._df_result = df_result

# Cell
@patch
def ref(self: DbtMagicObject) -> pd.DataFrame:
    self._exec_faldbt_ref()
    return self._df_result

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
    "file",
    type=str,
    help=("file path to write to"),
)
@register_cell_magic("dbt")
def write_dbt(line, cell):
    try:
        from dbt.main import parse_args
    except ImportError:
        return "'dbt-core' not installed. Did you run 'pip install dbt-core'?"
    line_args = magic_arguments.parse_argstring(write_dbt, line)
    dmo = DbtMagicObject(cell, line_args.file, line_args.project, line_args.notebook)
    dmo._write_sql()
    dmo._compile_model()
    if line_args.assign:
        IPython.get_ipython().push({line_args.assign: dmo})
        return None
    results = dmo.ref()
    return results