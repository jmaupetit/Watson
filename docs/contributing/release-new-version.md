# Release a new version

As a maintainer, if you plan to release a new version of Watson, you will find
useful information on this page.

## Bump a new `x.y.z` release

Create a new branch:

```bash
$ git checkout -b prepare-x.y.z
```

Bump the version number with
[`uv version`](https://docs.astral.sh/uv/guides/package/#updating-your-version),
which updates both `pyproject.toml` and `uv.lock`:

```bash
$ uv version --bump minor  # or patch, major
```

Then edit the following files to describe changes:

* `CHANGELOG.md`: move the `Unreleased` entries to a new dated section and
  update the compare links at the bottom of the file
* `watson.completion` and `watson.zsh-completion`: generate up-to-date
  completion scripts by running `make completion-scripts`

Then commit your work, using the release notes as the commit body, and push
your branch to GitHub:

```bash
$ git add pyproject.toml uv.lock CHANGELOG.md \
  watson.completion watson.zsh-completion
$ git commit -m '🔖(minor) bump release to x.y.z'  # or (patch), (major)
$ git push origin prepare-x.y.z
```

Create a new pull request (PR) with the `prepare-x.y.z` branch. You can safely
merge this PR if all checks are green.

## Publish the `x.y.z` release

Tag the up-to-date `main` branch. Tags must be prefixed with `v`, as pushing a
`v*` tag is what triggers the release workflows:

```bash
$ git checkout main
$ git pull --rebase origin main
$ git tag vx.y.z
$ git push origin vx.y.z
```

GitHub Actions then automatically:

* builds the package and publishes it to PyPI
* deploys the online documentation built with
  [`mkdocs`](https://www.mkdocs.org/) (`make docs-publish` does the same
  manually)

Finally, draft a new
[Watson Release on GitHub](https://github.com/jmaupetit/Watson/releases) with
the same release notes.

## Publish the `x.y.z` release to Homebrew

* Fork the [Homebrew/homebrew-core](https://github.com/Homebrew/homebrew-core)
  repository to your personal GitHub account.
* Get the new release SHA256 checksum by copying it from the
  [td-watson PyPI page](https://pypi.org/project/td-watson/#files).
* Update the brew formula with the automation command `bump-formula-pr`:

```bash
$ brew bump-formula-pr \
  --url='https://files.pythonhosted.org/packages/[...]/td_watson-x.y.z.tar.gz' \
  --sha256='PASTE THE SHA256 CHECKSUM HERE' \
  watson
```

Note: you may also need to update versions of Watson's dependencies (and related
checksums). See [Homebrew's
documentation](https://docs.brew.sh/How-To-Open-a-Homebrew-Pull-Request)
for details.
