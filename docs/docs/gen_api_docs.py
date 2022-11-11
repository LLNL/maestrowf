"""
Helper to auto generate reference pages for the api docs.

Recipe from mkdocstrings docs.
"""

from pathlib import Path
import os
import sys
import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

    
# print("LOOKING IN : {}".format(Path(Path("maestrowf").absolute().parent.parent, "maestrowf")))
# print("LOOKING IN : {}".format(Path(Path("maestrowf").absolute().parent.parent, "maestrowf")))
# src_path = Path(Path("maestrowf").absolute().parent.parent, "maestrowf")
src_path = Path('.') / '..' / 'maestrowf'
print(f"LOOKING IN : {src_path}")
# Resolve whether in docs dir or project root (local vs readthedocs config)
print(Path('.').resolve())
proj_toml = Path('.') / 'pyproject.toml'
mkdocs_yml = Path('.') / 'mkdocs.yml'

print(f"{proj_toml} exists: {proj_toml.exists()}")
print(f"{mkdocs_yml} exists: {mkdocs_yml.exists()}")
if proj_toml.exists():
    src_path = Path('.') / 'maestrowf'
elif mkdocs_yml.exists():
    src_path = Path('.') / '..' / 'maestrowf'
else:
    mkdocs_gen_files.log.warning('Skipping API docs because "maestrowf" directory is missing.')
    sys.exit()

for path in sorted(src_path.rglob("*.py")):

                   # Path("maestrowf").parent.rglob("*.py")):
    print("Searching {}".format(path))

    module_path = path.relative_to(src_path).with_suffix("")  # 
    doc_path = path.relative_to(src_path).with_suffix(".md")  # 
    full_doc_path = Path("Maestro/reference_guide/api_reference", doc_path)  # 

    parts = list(module_path.parts)
    # print 
    if parts[-1] == "__init__":  # 
        parts = parts[:-1]
        print("INIT PARTS: {}, in {}".format(parts, list(module_path.parts)))
        if not parts:
            continue
    elif parts[-1] == "__main__":
        continue

    # Add the package prefix back on 
    parts = ['maestrowf'] + parts
    with mkdocs_gen_files.open(full_doc_path, "w") as fd:  # 
        identifier = ".".join(parts)  # 
        print("::: " + identifier, file=fd)
        if parts[-1] == 'utils':
            print("DEBUG: identifier: ::: " + identifier)

    print("ADDING AUTODOC: {} {}".format(full_doc_path, path))
    mkdocs_gen_files.set_edit_path(full_doc_path, path)  #
    # mkdocs_gen_files.set_edit_path()


# Add a top level index to the api_reference section so it's actually a page
print("CWD: {}".format(os.getcwd()))
# with mkdocs_gen_files.open("Maestro/reference_guide/api_reference/index.md", "w") as api_index_file:
#     print(f"# Top-level namespace\n\n", file=api_index_file)
    
with mkdocs_gen_files.open("Maestro/reference_guide/SUMMARY.md", "w") as nav_file:
    print(list(nav.build_literate_nav()))
    for item in nav.build_literate_nav():
        print("NAV LINE: {}".format(item))
    nav_file.writelines(nav.build_literate_nav())
    # for line in nav.build_literate_nav():
    #     print("NAV LINE: {}".format(line))
