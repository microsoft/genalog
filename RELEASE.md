# Toucan Release Procedure

Checklist for the release process of `genalog`:

### Preparation
- [x] Ensure `main` branch contains all relevant changes and PRs relating to the specific release is merged
- [x] Create and switch to a new release branch (i.e. release-X.Y.Z)

### Package Metadata Update
- [x] Update VERSION.txt with version bump. Please reference [Semantic Versioning](https://semver.org/).
- [x] Update [CHANGELOG.md](./CHANGELOG.md)
- [x] Commit the above changes with title "Release vX.Y.Z" 
- [x] Generate a new git tag for the new version (e.g. `git tag -a v0.1.0 -m "Initial Release"`)
- [x] Push the new tag to remote `git push origin v0.1.0`
- [x] Create a new PR with the above changes into `main` branch. 

### Release to PyPI
- [x] Manually trigger the [release pipeline](https://dev.azure.com/genalog-dev/genalog/_build?definitionId=2) in DevOps on the release branch, this will publish latest version of `genalog` to PyPI.
    - [x] Select `releaseType` to `Test` to test out the release in [TestPyPI](https://test.pypi.org/project/genalog/)
    - [x] Rerun and switch `releaseType` to production if looks good.
- [x] If the pipeline ran successfully, check and publish the draft of this release on [Github Release](https://github.com/microsoft/genalog/releases)
- [x] Latest version is pip-installable with:
    - `pip install genalog`

### Update Documentation on Github Page
- [x] Staying on the release branch, `cd docs && pip install -r requirements-doc.txt`
- [x] Build the jupyter-book with `jupyter-book build --all genalog_docs`
- [x] Preview the HTML files, if looks good [publish to Github Page](https://jupyterbook.org/start/publish.html#publish-your-book-online-with-github-pages): `ghp-import -n -p -f genalog_docs/_build/html` 
