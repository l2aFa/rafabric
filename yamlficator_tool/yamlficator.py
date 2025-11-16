"""
This module provides functions and logging configuration for the yamlficator tool.
\nYou will need to install the PyYAML library before you can run it. (`pip install pyyaml`). We recommend using a virtual environment.

- Quick usage example:
```import logging
from pathlib import Path

from yamlficator import run_yamlficator

project_workspace_path: Path = Path("src/workspaces/sample_workspace")
desired_artifact_types: set[str] = {
    "Notebook",
    "Report",
    "SemanticModel",
    "VariableLibrary",
}
excluded_relative_paths: set[str] = {
    "sample_route_01",
    "sample_route_02/sample_subfolder_01",
    "sample_route_03/sample_subfolder_02/sample_subsubfolder_01",
}

log = logging.getLogger("yamlficator")

run_yamlficator(project_workspace_path, desired_artifact_types, excluded_relative_paths)
```
"""

# Imports
import itertools
import logging
import re
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Generator

import yaml


# Classes
class AnalysisSource(StrEnum):
    """Enumeration defined for the different analsys modes available."""

    YAML_FILE_PATH = "yaml_file_path"
    YAML_ITEM_NAME = "yaml_item_name"
    PROJECT = "Project"


class ConsoleFormatter(logging.Formatter):
    """Custom logging formatter for console output"""

    grey = "\x1b[38;20m"
    bold_white = "\x1b[1;37m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    MESSAGE_FORMAT = " %(asctime)s - %(message)s"
    DATE_FORMAT = "%H:%M:%S"

    def __init__(self):
        super().__init__()
        self.FORMATS = {
            logging.DEBUG: f"{self.grey}[debug]{self.MESSAGE_FORMAT}{self.reset}",
            logging.INFO: f"{self.bold_white}[info]{self.MESSAGE_FORMAT}{self.reset}",
            logging.WARNING: f"{self.yellow}[warn]{self.MESSAGE_FORMAT}{self.reset}",
            logging.ERROR: f"{self.red}[error]{self.MESSAGE_FORMAT}{self.reset}",
            logging.CRITICAL: f"{self.bold_red}[critical]{self.MESSAGE_FORMAT}{self.reset}",
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt=self.DATE_FORMAT)
        return formatter.format(record)


@dataclass
class ReportConfig:
    """Contains all attributes needed for customizing the report findings messages for each existing type of analysis."""

    found_msg: str
    not_found_msg: str
    result_start: str
    result_end: str
    log_level: int


# Constants
# Configuration for each existing analysis mode.
# file_path artifacts found in the YAML but not in the project are reported as errors,
# while item_name entries and project artifacts not found in the YAML are reported just as warnings.
# Feel free to modify and/or expand to suit your needs.
REPORT_CONFIGS: dict[AnalysisSource, ReportConfig] = {
    AnalysisSource.YAML_FILE_PATH: ReportConfig(
        found_msg="Your parameterization YAML file contains wrong file_path entries, please fix them before deploying:",
        not_found_msg="Congratulations, no invalid file_path references found in the YAML!",
        result_start="The file_path entry containing ",
        result_end=" was not found within the project.",
        log_level=logging.ERROR,
    ),
    AnalysisSource.YAML_ITEM_NAME: ReportConfig(
        found_msg="Your parameterization YAML file contains invalid item_name references, please check them before deploying:",
        not_found_msg="Congratulations, no invalid item_name references found in the YAML!",
        result_start="The item_name reference for ",
        result_end=" was not found within the project.",
        log_level=logging.WARNING,
    ),
    AnalysisSource.PROJECT: ReportConfig(
        found_msg="These artifacts are not included in your parameterization YAML file:",
        not_found_msg="Congratulations, there are no artifacts in the project that are not referenced in the YAML!",
        result_start="Artifact ",
        result_end=" is not referenced, check if it should be or configure its exclusion.",
        log_level=logging.WARNING,
    ),
}


# Logging
# The application's main logger ("yamlficator") is configured with two handlers:
# Console: Includes color-coded levels and minimum level set to DEBUG.
# File (yamlficator_results.log): No colors, “w” mode and minimum level set to INFO.
# Importing this module once at the start of the application is sufficient to configure logging throughout the project.
logger = logging.getLogger("yamlficator")
logger.setLevel(logging.DEBUG)
logger.propagate = False

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ConsoleFormatter())
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler("yamlficator_results.log", mode="w")
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)


# Functions
def _load_and_parse_yaml(project_workspace_path: Path) -> dict:
    """Loads the contents of the parameter.yml file safely, raising exceptions
    if anything happens.

    Args:
        project_workspace_path (Path): Path within the Fabric/Power BI project
            containing the parameter.yml file.

    Raises:
        FileNotFoundError: Error raised when the parameter.yml file is not found.
        RuntimeError: Error raised when the YAML file cannot be parsed.
        ValueError: Error raised when the parameter.yml file is empty.

    Returns:
        dict: Contents of the parsed YAML file if everything goes alright.
    """
    yaml_path: Path = project_workspace_path / "parameter.yml"
    try:
        with open(yaml_path, "r") as yaml_file:
            parameter_yaml_data = yaml.safe_load(yaml_file)
    except FileNotFoundError:
        logger.error(
            f"parameter.yml was not found at specified path '{project_workspace_path}'."
        )
        raise FileNotFoundError(
            f"❌ Error: parameter.yml was not found at specified path '{project_workspace_path}'."
        )
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file at '{yaml_path}': {e}")
        raise RuntimeError(f"❌ Error: Failed to parse YAML file at '{yaml_path}': {e}")

    if parameter_yaml_data is None:
        logger.error(f"No valid data found in YAML file at '{yaml_path}'.")
        raise ValueError(
            f"❌ Error: No valid data found in YAML file at '{yaml_path}'."
        )

    return parameter_yaml_data


def _get_yaml_entry_values(yaml_entry: dict, yaml_key: str) -> list[str]:
    """
    Gets the value of the specified attribute from the received dictionary, considering
    that it can be a string or a list of strings. A list is always returned.

    Args:
        yaml_entry (dict): The input dictionary corresponding to an
            entry in the YAML parameter file.
        yaml_key (str): The key of the attribute to be retrieved from the dictionary.

    Returns:
        list[str]: List of retrieved values.
    """
    key_value = yaml_entry.get(yaml_key)

    if isinstance(key_value, str):
        return [key_value]

    return key_value or []


def _get_file_path_artifact_name(
    file_path: str, path_pattern: re.Pattern
) -> str | None:
    """
    Gets the name of the artifact specified within the file_path attribute path.
    The returned value removes the rest of the characters from the path.
    Example:
        "path/to/artifact_name.Notebook/notebook-content.py" -> "artifact_name"

    Args:
        file_path (str): The file path specified within the file_path attribute.
        path_pattern (re.Pattern): The regular expression pattern for the
            specified item types to look for.

    Returns:
        str | None: The stripped name of the found artifact or None if not found.
    """
    match: re.Match[str] | None = path_pattern.search(file_path)

    if match:
        return match.group(1).rsplit(".", 1)[0]

    return None


def _find_artifact_folders_recursively(
    base_path: Path,
    search_patterns: set[str],
    excluded_paths: set[Path],
) -> Generator[Path, None, None]:
    """
    Recursively searches for artifact folders in the specified base path
    matching the given search patterns and excluding specified paths.

    Args:
        base_path (Path): The base directory to start the search.
        search_patterns (set[str]): The patterns for matching artifact directories,
            the values are aligned with the desired types specified.
        excluded_paths (set[Path]): Paths to exclude from the search.

    Returns:
        Generator[Path, None, None]: Generator yielding found artifact names.
    """
    try:
        for item_path in base_path.iterdir():
            if item_path.is_dir():
                resolved_path = item_path.resolve()

                if resolved_path in excluded_paths:
                    continue

                if any(item_path.match(pattern) for pattern in search_patterns):
                    yield item_path

                yield from _find_artifact_folders_recursively(
                    item_path, search_patterns, excluded_paths
                )

    except (PermissionError, FileNotFoundError):
        pass


def _analyze_and_report_findings(
    elements_to_analyze: set[str],
    elements_to_substract: set[str],
    analysis_source: AnalysisSource,
) -> None:
    """
    Reports findings of artifacts not found in the project or YAML.
    Retrieves the specific configuration for each mode from REPORT_CONFIGS.

    Args:
        elements_to_analyze (set[str]): Set of artifacts to be analyzed.
        elements_to_substract (set[str]): Set of artifacts to be excluded from the analysis.
        analysis_source (AnalysisSource): Desired mode to perform the analysis.(1: YAML file_path, 2: YAML item_name, 3: Project)

    Raises:
        ValueError: Error raised when an invalid analysis mode is specified.
    """
    report_findings_config: ReportConfig | None = REPORT_CONFIGS.get(analysis_source)

    if not report_findings_config:
        logger.error(f"Invalid analysis mode specified {analysis_source=}.")
        raise ValueError(f"❌ Invalid artifact source specified {analysis_source=}.")

    comparison_results: set[str] = elements_to_analyze - elements_to_substract

    if comparison_results:
        logger.debug(report_findings_config.found_msg)
        for artifact in sorted(comparison_results):
            result_message: str = (
                f"{report_findings_config.result_start}{artifact}{report_findings_config.result_end}"
            )
            logger.log(report_findings_config.log_level, result_message)
    else:
        logger.info(report_findings_config.not_found_msg)


def _show_all_results(
    project_artifacts: set[str],
    yaml_file_paths: set[str],
    yaml_item_names: set[str],
    yaml_entire_artifacts: set[str],
) -> None:
    """
    Compares and reports discrepancies between YAML entries and project artifacts.
    Runs the _analyze_and_report_findings function for each case.

    Args:
        project_artifacts (set[str]): Artifact names found in the project path specified, filtered according to desired item types.
        yaml_file_paths (set[str]): file_path attribute entries found in the YAML.
        yaml_item_names (set[str]): item_name attribute entries found in the YAML.
        yaml_entire_artifacts (set[str]): Whole artifact names found in the YAML, contains both file_path and item_name unique entries.
    """
    # Compare each case and report findings
    # Feel free to comment/uncomment each scenario to see individual comparisons
    _analyze_and_report_findings(
        yaml_file_paths, project_artifacts, AnalysisSource.YAML_FILE_PATH
    )
    _analyze_and_report_findings(
        yaml_item_names, project_artifacts, AnalysisSource.YAML_ITEM_NAME
    )
    _analyze_and_report_findings(
        project_artifacts, yaml_entire_artifacts, AnalysisSource.PROJECT
    )


def run_yamlficator(
    project_workspace_path: Path,
    desired_artifact_types: set[str],
    excluded_relative_paths: set[str],
) -> None:
    """
    Runs the entire process of validation over the specificied project path.
    Starts from loading the parameter YAML file and analyzes its contents before showing the results.
    It makes use of the rest of inner functions as needed.

    Args:
        project_workspace_path (Path): The path to the workspace contents within the project.
        desired_artifact_types (set[str]): Desired artifact types to check for, the rest will be ignored.
        excluded_relative_paths (set[str]): Relative paths to exclude from the process.
    """
    logger.info(
        f"Starting validation process for '{project_workspace_path}\\parameter.yml'"
    )
    logger.info("Analysis restricted to the following item types:")
    logger.info(f"{desired_artifact_types}")
    if excluded_relative_paths:
        logger.info("The following paths will be excluded from the analysis:")
        for excluded_path in excluded_relative_paths:
            logger.info(f"{excluded_path}")
    else:
        logger.info("No paths will be excluded from the analysis.")

    parameter_yaml_data = _load_and_parse_yaml(project_workspace_path)

    # Obtain both replacement mode entries(find_replace, key_value_replace) from the parameter YAML
    # We only want those without a specified item_type or with a value within the defined scope
    combined_replacement_entries: list = [
        yaml_entry
        for yaml_entry in itertools.chain(
            parameter_yaml_data.get("find_replace", []),
            parameter_yaml_data.get("key_value_replace", []),
        )
        if yaml_entry.get("item_type") is None
        or yaml_entry.get("item_type") in desired_artifact_types
    ]

    # Obtain both item_name and file_path values from the previous combined entries
    # Wildcard and recursive path patterns are omitted for file_path entries
    items_pattern: str = "|".join(desired_artifact_types)
    path_pattern: re.Pattern = re.compile(rf"([^/*]+\.(?:{items_pattern}))")
    yaml_file_path_entries: Generator[str, None, None] = (
        artifact_name
        for yaml_entry in combined_replacement_entries
        for file_path in _get_yaml_entry_values(yaml_entry, "file_path")
        if (artifact_name := _get_file_path_artifact_name(file_path, path_pattern))
        is not None
    )
    yaml_item_name_entries: Generator[str, None, None] = (
        item_name
        for yaml_entry in combined_replacement_entries
        for item_name in _get_yaml_entry_values(yaml_entry, "item_name")
    )

    # Project existing artifacts considering exclusion path and desired item types specified
    excluded_absolute_paths: set[Path] = {
        project_workspace_path.joinpath(excluded_path).resolve()
        for excluded_path in excluded_relative_paths
    }
    artifact_search_tags: set[str] = {f"*.{item}" for item in desired_artifact_types}
    filtered_project_artifacts: Generator[Path, None, None] = (
        _find_artifact_folders_recursively(
            project_workspace_path, artifact_search_tags, excluded_absolute_paths
        )
    )
    # Remove extensions from paths obtained
    extension_replacements: dict[str, str] = {
        f".{item}": "" for item in desired_artifact_types
    }
    extension_pattern: re.Pattern = re.compile(
        "|".join(re.escape(key) for key in extension_replacements.keys())
    )
    artifact_names: Generator[str, None, None] = (
        extension_pattern.sub(
            lambda match: extension_replacements[match.group(0)], artifact.name
        )
        for artifact in filtered_project_artifacts
        if artifact.is_dir()
    )

    # Generators can just be called once, so we must "persist" some of them
    yaml_file_paths: set[str] = set(yaml_file_path_entries)
    yaml_item_names: set[str] = set(yaml_item_name_entries)
    yaml_entire_artifacts: set[str] = yaml_item_names | yaml_file_paths
    _show_all_results(
        project_artifacts=set(artifact_names),
        yaml_file_paths=yaml_file_paths,
        yaml_item_names=yaml_item_names,
        yaml_entire_artifacts=yaml_entire_artifacts,
    )
    logger.info(
        f"Finished validation process for '{project_workspace_path}\\parameter.yml'"
    )
