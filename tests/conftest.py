from collections import defaultdict
import difflib
import fnmatch
import json
import logging
import os
from pathlib import Path
import re
import shutil
from subprocess import check_output
import subprocess
from typing import Any, Dict, Iterable, List, Optional, Pattern, Union

import pprint
import pytest

from maestrowf.datastructures.core import Study
from maestrowf.datastructures.environment import Variable
from maestrowf.specification import YAMLSpecification
from maestrowf.utils import (
    create_parentdir,
    LoggerUtility,
    make_safe_path,
    parse_version
)

from packaging.version import InvalidVersion

# Hypothesis profiles
from hypothesis import settings

#  Profile for local development using default deadlines
settings.register_profile("local", deadline=200, max_examples=100)

#  Profile for CI with relaxed deadlines to handle system variability
settings.register_profile("ci", deadline=1000, max_examples=100)

#  Auto-detect and load correct profile
if os.getenv("CI") == "true":
    settings.load_profile("ci")
else:
    settings.load_profile("local")
    

# Check for active schedulers to enable/disable appropriate tests
SCHEDULERS = set(('sched_lsf', 'sched_slurm', 'sched_flux', 'sched_local'))
SCHED_CHECKS = defaultdict(lambda: False)


def check_lsf():
    """
    Checks if there is an lsf instance to schedule to. NOT IMPLEMENTED YET.
    """
    return False


SCHED_CHECKS['sched_lsf'] = check_lsf


def check_slurm():
    """
    Checks if there is a slurm instance to schedule to.
    """
    slurm_info_func = 'sinfo'
    try:
        slurm_ver_output_lines = check_output([slurm_info_func,'-V'], encoding='utf8')
    except FileNotFoundError as fnfe:
        if fnfe.filename == slurm_info_func:
            return False

        raise

    slurm_ver_parts = slurm_ver_output_lines.split('\n')[0].split()

    try:
        version = parse_version(slurm_ver_parts[1])
    except InvalidVersion:
        # This can happen when encountering LLNL's slurm wrappers for flux machines
        print(f"Error extracting SLURM version from 'sinfo' output: {slurm_ver_output_lines} does not have a version in the expected location, item 0: {slurm_ver_parts}")
        return False

    if slurm_ver_parts[0].lower() == 'slurm' and version:
        return True

    return False


SCHED_CHECKS['sched_slurm'] = check_slurm


def check_flux():
    """
    Checks if there is a flux scheduler to schedule to.

    Returns
    -------
    True if flux bindings installed and active broker found, False if not
    """
    try:
        import flux

        fhandle = flux.Flux()

    except ImportError:
        # Flux bindings not found
        return False

    except FileNotFoundError:
        # Couldn't connect to a broker
        return False

    return True


SCHED_CHECKS['sched_flux'] = check_flux


def check_local():
    """
    Dummy check for the local scheduler which should always be present.

    Returns
    -------
    True
    """
    return True


SCHED_CHECKS['sched_local'] = check_local


def check_for_scheduler(sched_name):
    """
    Thin wrapper for dispatching scheduler presence testing for marking
    tests to be skipped
    """
    return SCHED_CHECKS[sched_name]()


def pytest_runtest_setup(item):
    """Helper for applying automated test marking"""
    # Scheduler dependent checks
    for marker in item.iter_markers():
        if not marker.name.startswith('sched_'):
            continue

        if marker.name not in SCHEDULERS:
            pytest.skip(f"'{marker}' is not a supported scheduler")

        print(f"CHECKING IF ON SCHEDULER: {marker.name}")
        if not check_for_scheduler(marker.name):

            pytest.skip(f"not currently running tests on '{marker}' managed system")


@pytest.fixture
def samples_spec_path():
    """
    Fixture for providing maestro specifications from the samples
    directories
    """
    def load_spec(file_name):
        samples_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'samples'
        )

        for dirpath, dirnames, filenames in os.walk(samples_dir):
            for fname in filenames:
                if file_name == fname:
                    return os.path.join(dirpath, file_name)

    return load_spec


@pytest.fixture
def spec_path():
    """
    Fixture for providing maestro specifications from test data directories
    """
    def load_spec(file_name):
        dirpath = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirpath, "specification", "test_specs", file_name)

    return load_spec


@pytest.fixture
def status_csv_path():
    """Fixture for providing status files from test data directories"""
    def load_status_csv(file_name):
        dirpath = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirpath, "status", "test_status_data", file_name)

    return load_status_csv


@pytest.fixture
def data_dir():
    """Base directory for top level shared test data."""
    return Path(__file__).parent / "data"


@pytest.fixture
def variant_expected_output(data_dir):
    def _load_variant_expected_output(expected_output_name):
        return data_dir / "expected_spec_outputs" / expected_output_name

    return _load_variant_expected_output


@pytest.fixture
def variant_spec_path(data_dir):
    """Utility fixture to load yaml spec's from top level shared test data"""
    def _load_variant_spec(spec_name):
        # Not loading it here: defer to yamlspecification..
        return data_dir / "specs" / spec_name
    return _load_variant_spec


@pytest.fixture
def load_study():
    """Fixture to provide an unexecuted study object"""
    def _load_study(spec_path, output_path, dry_run=False):

        # Setup some default args to use for testing
        use_tmp_dir = False          # NOTE: likely want to let pytest control this?
        hash_ws = False
        throttle = 0
        submission_attempts = 3
        restart_limit = 1

        # Load the Specification
        spec = YAMLSpecification.load_specification(spec_path)

        environment = spec.get_study_environment()
        steps = spec.get_study_steps()

        # Set up the output directory.
        out_dir = environment.remove("OUTPUT_PATH")

        pprint.pprint(f"LOAD_STUDY: {str(out_dir)}, {output_path=}")
        if output_path:
            # If out is specified in the args, ignore OUTPUT_PATH.
            output_path = os.path.abspath(output_path)
        else:
            if out_dir is None:
                # If we don't find OUTPUT_PATH in the environment, assume pwd.
                out_dir = os.path.abspath("./")
            else:
                # We just take the value from the environment.
                out_dir = os.path.abspath(out_dir.value)

            out_name = spec.name.replace(" ", "_")
            # NOTE: shouldn't need timestamp for testing; omitting for now
            # out_name = "{}_{}".format(
            #     spec.name.replace(" ", "_"),
            #     time.strftime("%Y%m%d-%H%M%S")
            # )
            output_path = make_safe_path(out_dir, *[out_name])
        environment.add(Variable("OUTPUT_PATH", output_path))

        pprint.pprint(f"LOAD_STUDY: post-output_path resolution: {output_path=}")
        # Set up file logging
        create_parentdir(os.path.join(output_path, "logs"))
        output_path = Path(output_path)
        log_path = output_path / "logs" / "{}.log".format(spec.name)
        # log_path = os.path.join(output_path, "logs", "{}.log".format(spec.name))
        # TODO: revisit this logger/name -> don't use __name__ as in maestro.py?
        LOGGER = logging.getLogger()
        LOG_UTIL = LoggerUtility(LOGGER)
        LFORMAT = "[%(asctime)s: %(levelname)s] %(message)s"
        LOG_UTIL.add_file_handler(log_path, LFORMAT, 2)  # INFO level

        # Addition of the $(SPECROOT) to the environment.
        spec_root = os.path.split(spec_path)[0]
        spec_root = Variable("SPECROOT", os.path.abspath(spec_root))
        environment.add(spec_root)

        # Don't wire up pgen for now.
        parameters = spec.get_parameters()

        # Setup the study.
        study = Study(spec.name, spec.description, studyenv=environment,
                      parameters=parameters, steps=steps, out_path=output_path)

        # Set up the study workspace and configure it for execution.
        study.setup_workspace()
        study.configure_study(
            throttle=throttle,
            submission_attempts=submission_attempts,
            restart_limit=restart_limit,
            use_tmp=use_tmp_dir,
            hash_ws=hash_ws,
            dry_run=dry_run)
        study.setup_environment()

        batch = {"type": "local"}
        if spec.batch:
            batch = spec.batch
            if "type" not in batch:
                batch["type"] = "local"

        # Copy the spec to the output directory
        shutil.copy(spec_path, study.output_path)

        # Use the Conductor's classmethod to store the study.
        # Conductor.store_study(study)
        # Conductor.store_batch(study.output_path, batch)

        return study

    return _load_study


@pytest.fixture
def text_diff():
    """
    Fixture to diff two text streams, ignoring lines that match any pattern in
    optional ignore_patterns.  Ignore patterns are a list of regexes.
    """
    def _diff(actual, expected, ignore_patterns=None):
        """
        Compare two text streams, ignoring lines matching any ignore_patterns.
        Text streams are assumed to not be split on line endings yet.

        :param actual: The actual text output (str)
        :param expected: The expected text (str)
        :param ignore_patterns: List of regex patterns to ignore/whitelist (optional)
        :raises AssertionError: If the filtered texts do not match
        """
        if ignore_patterns is None:
            ignore_patterns = []

        def line_matches(line):
            return [re.search(pattern, line) for pattern in ignore_patterns]
        
        def filter_lines(lines):
            for line in lines:
                if any(line_matches(line)):
                    continue
                yield line

        actual_lines = actual.splitlines()
        if actual_lines and actual_lines[-1].strip() == "":
            actual_lines.pop()
        expected_lines = expected.splitlines()
        if expected_lines and expected_lines[-1].strip() == "":
            expected_lines.pop()

        def annotate_ignored_lines(lines_to_annotate):
            for line in lines_to_annotate:
                if any(line_matches(line)):
                    yield f"IGNORED: {line}"
                else:
                    yield line

        actual_filtered_lines = list(filter_lines(actual_lines))

        expected_filtered_lines = list(filter_lines(expected_lines))

        if actual_filtered_lines != expected_filtered_lines:
            actual_annotated_lines = list(annotate_ignored_lines(actual_lines))

            expected_annotated_lines = list(annotate_ignored_lines(expected_lines))

            diff = list(
                difflib.unified_diff(
                    expected_annotated_lines,
                    actual_annotated_lines,
                    fromfile="expected",
                    tofile="actual",
                    lineterm=""
                )
            )

            diff = "\n".join(diff)
            raise AssertionError(f"Text streams differ (ignoring marked lines):\n{diff}")

        return True

    return _diff


@pytest.mark.sched_flux
@pytest.fixture
def flux_jobspec_check(request):
    import flux

    def _diff_jobspec_keys(
        jobid,
        expected,
        path=None,
        source_label=None,
        list_matcher=None,
        ignore_keys=None,
        debug=False,
        debug_log=None,
    ):
        """
        Verify that 'expected' is a subset of the actual flux jobspec, with support for:
          - Ignoring specific keys/indices via ignore_keys (paths, names, or predicate(s))
          - Multiple ignore predicates or path specs
          - Optional debugging trace

        Parameters:
          - jobid: flux job id
          - expected: nested structure of expected keys/values
          - path: initial dict path to descend before comparing
          - source_label: label for error messages
          - list_matcher: optional matcher callable for unordered list of dicts
          - ignore_keys: None, single spec, or list/tuple of specs:
              * dotted path strings, e.g. "tasks.0.command.3"
              * tuples of raw segments, e.g. ("tasks", 0, "command", 3)
              * sets/lists of simple key names, e.g. {"timestamp", "uuid"}
              * callable predicate(raw_path, key_or_index, actual_value) -> bool
            Any spec that returns True will cause that key/index to be skipped.
          - debug: True to enable verbose ignore diagnostics
          - debug_log: optional callable(msg). Defaults to print if debug is True.

        Assumptions:
          - Top-level jobspec is a dict.
        """
        fh = flux.Flux()
        jobspec = flux.job.job_kvs_lookup(
            fh, flux.job.JobID(jobid), decode=True, original=False
        ).get("jobspec")

        prefix = f"[{source_label}] " if source_label else ""

        # Build composite ignore predicate with debugging
        ignore_pred = build_ignore_predicate(ignore_keys, debug=debug, debug_log=debug_log)
        # pprint.pprint(f"[flux_jobspec_check]: id(ignore_pred) = {id(ignore_pred)}")
        def fmt_path(pretty_segments):
            return ".".join(pretty_segments) if pretty_segments else "<root>"

        def assert_equal_scalar(actual, expected, raw_path, pretty_path):
            assert actual == expected, (
                f"{prefix}Value mismatch at {fmt_path(pretty_path)}: "
                f"expected {expected!r}, got {actual!r}"
            )

        def assert_dict_subset(actual_dict, expected_dict, raw_path, pretty_path):
            assert isinstance(actual_dict, dict), (
                f"{prefix}Expected dict at {fmt_path(pretty_path)}, "
                f"got {type(actual_dict).__name__}"
            )
            for key, expected_value in expected_dict.items():
                # Ignore check with raw context
                # pprint.pprint(f"[flux_jobspec_check][assert_dict_subset]: id(ignore_pred) = {id(ignore_pred)}")
                if ignore_pred(raw_path, key, actual_dict.get(key, None), pretty_path):
                    continue

                raw_next = raw_path + (key,)
                pretty_next = pretty_path + [repr(key)]
                assert key in actual_dict, f"{prefix}Missing key at {fmt_path(pretty_next)}"
                actual_value = actual_dict[key]
                assert_nested_subset(actual_value, expected_value, raw_next, pretty_next)

        def assert_list_positional_subset(actual_list, expected_list, raw_path, pretty_path):
            assert isinstance(actual_list, list), (
                f"{prefix}Expected list at {fmt_path(pretty_path)}, "
                f"got {type(actual_list).__name__}"
            )
            for i, item in enumerate(expected_list):
                if item is ...:
                    continue

                # pprint.pprint(f"[flux_jobspec_check][assert_list_positional_subset]: id(ignore_pred) = {id(ignore_pred)}")
                actual_val = actual_list[i] if i < len(actual_list) else None
                if ignore_pred(raw_path, i, actual_val, pretty_path):
                    continue
                # else:
                #     pprint.pprint(f"[ignore-pred]: not ignoring: {raw_path=} {i=} {actual_val=} {pretty_path=}")

                assert i < len(actual_list), (
                    f"{prefix}List index out of range at {fmt_path(pretty_path)}[{i}]: "
                    f"actual length {len(actual_list)}"
                )
                assert_nested_subset(actual_list[i], item, raw_path + (i,), pretty_path + [f"[{i}]"])

        def assert_list_unordered_subset(actual_list, expected_list, raw_path, pretty_path):
            assert isinstance(actual_list, list), (
                f"{prefix}Expected list at {fmt_path(pretty_path)}, "
                f"got {type(actual_list).__name__}"
            )
            # pprint.pprint(f"[flux_jobspec_check][assert_list_unordered_subset]: id(ignore_pred) = {id(ignore_pred)}")
            available_indices = [
                i for i in range(len(actual_list))
                if not ignore_pred(raw_path, i, actual_list[i], pretty_path)
            ]

            def consume(idx):
                try:
                    available_indices.remove(idx)
                    return True
                except ValueError:
                    return False

            for i, exp_item in enumerate(expected_list):
                if exp_item is ...:
                    continue

                matched_idx = None
                # Try matcher first
                if callable(list_matcher):
                    idx = list_matcher(actual_list, exp_item, pretty_path)
                    if idx is not None and idx in available_indices:
                        matched_idx = idx

                # Fallback search
                if matched_idx is None:
                    for idx in list(available_indices):
                        try:
                            assert_nested_subset(
                                actual_list[idx], exp_item,
                                raw_path + (idx,), pretty_path + [f"[{idx}]"]
                            )
                            matched_idx = idx
                            break
                        except AssertionError:
                            continue

                assert matched_idx is not None, (
                    f"{prefix}No matching list element for expected item at "
                    f"{fmt_path(pretty_path)}[{i}]"
                )
                assert consume(matched_idx), (
                    f"{prefix}Internal error, matched index {matched_idx} could not be consumed at "
                    f"{fmt_path(pretty_path)}[{i}]"
                )

        def assert_tuple_unordered_subset(actual_tuple, expected_tuple, raw_path, pretty_path):
            assert isinstance(actual_tuple, tuple), (
                f"{prefix}Expected tuple at {fmt_path(pretty_path)}, "
                f"got {type(actual_tuple).__name__}"
            )
            # pprint.pprint(f"[flux_jobspec_check][assert_tuple_unordered_subset]: id(ignore_pred) = {id(ignore_pred)}")
            available_indices = [
                i for i in range(len(actual_tuple))
                if not ignore_pred(raw_path, i, actual_tuple[i], pretty_path)
            ]

            def consume(idx):
                try:
                    available_indices.remove(idx)
                    return True
                except ValueError:
                    return False

            for i, exp_item in enumerate(expected_tuple):
                matched_idx = None
                for idx in list(available_indices):
                    try:
                        assert_nested_subset(
                            actual_tuple[idx], exp_item,
                            raw_path + (idx,), pretty_path + [f"({idx})"]
                        )
                        matched_idx = idx
                        break
                    except AssertionError:
                        continue
                assert matched_idx is not None, (
                    f"{prefix}No matching tuple element for expected item at "
                    f"{fmt_path(pretty_path)}({i})"
                )
                assert consume(matched_idx), (
                    f"{prefix}Internal error, matched tuple index {matched_idx} could not be consumed at "
                    f"{fmt_path(pretty_path)}({i})"
                )

        def assert_nested_subset(actual, expected, raw_path, pretty_path):
            if isinstance(expected, dict):
                return assert_dict_subset(actual, expected, raw_path, pretty_path)
            if isinstance(expected, list):
                if callable(list_matcher):
                    return assert_list_unordered_subset(actual, expected, raw_path, pretty_path)
                return assert_list_positional_subset(actual, expected, raw_path, pretty_path)
            if isinstance(expected, tuple):
                return assert_tuple_unordered_subset(actual, expected, raw_path, pretty_path)
            return assert_equal_scalar(actual, expected, raw_path, pretty_path)

        try:
            assert isinstance(jobspec, dict), (
                f"{prefix}Top-level jobspec is not a dict, got {type(jobspec).__name__}"
            )
            actual_root = jobspec
            raw_path = tuple()
            pretty_path = []

            # Descend initial path
            if path:
                for segment in path:
                    # If this segment is ignored, stop descending and compare at current level
                    # pprint.pprint(f"[flux_jobspec_check][main]: id(ignore_pred) = {id(ignore_pred)}")
                    if ignore_pred(raw_path, segment, actual_root.get(segment, None), pretty_path):
                        break
                    assert isinstance(actual_root, dict), (
                        f"{prefix}Expected dict while walking path at {fmt_path(pretty_path)}, "
                        f"got {type(actual_root).__name__}"
                    )
                    assert segment in actual_root, (
                        f"{prefix}Missing key while walking path at {fmt_path(pretty_path + [repr(segment)])}"
                    )
                    actual_root = actual_root[segment]
                    raw_path += (segment,)
                    pretty_path.append(repr(segment))

            assert_nested_subset(actual_root, expected, raw_path, pretty_path)

        except AssertionError:
            jobspec_str = pprint.pformat(jobspec, width=100)
            expected_str = pprint.pformat(expected, width=100)
            request.node.add_report_section(
                "call",
                "jobspec",
                (
                    f"\n=== Jobspec dump on failure for job {jobid} "
                    f"(expected source: {source_label or 'unknown'}) ===\n{jobspec_str}\n"
                    f"=== Expected structure ===\n{expected_str}\n"
                    "=== End jobspec dump ===\n"
                ),
            )
            raise

    return _diff_jobspec_keys


def build_ignore_predicate(ignore_keys, debug=False, debug_log=None):
    """
    Build a composite predicate with support for multiple specs.

    Returns predicate(raw_path_tuple, key_or_index_raw, actual_value, pretty_path_list) -> bool.

    Supported input forms for ignore_keys:
      - None
      - Single predicate callable
      - Single path spec: dotted string "a.b.1.c.2" or tuple ("a", "b", 1, "c", 2)
      - Collection of mixed specs: [predicate, {"timestamp"}, "tasks.0.command.3", ("tasks", 0, "count")]
      - Sets/lists of simple names: {"timestamp", "uuid"}

    Matching rules:
      - Full path match compares tuple(raw_path) + (key_or_index,) against normalized path set.
      - Simple name match applies when key_or_index is a str and appears in simple_names.
      - Custom predicates are called with raw_path, key_or_index, actual_value.
      - If any matcher returns True, the element is ignored.

    Debugging:
      - If debug=True, every ignore decision is logged with context.
      - Provide debug_log(msg) to route logs, otherwise print is used.
    """
    if not debug_log and debug:
        debug_log = pprint.pprint

    # Normalize all specs into:
    normalized_paths = set()  # set of tuples of raw segments
    simple_names = set()      # set of str names
    custom_preds = []         # list of callables(raw_path, key_or_index, actual_value) -> bool
    
    # pprint.pprint(f"[build-pred][main]: post-spec addition, id(normalized_paths) = {id(normalized_paths)}")
    def parse_path_str(s):
        parts = s.split(".")
        parsed = []
        for p in parts:
            if p.isdigit():
                parsed.append(int(p))
            else:
                parsed.append(p)
        return tuple(parsed)

    def add_spec(spec):
        if spec is None:
            return
        if callable(spec):
            custom_preds.append(spec)
            return
        if isinstance(spec, str):
            normalized_paths.add(parse_path_str(spec))
            return
        if isinstance(spec, tuple):
            normalized_paths.add(spec)
            return
        # If it is a collection, inspect elements
        if isinstance(spec, (list, set, tuple)):
            # Heuristically treat string elements as simple names unless they look like paths
            for x in spec:
                if callable(x):
                    custom_preds.append(x)
                elif isinstance(x, str):
                    # Decide if this is a dotted path or just a name
                    if "." in x or x.isdigit():
                        normalized_paths.add(parse_path_str(x))
                    else:
                        simple_names.add(x)
                elif isinstance(x, tuple):
                    normalized_paths.add(x)
                else:
                    # ignore non-supported types quietly
                    pass
            return
        # Fallback, unsupported type ignored

    # Accept single or multiple specs
    if isinstance(ignore_keys, (list, tuple, set)):
        for spec in ignore_keys:
            # pprint.pprint(f"[build-pred]: Adding {spec=}")
            add_spec(spec)

        # pprint.pprint(f"[build-pred]: Normalized paths: {normalized_paths=}, types: {list(tuple(type(pi) for pi in i) for i in normalized_paths)}")
    else:
        add_spec(ignore_keys)
    # pprint.pprint(f"[build-pred][main]: post-spec addition, id(normalized_paths) = {id(normalized_paths)}")
    def match(raw_path, key_or_index, actual_value):
        full = tuple(raw_path) + (key_or_index,)
        # pprint.pprint(f"[ignore-pred][match]: {full=}, types: {tuple(type(i) for i in full)}")
        # pprint.pprint(f"[ignore-pred][match]: {normalized_paths=}, types: {list(tuple(type(pi) for pi in i) for i in normalized_paths)}")
        # pprint.pprint(f"[build_ignore_predicate][match]: id(normalized_paths) = {id(normalized_paths)}")
        
        if full in normalized_paths:
            return True
        if isinstance(key_or_index, str) and key_or_index in simple_names:
            return True
        for pred in custom_preds:
            try:
                if pred(raw_path, key_or_index, actual_value):
                    return True
            except Exception:
                # Do not break matching on predicate error, treat as False
                continue
        return False

    def composite(raw_path, key_or_index, actual_value, pretty_path):
        # pprint.pprint(f"[build_ignore_predicate][composite]: pre-match: id(normalized_paths) = {id(normalized_paths)}")
        result = match(raw_path, key_or_index, actual_value)
        if debug:
            which = []
            if tuple(raw_path) + (key_or_index,) in normalized_paths:
                which.append("path")
            if isinstance(key_or_index, str) and key_or_index in simple_names:
                which.append("name")
            for idx, pred in enumerate(custom_preds):
                try:
                    if pred(raw_path, key_or_index, actual_value):
                        which.append(f"pred[{idx}]")
                except Exception:
                    pass
            msg = (
                f"[ignore-debug] raw_path={raw_path}, key_or_index={key_or_index!r}, "
                f"pretty_path={'.'.join(pretty_path) if pretty_path else '<root>'}, "
                f"actual_value={actual_value!r}, ignored={result}, via={','.join(which) or 'none'}"
            )
            debug_log(msg)
        return result

    return composite


class FluxJobspecError(Exception):
    pass


@pytest.fixture
def generate_jobspec_from_script():
    """
    Pytest fixture that returns a helper callable:
      generate_jobspec_from_script(script_path, extra_args=None) -> Dict[str, Any]

    It runs `flux batch --dry-run <script>` and returns the jobspec JSON as a dict.
    """
    def _generate(script_path: str, extra_args: Optional[list[str]] = None) -> Dict[str, Any]:
        cmd = ["flux", "batch", "--dry-run", script_path]
        if extra_args:
            cmd = ["flux", "batch", "--dry-run"] + extra_args + [script_path]

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as e:
            raise FluxJobspecError(f"Failed to execute flux batch: {e}") from e

        if proc.returncode != 0:
            raise FluxJobspecError(
                f"flux batch dry-run failed with exit code {proc.returncode}; stderr: {proc.stderr.strip()}"
            )

        stdout = proc.stdout.strip()
        if not stdout:
            raise FluxJobspecError("No jobspec output captured from flux batch --dry-run")

        try:
            jobspec = json.loads(stdout)
            # pprint.pprint(f"type of jobspec: {type(jobspec)}")
        except json.JSONDecodeError:
            # Fallback in case of extra banner lines; try from first '{'
            first_brace = stdout.find("{")
            if first_brace == -1:
                raise FluxJobspecError("Dry-run output did not contain JSON")
            try:
                jobspec = json.loads(stdout[first_brace:])
            except json.JSONDecodeError as e2:
                raise FluxJobspecError("Failed to parse jobspec JSON from dry-run output") from e2

        if not isinstance(jobspec, dict):
            raise FluxJobspecError("Parsed jobspec is not a JSON object")

        return jobspec

    return _generate

@pytest.fixture
def normalize_workspace_token(workspace_str: str, study_root: Path):
    """
    Helper for checking proper workspace token substitution in step scripts.
    Makes workspace path relative to study_root to account for tests running
    from anywhere, precluding use of full paths in expected value tests.
    """
    # NOTE: does this handle workspace_str having '/' in it already?
    return study_root.resolve() / workspace_str



class PathNotFoundError(AssertionError):
    pass

# @pytest.fixture
# def assert_path_in_file_is_relative_to(request):
def assert_path_in_file_is_relative_to(
    file_path: Path,
    *,
    workspace_root: Path,
    line_prefix_regex: Optional[Pattern[str]] = None,
    path_regex: Pattern[str],
) -> Path:
    """
    Search `file_path` for a line that optionally matches `line_prefix_regex`,
    then extract a path via `path_regex`.

    Example path_regex: re.compile(r"This workspace:\s+(?P<path>\S+)")
    or: re.compile(r'workspace:\s+(?P<path>/\S+)')

    Asserts that:
      - The path is absolute
      - It is inside `workspace_root`
    Returns the relative path (Path object) from `workspace_root` to that path.
    """
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        if line_prefix_regex is not None:
            if not line_prefix_regex.search(line):
                continue

        m = path_regex.search(line)
        if not m:
            continue

        raw_path = m.group("path") if "path" in m.groupdict() else m.group(0)
        abs_path = Path(raw_path)

        assert abs_path.is_absolute(), (
            f"Expected an absolute path in {file_path} line {idx}, got {raw_path!r}"
        )
        workspace_root = workspace_root.resolve()
        abs_path = abs_path.resolve()

        try:
            rel = abs_path.relative_to(workspace_root)
        except ValueError as exc:
            raise AssertionError(
                f"Path {abs_path} (from {file_path} line {idx}) is not under workspace root {workspace_root}"
            ) from exc

        return rel

    raise PathNotFoundError(
        f"No line in {file_path} matched line_prefix_regex={line_prefix_regex} "
        f"and path_regex={path_regex.pattern!r}"
    )

    # return _assert_path_in_file_is_relative_to

@pytest.fixture
def relative_path_checker():
    """
    Fixture that returns a function to assert that a path inside a file
    is relative to a given workspace root, and give you the relative path.
    """
    def _check(
        file_path: Path,
        *,
        workspace_root: Path,
        line_prefix: Optional[str] = None,
        path_pattern: str,
    ) -> Path:
        """
        Convenience wrapper that builds regex objects from simple args.

        - line_prefix: simple text prefix to identify the line, or None
        - path_pattern: a regex with named group 'path', e.g.
            r"This workspace:\s+(?P<path>\S+)"
        """
        line_prefix_regex = None
        if line_prefix is not None:
            line_prefix_regex = re.compile(re.escape(line_prefix))

        path_regex = re.compile(path_pattern)

        return assert_path_in_file_is_relative_to(
            file_path=file_path,
            workspace_root=workspace_root,
            line_prefix_regex=line_prefix_regex,
            path_regex=path_regex,
        )

    return _check

# @pytest.fixture
# def step_workspace_token_checker():

@pytest.fixture
def fs_layout_checker():
    """
    Fixture for checking that specific relative directories/files exist
    under a given workspace root, without hardcoding absolute paths.
    """
    def _expect_dir(workspace_root: Path, rel_dir: Union[str, Path]) -> Path:
        rel_dir = Path(rel_dir)
        full = workspace_root / rel_dir
        assert full.is_dir(), f"Expected directory {rel_dir} under {workspace_root}, but it does not exist"
        return full

    def _expect_file_pattern(
        workspace_root: Path,
        rel_dir: Union[str, Path],
        pattern: str,
    ) -> List[Path]:
        """
        Assert that at least one file in `rel_dir` matches `pattern`
        (shell-style, like 'hello_world_instance_0_*.sh').

        Returns matching Path objects.
        """
        rel_dir = Path(rel_dir)
        full_dir = workspace_root / rel_dir
        assert full_dir.is_dir(), f"Expected directory {rel_dir} under {workspace_root}, but it does not exist"

        matches: List[Path] = []
        for child in full_dir.iterdir():
            if child.is_file() and fnmatch.fnmatch(child.name, pattern):
                matches.append(child)

        assert matches, (
            f"No files in {rel_dir} under {workspace_root} match pattern {pattern!r}. "
            f"Files existing: {[c for c in full_dir.iterdir() if c.is_file()]}"
        )
        return matches

    class Checker:
        expect_dir = staticmethod(_expect_dir)
        expect_file_pattern = staticmethod(_expect_file_pattern)

    return Checker
