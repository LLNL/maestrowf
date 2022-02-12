DOCS = docs
EGG = $(wildcard *.egg-info)

.PHONY: cleanall clean cleandocs docs help release

# Use '#' comments to auto document each target in the help message
help: # Show this help message
	@echo 'usage: make [target] ...'
	@echo
	@echo 'targets:'
	@egrep '^(.+)\:\ #\ (.+)' ${MAKEFILE_LIST} | column -t -c 2 -s ':#'

all: # Clean and then build everything
	cleanall release docs

release: # Build wheel
	python setup.py sdist bdist_wheel

docs: # Build documentation
	$(MAKE) -C $(DOCS) html

clean: # Clean up release (wheel) build areas
	rm -rf dist
	rm -rf build

cleandocs: # Clean up docs build areas
	rm -rf $(DOCS)/build

cleanall: # Clean every thing
	clean
	cleandocs
