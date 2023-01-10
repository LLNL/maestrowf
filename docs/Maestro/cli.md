# Command Line Interface
---

Installing Maestro will add two entry points/console scripts that are used for running, creating, and interacting with studies:

* `maestro`
    
    This is the primary user interface for creating, launching, and monitoring studies.
    
* `conductor`

    This is the background process that Maestro launches which does the actual orchestration and running of the studies and lives until the study execution is complete.
    
    
## **maestro**

The Maestro Workflow Conductor for specifying, launching, and managing general workflows.

**Usage:**

``` console
maestro [OPTIONS] COMMAND [ARGS]...
```

**Options:**

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `-h`, `--help` | boolean | Show this help message and exit. | `False` |
| `-l`, `--logpath` | filename | Alternate path to store program logging. | <study_name\>.log |
| `-d`, `--debug_lvl` | choice (`1` &#x7C; `2` &#x7C; `3` &#x7C; `4` &#x7C; `5`) | Level of logging messages to be output.  Smaller choice produces more output. <table>  <thead>  <th>Choice</th>  <th>Max Debug Level</th>  </tr>  </thead>  <tbody>  <tr>  <td>5</td>  <td>Critical</td>  </tr>  <tr>  <td>4</td>  <td>Error</td>  </tr>  <tr>  <td>3</td>  <td>Warning</td>  </tr>  <tr>  <td>2</td>  <td>Info (Default)</td>  </tr> <tr> <td>1</td> <td>Debug</td>  </tbody>  </table>               | 2 |
| `-c`, `--logstdout` | boolean | Log to stdout in addition to a file.  **NOTE:** This only controls immediate output from `maestro` during the setup phase.  Once `conductor` is launched and the study is running this log info goes to file only if not running in the foreground | `True` | <!-- insert link to the foreground/background option -->
| `-v`, `--version` | boolean | Show program's version number and exit. | `False` |


**Subcommands**

- [*cancel*](#cancel): Cancel all running jobs.
- [*run*](#run): Launch a study based on a specification
- [*status*](#status): Check the status of a running study.

### **cancel**

Cancel all running jobs in every given study directory.

**Usage:**

``` console
maestro cancel [OPTIONS] DIRECTORY [DIRECTORY ...]
```

**Options:**

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `-h`, `--help` | boolean | Show this help message and exit. | `False` |


### **run**

Entry point for launching a study described in a YAML based study specification <!-- add link to this specification? -->

**Usage:**

``` console
maestro run [OPTIONS] SPECIFICATION
```

**Options:**

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `-h`, `--help` | boolean | Show this help message and exit. | `False` |
| `-a`, `--attempts` | integer | Maximum number of submission attempts before a step is marked failed. | 1 |
| `-r`, `--rlimit` | integer | Maximum number of restarts allowed when steps specify a restart command. (0 denotes no limit)| 1 |
| `-t`, `--throttle` | integer | Maximum number of inflight jobs allowed to execute simultaneously (0 denotes not throttling) | 0 |
| `-s`, `--sleeptime` | integer | Amount of time (in seconds) for the manager to wait between job status checks. | 60 |
| `--dry` | boolean | Generate the directory structure and scripts for a study but do not launch it. | `False` |
| `-p`, `--pgen` | filename/path | Path to a Python code file containing a function that returns a custom filled ParameterGenerator instance. | None |
| `--pargs` | string | A string that represents a single argument to pass a custom parameter generation function. Reuse '--parg' to pass multiple arguments. [Use with '--pgen'] | None |
| `-o`, `--out` | path | Output path to place study in. [NOTE: overrides OUTPUT_PATH in the specified specification] | "<study name\>_timestamp" |
| `-fg` | boolean | Runs the backend conductor in the foreground instead of using nohup. | `False` |
| `--hashws` | boolean | Enable hashing of subdirectories in parameterized studies (NOTE: breaks commands that use parameter labels to search directories). | `False` |
| `-n`, `--autono` | boolean | Automatically answer no to input prompts. | `False` |
| `-y`, `--autoyes` | boolean | Automatically answer yes to input prompts. | `False` |
| `--usetmp` | boolean | Make use of a temporary directory for dumping scripts and other Maestro related files. | `False` |


### **status**

Check the status of each given running or completed study.

**Usage:**

``` console
maestro status [OPTIONS] DIRECTORY [DIRECTORY ...]
```

**Options:**

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `-h`, `--help` | boolean | Show this help message and exit. | `False` |
| `--layout` | choice (`flat` &#x7C; `legacy` &#x7C; `narrow`) | Alternate status table layouts. | `flat` |


## **conductor**

A application for checking and managing and ExecutionDAG within an executing study.

**Usage:**

``` console
conductor [OPTIONS] DIRECTORY
```

**Options:**

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `-h`, `--help` | boolean | Show this help message and exit. | `False` |
| `-s`, `--status` | path |  Check the status of the ExecutionGraph located as specified by the 'directory' argument. | None |
| `-l`, `--logpath` | filename | Alternate path to store program logging. | <study_name\>.log |
| `-d`, `--debug_lvl` | choice (`1` &#x7C; `2` &#x7C; `3` &#x7C; `4` &#x7C; `5`) | Level of logging messages to be output.  Smaller choice produces more output. <table>  <thead>  <th>Choice</th>  <th>Max Debug Level</th>  </tr>  </thead>  <tbody>  <tr>  <td>5</td>  <td>Critical</td>  </tr>  <tr>  <td>4</td>  <td>Error</td>  </tr>  <tr>  <td>3</td>  <td>Warning</td>  </tr>  <tr>  <td>2</td>  <td>Info (Default)</td>  </tr> <tr> <td>1</td> <td>Debug</td>  </tbody>  </table>               | 2 |
| `-c`, `--logstdout` | boolean | Log to stdout in addition to a file.  **NOTE:** This only controls immediate output from `maestro` during the setup phase.  Once `conductor` is launched and the study is running this log info goes to file only if not running in the foreground | `True` | <!-- insert link to the foreground/background option -->
| `-s`, `--sleeptime` | integer | Amount of time (in seconds) for the manager to wait between job status checks. | 60 |



