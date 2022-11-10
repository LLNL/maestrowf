"""
Helper to auto generate reference pages for the api docs.

Recipe from mkdocstrings docs.
"""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

print("LOOKING IN : {}".format(Path(Path("maestrowf").absolute().parent.parent, "maestrowf")))
src_path = Path(Path("maestrowf").absolute().parent.parent, "maestrowf")
for path in sorted(src_path.rglob("*.py")):

                   # Path("maestrowf").parent.rglob("*.py")):
    print("Searching {}".format(path))
    module_path = path.relative_to(src_path).with_suffix("")  # 
    doc_path = path.relative_to(src_path).with_suffix(".md")  # 
    full_doc_path = Path("Maestro/api_reference", doc_path)  # 

    parts = list(module_path.parts)
    # print 
    if parts[-1] == "__init__":  # 
        parts = parts[:-1]
        print("INIT PARTS: {}, in {}".format(parts, list(module_path.parts)))
        if not parts:
            continue
    elif parts[-1] == "__main__":
        continue

    parts = ['maestrowf'] + parts
    with mkdocs_gen_files.open(full_doc_path, "w") as fd:  # 
        identifier = ".".join(parts)  # 
        print("::: " + identifier, file=fd)
        if parts[-1] == 'utils':
            print("DEBUG: identifier: ::: " + identifier)

    print("ADDING AUTODOC: {} {}".format(full_doc_path, path))
    mkdocs_gen_files.set_edit_path(full_doc_path, path)  #
    # mkdocs_gen_files.set_edit_path()


with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
    for line in nav.build_literate_nav():
        print("NAV LINE: {}".format(line))
