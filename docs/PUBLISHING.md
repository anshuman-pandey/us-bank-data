# Publishing BanksOnSale Data

The GitHub release is independently installable. A PyPI release is a separate
publication and must not be advertised as available before its project page and
clean index installation actually work.

## PyPI account setup

The repository has a manual `publish-pypi.yml` workflow using PyPI's trusted
publishing protocol; no API token belongs in source, issues, chat or workflows.
Before running it, the account owner must register the publisher on PyPI for both
`banksonsale-data` and `openbb-banksonsale`:

- Repository owner: `anshuman-pandey`
- Repository name: `banksonsale-data`
- Workflow filename: `publish-pypi.yml`
- Environment name: `pypi`

For an unpublished package, use PyPI's pending-publisher flow. Account creation,
2FA and new publishing trust require the account owner's action/authorization.
Reference: https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/

After registration, run the manual GitHub workflow against the tested tag. It
rebuilds and checks the core plus OpenBB distributions and publishes with short-
lived OIDC credentials. Verify both PyPI project pages and clean installations
before changing README/website instructions to registry shorthand.

## Release integrity

Build and run offline tests, notebook execution, installed-wheel checks and the
optional OpenBB integration before tagging. Pin source data and retain its
manifest; no silent replacement of sample bytes under an existing release tag.
Upload checksummed artifacts to the GitHub release. Never bundle private website
source, user records, prospect lists, API keys or account exports.
