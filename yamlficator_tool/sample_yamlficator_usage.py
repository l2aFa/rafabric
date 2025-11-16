# Licensed under the MIT License.

# The following is intended for developers using the fabric-cicd library for fabric cicd deployments,
# hoping that it will help them ensure correct implementations and save time in the face of potential errors ;)

import logging
from pathlib import Path

# Custom module for the tool
from yamlficator import run_yamlficator

# Replace with the path from your own project
# The file parameter.yml must be located within this path
"""Example:
    sample_project_name
    ├── src
    │   └── workspaces
    │       └── sample_workspace
    │           ├── sample_artifact_01.Notebook
    │           ├── Group_01
    │           │   ├──sample_artifact_02.Report
    │           ├── ...
    │           └── parameter.yml
"""
project_workspace_path: Path = Path("src/workspaces/sample_workspace")

# Set the artifact types to check for
# Find supported item types at: https://microsoft.github.io/fabric-cicd/latest/#supported-item-types
desired_artifact_types: set[str] = {
    "Notebook",
    "Report",
    "SemanticModel",
    "VariableLibrary",
}

# Set any relative paths to exclude from the search
# This is entirely optional and can be modified as needed, you can leave it empty using set()
# You should align it with paths containing artifacts not intended/needed
# to be referenced inside parameter.yml in order to avoid false positives
excluded_relative_paths: set[str] = {
    "sample_route_01",
    "sample_route_02/sample_subfolder_01",
    "sample_route_03/sample_subfolder_02/sample_subsubfolder_01",
}


def run_yamlficator_analysis(
    project_workspace_path: Path,
    desired_artifact_types: set[str],
    excluded_relative_paths: set[str],
) -> None:
    """
    This function serves as the main entry point for the `yamlficator` tool.
    It orchestrates the validation process by calling `run_yamlficator` after performing
    an initial check to ensure the provided `project_workspace_path` exists.
    Makes use of the previously defined variables.

    Args:
        project_workspace_path (Path): The path to the workspace contents within the project.
        desired_artifact_types (set[str]): Desired artifact types to check for, the rest will be ignored.
        excluded_relative_paths (set[str]): Relative paths to exclude from the process.

    Raises:
        FileNotFoundError: Error raised when the specified path is not found.

    Returns:
        None
    """
    logger = logging.getLogger("yamlficator")

    if not project_workspace_path.is_dir():
        logger.error(f"Specified path '{project_workspace_path}' was not found.")
        raise FileNotFoundError(
            f"❌ Error: Specified path '{project_workspace_path}' was not found."
        )
    else:
        run_yamlficator(
            project_workspace_path, desired_artifact_types, excluded_relative_paths
        )


if __name__ == "__main__":
    run_yamlficator_analysis(
        project_workspace_path, desired_artifact_types, excluded_relative_paths
    )
