DOCS = docs
EGG = $(wildcard *.egg-info)

.PHONY: cleanall clean cleandocs docs

all: cleanall release docs

release:
	python setup.py sdist bdist_wheel

docs:
	$(MAKE) -C $(DOCS) html

clean:
	rm -rf dist
	rm -rf build

cleandocs:
	rm -rf $(DOCS)/build

cleanall: clean cleandocs
