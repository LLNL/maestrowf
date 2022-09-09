# finish debugging {{step}} validation

================================================= short test summary info =================================================
FAILED tests/test_link.py::TestLinkUtilsUnits::test_validate_combo_template - AssertionError: False is not true
FAILED tests/test_link.py::TestLinkUtilsUnits::test_validate_study_template - UnboundLocalError: local variable 'max_stu...
======================================= 2 failed, 31 passed, 5 deselected in 4.05s ========================================
(maestrowf-F8Kxbm4v-py3.8) (base) crkrenn@admins-MacBook-Pro-2 maestrowf_crk %

# validate {step} in linker.py template
# remove .replace from linker.py (done except for step)
# Write yaml index_directory index path
# labels.yaml
# update default template in maestro.py
# update --link-template help in maestro.py
# spell check
# lint flake8 pylint

# maestro run -fg -y --make-links tests/specification/test_specs/link_integration_fast.yml

NOTE: template must include {{combo}} and {{step}}.
[Default: {{link_directory}}/{{date}}/run-{{INDEX}}/{{combo}}/{{step}}
[Default: {{link_directory}}/{{date}}/{study_name}-{{study_index}}/combo-{{combo_index}}-{{combo}}/{{step}}

# use variable list below first. raise warning if there is a conflict.

* {{study_time}}
* {{study_date}}
* {{maestro_variable_names}} # make sure maestro variable names don't conflict with other variables
* {{study_name}}
* {{output_path}} - Parent directory for this maestro study
* {{date}} - Human-readable date (e.g. '2020_07_28')
* {{long_combo}} - Maestro label for a set of parameters,
* {{combo}} - Maestro label for a set of parameters, with reals rounded
                (e.g. 'X1.5.X2.5.X3.20')
                [maximum length: 255 characters]
* {{step}} - Maestro label for a given step (e.g. 'run')

{{study_index}} - Unique number for each maestro execution (e.g. '0001')
{{output_path}} / {{study_name}} / {{study_date}} / {{study_time}}

{{combo_index}} - Unique number for each maestro combination (e.g. '0001')

