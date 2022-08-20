# fix output_path // output_root problems


# Write yaml index_directory index path
# labels.yaml
# requirements of template:
# unique path for each study/combo/step
# optional: {{date}}
# get rid of link_directory
NOTE: template must include {{combo}} and {{step}}.
[Default: {{link_directory}}/{{date}}/run-{{INDEX}}/{{combo}}/{{step}}
[Default: {{link_directory}}/{{date}}/{study_name}-{{study_index}}/combo-{{combo_index}}-{{combo}}/{{step}}

# use variable list below first. raise warning if there is a conflict.

{{run_time}}
{{maestro_variable_names}} # make sure maestro variable names don't conflict with other variables
{{study_name}}
{{output_path}} - Parent directory for this maestro study
{{link_directory}} - Link directory for this maestro study
{{date}} - Human-readable date (e.g. '2020_07_28')
{{combo}} - Maestro label for a set of parameters
                (e.g. 'X1.5.X2.5.X3.20')
                [maximum length: 255 characters]
{{step}} - Maestro label for a given step (e.g. 'run')
{{study_index}} - Unique number for each maestro execution (e.g. '0001')
{{combo_index}} - Unique number for each maestro combination (e.g. '0001')

# split_indexed_directory

# add options for float formatting

# {{study-name}} {{step-name}} {{study-index}} {{combo-index}}

# test with hash
maestro run -s 1 -y --hashws --make-links ./samples/lulesh/lulesh_sample1_macosx.yaml; tail -f sample_output/lulesh/lulesh_sample1_2022081*/log*/*

# test without hash
maestro run -s 1 -y --make-links ./samples/lulesh/lulesh_sample1_macosx.yaml; tail -f sample_output/lulesh/lulesh_sample1_2022081*/log*/*

