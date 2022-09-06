# fix bug... links are made one directory down. 

# make Linker more robust by saving time, date, name in study instances
        study_time = output_name.split("-")[-1]
        replacements['study_time'] = study_time
        study_date = output_name.split("_")[-1].replace(f"-{study_time}","")
        replacements['study_date'] = study_date
        study_name = output_name.replace(f"_{study_date}-{study_time}","")


move Linker to maestrowf/datastructures/core/linker.py

make setter for step_exp.workspace_no_hash = workspace_no_hash (in study.py)
update Linker code to use workspace_no_hash


# no hash:
 'combo': 'VAR1.0.84.VAR2.0.73.VAR3.0.90.VAR4.0.19',
 'long_combo': 'VAR1.0.8368954934.VAR2.0.7296721416.VAR3.0.8958327389.VAR4.0.1895291838',
 'nickname': None,
 'step': 'test-directory-hashing',
# hash
 'combo': 'c74742ecea5a2b58e67350b5a1e0a234',
 'long_combo': 'c74742ecea5a2b58e67350b5a1e0a234',
 'nickname': 'c74742ecea5a2b58e67350b5a1e0a234',
 'step': 'test-directory-hashing_VAR1.0.8368954934.VAR2.0.7296721416.VAR3.0.8958327389.VAR4.0.1895291838',


# combo index working; run_index no longer working

# maestro run -fg -y --make-links tests/specification/test_specs/link_integration_fast.yml 

            if type(self.study_index) == int:
                self.study_index = self.new_index(
                    link_path, "{{study_index}}")
                replacements = self.build_replacements(record)
            if type(self.combo_index[long_combo]) == int:
                self.combo_index[long_combo] = self.new_index(
                    link_path, "{{combo_index}}")   

# add more options  

# store indices in object

# Write yaml index_directory index path
# labels.yaml
# requirements of template:
# unique path for each study/combo/step
# optional: {{date}}
NOTE: template must include {{combo}} and {{step}}.
[Default: {{link_directory}}/{{date}}/run-{{INDEX}}/{{combo}}/{{step}}
[Default: {{link_directory}}/{{date}}/{study_name}-{{study_index}}/combo-{{combo_index}}-{{combo}}/{{step}}

 'link_template': '{{output_path}}/links/{{date}}/run-{{study_index}}/{{combo}}/{{step}}',
 'output_path': '/Users/crkrenn/Dropbox/code/maestrowf_crk/output',

{'VAR1': 0.3874309076,
 'VAR2': 0.7520078045,
 'combo': 'VAR1.0.39.VAR2.0.75.VAR3.0.72.VAR4.0.55',
 'long_combo': 'VAR1.0.3874309076.VAR2.0.7520078045.VAR3.0.718718159.VAR4.0.5491000152',

 'date': '2022-08-25',
 'output_name': 'link_integration_test_20220825-214652',
 'study_date': '20220825',
 'study_time': '214652'}

 'step': 'test-directory-hashing',
 'study_name': 'link_integration_test',


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

