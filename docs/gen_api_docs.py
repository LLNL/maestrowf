"""
Helper to auto generate reference pages for the api docs.

Recipe from mkdocstrings docs.
"""

from pathlib import Path
import sys
import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

src_path = Path('.') / '..' / 'maestrowf'

# Resolve whether in docs dir or project root (local vs readthedocs config)
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

    module_path = path.relative_to(src_path).with_suffix("")
    doc_path = path.relative_to(src_path).with_suffix(".md")
    full_doc_path = Path("Maestro/reference_guide/api_reference", doc_path)

    parts = list(module_path.parts)

    # Ensure __init__.py's get added/parsed properly and write contents to
    # the current module's index.md
    parts = ['maestrowf'] + parts  # add package prefix back on
    if parts[-1] == "__init__":  # special handling for top level module files
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
        if not parts:
            continue
    elif parts[-1] == "__main__":
        continue

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:  #
        identifier = ".".join(parts)
        # Set custom title for index pages to match nav entries
        if doc_path.name == "index.md":
            print(f"# {parts[-1].capitalize()}", file=fd)
            print("---", file=fd)

        # add the mkdoc strings hook
        print("::: " + identifier, file=fd)

    mkdocs_gen_files.set_edit_path(full_doc_path, path)  #

# NOTE: SUMMARY.md has to be the name of the nav file
with mkdocs_gen_files.open("Maestro/reference_guide/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
