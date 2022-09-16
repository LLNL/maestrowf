# validate that all variables in template are valid

# validate that no variables in template conflict between
# maestro variables and TEMPLATE_VAR_LIST

# Write yaml index_directory index path
# labels.yaml
# update default template in maestro.py
# update --link-template help in maestro.py
# spell check
# lint flake8 pylint

# using {{data}} as maestro input and in template should cause error

# add test for maestro user key/value conflicts with maestro template keyvalue
# add test for maestro user key/value substitutes properly

# maestro run -s 1 -fg -y --make-links tests/specification/test_specs/link_integration_fast.yml

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

