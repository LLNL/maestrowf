VENV = venv
DOCS = docs
EGG = $(wildcard *.egg-info)

all:
	$(MAKE) cleanall
	$(MAKE) wheel
	$(MAKE) clean

clean:
	rm -rf $(VENV)

cleandocs:
	rm -rf $(DOCS)/build/

cleanall:
	$(MAKE) clean
	rm -rf build/
	rm -rf dist/
	rm -rf $(EGG)

venv: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	test -d $(VENV) || python -m virtualenv $(VENV)
	$(VENV)/bin/pip install -U pip setuptools
	$(VENV)/bin/pip install -Ur requirements.txt
	touch $(VENV)/bin/activate

test: venv
	$(VENV)/bin/nosetests

wheel: venv
	$(VENV)/bin/python setup.py bdist_wheel

sphinx: venv
	source $(VENV)/bin/activate && cd $(DOCS) && make html
