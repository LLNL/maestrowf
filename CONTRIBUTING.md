# Contributing

Thank you for contributing.

## Development environment

We recommend using [Poetry](https://python-poetry.org/) for local development.

The Poetry version, and lock file, is pinned to:

- `1.8.4`

This version is pinned for now while the project continues to support older Python versions. The constraint may be relaxed in the future.

Typical setup:
```bash
pip install "poetry==1.8.4"
poetry install --with dev
```
This installs the project together with the development dependencies used for testing, linting, and documentation work.

Using Poetry is recommended, but it is not required. Contributors may also use `pip` or another environment manager if preferred. If you do so, please install the project and any required development and documentation dependencies manually instead of relying on the Poetry-managed lock file.

## Branching strategy

This project uses a release-oriented branching model.

- Create feature and bugfix branches from `develop`.
- Open pull requests back into `develop` for normal development work.
- Treat `develop` as the integration branch for ongoing changes.
- Merge to `main` only as part of the release process.

In other words, day-to-day development should not usually target `main` directly.

Hotfixes on `main` are allowed in principle, but no formal hotfix workflow has been needed yet. If that changes, the process should be documented here.

## Development workflow

- Create a branch for your change.
- Make code and documentation updates.
- Add a changelog fragment when the change should be surfaced to users or contributors.
- Open a pull request for review.

## Changelog fragments

This project uses `scriv` to manage changelog fragments.  `scriv` is installed with the project dependencies, and creating the fragment is as simple as `scrive create` from the top level and then edit that fragment. Fragments are stored in:

- `changelog.d/`

Fragments are collected into the main changelog at release time.

## Scriv git configuration

`scriv` may use git or GitHub identity information when naming changelog fragments. If you
want fragment filenames to use your GitHub username rathern than your email-derived identity, add this to your git configuration used for github:
```ini
[scriv]
  user-nick = your-github-username
```

For example:
```bash
git config --global scriv.user-nick your-github-username
```

## Changelog categories

Use one of the following categories in changelog fragments:

| Category | Description |
|---|---|
| Added | New features or capabilities |
| Changed | Updates to existing behavior |
| Fixed | Bug fixes |
| Removed | Removed functionality |
| Documentation | Important documentation changes |
| Maintenance | Internal maintenance or dependency updates, CI, tooling, ... |

## Changelog files

| File | Purpose |
|---|---|
| `CHANGELOG.md` | Main committed changelog |
| `CHANGELOG_docs.md` | Generated docs-only changelog |
| `docs/whats_new/changelog.md` | Generated docs page during build |

## Documentation changelog behavior

Documentation builds prefer `CHANGELOG_docs.md` when it exists. This allows development documentation to include unreleased changelog fragments without modifying the committed `CHANGELOG.md`.

If `CHANGELOG_docs.md` is not present, documentation builds fall back to `CHANGELOG.md`.

The docs-only changelog build uses a separate Scriv configuration file to generate the `_docs` variant, but is otherwise the same as the config in `pyproject.toml`:

- `scriv_docs.ini`

## Local docs workflow

For a development-style docs build with unreleased changelog fragments:
```bash
python scripts/docs_prepare.py --mode dev --title "Unreleased"
mkdocs serve
```
For a release-style docs build:
```bash
python scripts/docs_prepare.py --mode release
mkdocs build
```
## What's New docs section

The documentation includes a `What's New` section with:

- an overview page
- the changelog (`CHANGELOG_docs.md` sourced)
- the roadmap (under construction)
- proposal tracking pages for draft and accepted proposals (under construction)

## Release process

The release process is currently manual.

Typical steps:

1. Finalize the changes for the release.
2. Update the project version.
3. Run `scriv collect` to generate the release entry in `CHANGELOG.md`. (Replaces old manual curation)
4. Commit the version bump and changelog update.
5. Build the distribution artifacts.
6. Publish the release candidate to TestPyPI.
7. Run manual validation on real machines, including tests against multiple schedulers.
8. Merge release into main
9. Create the release tag.
10. Publish the final release to PyPI.
11. Create the GitHub release.
12. Build and publish release documentation.

## Future automation

Release automation will likely remain separate from ordinary CI on pull requests or merges to `main`.

A likely future model is:

- regular CI on pull requests and merges to `main`
- a manually triggered release workflow for building artifacts and publishing to TestPyPI
- manual validation outside CI
- a controlled final publish to PyPI
- tag-triggered release documentation and GitHub release creation

This avoids treating every merge to `main` as a release that publishes to pypi.
