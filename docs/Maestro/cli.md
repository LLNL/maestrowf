# Command Line Interface
---

Installing Maestro will add two entry points/console scripts that are used for running, creating, and interacting with studies:

* [`maestro`](#maestro)
    
    This is the primary user interface for creating, launching, and monitoring studies.
    
* [`conductor`](#conductor)

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
| `-d`, `--debug_lvl` | choice (`1` &#x7C; `2` &#x7C; `3` &#x7C; `4` &#x7C; `5`) | Level of logging messages to be output.  Smaller choice produces more output. <table>  <thead>  <th>Choice</th>  <th>Max Debug Level</th>  </thead>  <tbody>  <tr>  <td>5</td>  <td>Critical</td>  </tr>  <tr>  <td>4</td>  <td>Error</td>  </tr>  <tr>  <td>3</td>  <td>Warning</td>  </tr>  <tr>  <td>2</td>  <td>Info (Default)</td>  </tr> <tr> <td>1</td> <td>Debug</td>  </tbody>  </table>               | 2 (Info) |
| `-c`, `--logstdout` | boolean | Log to stdout in addition to a file.  **NOTE:** This only controls immediate output from `maestro` during the setup phase.  Once `conductor` is launched and the study is running this log info goes to file only if not running in the foreground | `True` | <!-- insert link to the foreground/background option -->
| `-v`, `--version` | boolean | Show program's version number and exit. | `False` |


**Subcommands**

- [*cancel*](#cancel): Cancel all running jobs.
- [*run*](#run): Launch a study based on a specification
- [*status*](#status): Check the status of a running study.
- [*update*](#update): Update a running study

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
| `--layout` | choice (`flat` &#x7C; `legacy` &#x7C; `narrow`) | Alternate status table layouts. See [Status Layouts](monitoring.md#status-layouts) for description of these options| `flat` |
| `--disable-theme` | boolean | Turn off styling for the status layout. See [Status Theme](monitoring.md#status-theme) for more information on this option. | `False` |
| `--disable-pager` | boolean | Turn off the pager for the status display. See [Status Pager](monitoring.md#status-pager) for more information on this option. | `False` |


### **update**

Update the config of a running study.  Currently limited to three settings: throttle, restart limit (rlimit), and sleep.  Explicitly set each argument via keyword args, interactively set for each study, or a mix of the two. Supports updating multiple studies at once.

!!! note

    This command will drop a hidden file in your study workspace '.study.update.lock' which conductor reads asynchronously and removes upon successful reading.  Applying this command to a finished study will currently leave this file in your workspace.  Similarly, this file will also not be cleaned up if conductor crashes before reading.

**Usage:**

``` console
maestro update [-h] [--rlimit RLIMIT] [--sleep SLEEP] [--throttle THROTTLE] DIRECTORY [DIRECTORY ...]
```

**Options:**

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `-h`, `--help` | boolean | Show this help message and exit. | `False` |
| `--rlimit` | integer | Update maximum number of restarts when steps specify a restart command (0 denotes no limit) | None |
| `--sleep` | integer  | Update the time (in seconds) that the manager (conductor) will wait between job status checks. | None |
| `--throttle` | integer  | Update the maximum number of inflight jobs allowed to execute simultaneously (0 denotes no throttling). | None |


#### **Examples**

**Update a single study configuration value for a single study:**

``` console title="Change single config value for a single study"
maestro update --rlimit 4 /path/to/my/timestamped/study/workspace/
```

**Update multiple study configuration values for a single study:**

``` console title="Change multiple config values for a single study"
maestro update --rlimit 4 --throttle 2 /path/to/my/timestamped/study/workspace/
```
**Update single study configuration value for multiple studies:**

``` console title="Single config value, two studies"
maestro update --rlimit 4 --rlimit 2 /path/to/my/timestamped/study/workspace_1/ /path/to/my/timestamped/study/workspace_2/
```

**Update multiple study configuration values for multiple studies:**

``` console title="Multiple config values, two studies"
maestro update --rlimit 4 --rlimit 2 /path/to/my/timestamped/study/workspace_1/ /path/to/my/timestamped/study/workspace_2/
```

**Interactively update study configuration for one study:**

<!-- termynal -->
```
$ maestro update ./sample_output/hello_world_restart/hello_bye_world_20241119-173122
Updating study at '/path/to/sample_output/hello_world_restart/hello_bye_world_20241119-173122'
Choose study config to update, or done/quit to finish/abort
[rlimit/throttle/sleep/done/quit]
> rlimit
Enter new restart limit [Integer, 0 = unlimited]
> 4
Choose study config to update, or quit
 [rlimit/throttle/sleep/done/quit]
> sleep
Enter new sleep duration for Conductor [Integer, seconds]
> 30
Choose study config to update, or quit
 [rlimit/throttle/sleep/done/quit]
> quit
Discarding updates to 'sample_output/hello_world_restart/hello_bye_world_20241119-173122/'
$ maestro update ./sample_output/hello_world_restart/hello_bye_world_20241119-173122
Updating study at '/path/to/sample_output/hello_world_restart/hello_bye_world_20241119-173122'
Choose study config to update, or done/quit to finish/abort
[rlimit/throttle/sleep/done/quit]
> rlimit
Enter new restart limit [Integer, 0 = unlimited]
> 4
Choose study config to update, or quit
 [rlimit/throttle/sleep/done/quit]
> done
Writing updated study config to 'sample_output/hello_world_restart/hello_bye_world_20241119-173122/.study.update.lock'
```

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
| `-d`, `--debug_lvl` | choice (`1` &#x7C; `2` &#x7C; `3` &#x7C; `4` &#x7C; `5`) | Level of logging messages to be output.  Smaller choice produces more output. <table>  <thead>  <th>Choice</th>  <th>Max Debug Level</th> </thead>  <tbody>  <tr>  <td>5</td>  <td>Critical</td>  </tr>  <tr>  <td>4</td>  <td>Error</td>  </tr>  <tr>  <td>3</td>  <td>Warning</td>  </tr>  <tr>  <td>2</td>  <td>Info (Default)</td>  </tr> <tr> <td>1</td> <td>Debug</td>  </tbody>  </table>               | 2 (Info) |
| `-c`, `--logstdout` | boolean | Log to stdout in addition to a file.  **NOTE:** This only controls immediate output from `maestro` during the setup phase.  Once `conductor` is launched and the study is running this log info goes to file only if not running in the foreground | `True` | <!-- insert link to the foreground/background option -->
| `-s`, `--sleeptime` | integer | Amount of time (in seconds) for the manager to wait between job status checks. | 60 |



