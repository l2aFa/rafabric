# **🚀 yamlficator 🚀**
![language](https://img.shields.io/badge/language-Python-brightgreen)
![license](https://img.shields.io/badge/license-MIT-green)

Validation tool for CICD deployments within Microsoft Fabric using the [fabric-cicd library](https://microsoft.github.io/fabric-cicd/latest/).

You can read more about it on Medium:
* [English version](https://medium.com/@baggirraf/searching-for-a-needle-in-a-haystack-facilitating-deployments-with-fabric-cicd-c591fec3e478)
* [Spanish version](https://medium.com/@baggirraf/buscando-la-aguja-en-el-pajar-facilitando-despliegues-con-fabric-cicd-fa967f1d0fce)

This is not a replacement for the existing library; it is a complement when validating the content of the parameterization file and locating existing elements in the project that are not included in it. It does not deploy any content.

yamlficator can be used in conjunction with [the existing validator](https://github.com/microsoft/fabric-cicd/blob/main/devtools/debug_parameterization.py) or independently.

The code includes comments and definitions for each of the defined elements. Please let me know if anything is incorrect.

Hope you find it useful 😃

---

## 1️⃣ Prerequisites:
* Include the [yamlficator](https://github.com/l2aFa/rafabric/blob/main/yamlficator_tool/yamlficator.py) file inside your project.
* Install the PyYAML required library (the use of a virtual environment is recommended): `pip install pyyaml` <br>
This is the only non-standard library used by the tool, the rest should be available as Python built-ins.
* Include the [sample_yamlficator_usage](https://github.com/l2aFa/rafabric/blob/main/yamlficator_tool/sample_yamlficator_usage.py) file inside your project or rename it/create your own following its example.
* Configure the repository directory path, desired item types and exclusion paths (if needed). This should be aligned with your replacement strategy defined within the parameter.yml file.


## 2️⃣ Contents:
* [sample_yamlficator_usage.py](https://github.com/l2aFa/rafabric/blob/main/yamlficator_tool/sample_yamlficator_usage.py): Example of using the tool from a separate file. Includes path validation checks and logging. </br>It can be invoked directly from the terminal once included in the project (make sure you are at the correct path): `python sample_yamlficator_usage.py`
* [yamlficator.py](https://github.com/l2aFa/rafabric/blob/main/yamlficator_tool/yamlficator.py): Module content. Includes the classes, logging configuration and functions that conform the validation process, which can be adjusted as needed. For the moment, everything is in the same file for simplicity reasons.

---

## 3️⃣ Need to know:
* Each execution overwrites the log file if it exists:
    * Console logging is configured at the `DEBUG` level and color-coded.
    * File logging is configured at the `INFO` level.
* `file_path` invalid entries are reported as errors, you should fix them before trying the deployment.
    * The process excludes and ignores paths using wildcard patterns (*) inside the `file_path` attribute.
    * These paths, if correct, should be defined as exclusion path. You can also check them with the [official validation tool](https://github.com/microsoft/fabric-cicd/blob/main/devtools/debug_parameterization.py).
* `item_name` invalid entries are reported as warnings, it is recommended to fix them because, although they will not cause the deployment to fail, they may cause errors later once they are executed.
* Project artifacts not found in the parameter.yml are reported as warnings as well. This is not an issue as such, but it should be reviewed to see if any of them (or their path) need to be included in the process. If they are false positives, it is recommended to configure them as excluded paths.