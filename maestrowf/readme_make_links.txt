# test with hash
maestro run -s 1 -y --hashws --make-links ./samples/lulesh/lulesh_sample1_macosx.yaml; tail -f sample_output/lulesh/lulesh_sample1_2022081*/log*/*

# test without hash
maestro run -s 1 -y --make-links ./samples/lulesh/lulesh_sample1_macosx.yaml; tail -f sample_output/lulesh/lulesh_sample1_2022081*/log*/*

