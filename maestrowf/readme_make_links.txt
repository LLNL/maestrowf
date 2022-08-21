============================================================== short test summary info ===============================================================
FAILED tests/test_link.py::TestLinkUtilUnits::test_build_replacements - AttributeError: 'Linker' object has no attribute 'validate_link_template'
FAILED tests/test_link.py::TestLinkUtilUnits::test_split_indexed_directory - AttributeError: 'Linker' object has no attribute 'validate_link_template'
===================================================== 2 failed, 30 passed, 2 deselected in 4.49s =====================================================
(maestrowf-F8Kxbm4v-py3.8) (base) crkrenn@admins-MBP-2 maestrowf_crk % open tests/test_link.py    
(maestrowf-F8Kxbm4v-py3.8) (base) crkrenn@admins-MBP-2 maestrowf_crk % open tests/test_link.py
(maestrowf-F8Kxbm4v-py3.8) (base) crkrenn@admins-MBP-2 maestrowf_crk % code tests/test_link.py
(maestrowf-F8Kxbm4v-py3.8) (base) crkrenn@admins-MBP-2 maestrowf_crk % pytest -k "not test_integration"

# rename instance -> combo

# Write yaml index_directory index path
# labels.yaml
# requirements of template:
# unique path for each study/combo/step
# optional: {{date}}
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


# split_indexed_directory

# add options for float formatting

# {{study-name}} {{step-name}} {{study-index}} {{combo-index}}

# test with hash
maestro run -s 1 -y --hashws --make-links ./samples/lulesh/lulesh_sample1_macosx.yaml; tail -f sample_output/lulesh/lulesh_sample1_2022081*/log*/*

# test without hash
maestro run -s 1 -y --make-links ./samples/lulesh/lulesh_sample1_macosx.yaml; tail -f sample_output/lulesh/lulesh_sample1_2022081*/log*/*

