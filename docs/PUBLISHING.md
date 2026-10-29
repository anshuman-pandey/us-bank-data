# Publishing US Bank Data

## Current public releases

- `us-bank-data` v0.1.1 is the primary public package on PyPI. Import `usbankdata`.
- `banksonsale-data` v0.1.0 is the existing independently usable engine; its imports and source snapshots remain compatible.
- The OpenBB extension is available from the GitHub source/release. Its PyPI project has not been published.

The GitHub repository was renamed to `anshuman-pandey/us-bank-data` without changing
its repository ID. Existing repository and release URLs redirect to the new name.
The public package adds a small entry point; financial implementation and archived
sources remain in `src/banksonsale_data` without a second implementation.

## PyPI release workflow

The manually dispatched `publish-pypi.yml` workflow uses trusted publishing. The
verified publisher for `us-bank-data` is:

- Repository owner: `anshuman-pandey`
- Repository name: `us-bank-data`
- Workflow filename: `publish-pypi.yml`
- Environment name: `pypi`

Dispatch from the current default branch with a tested `release_tag` and
`package=us-bank-data` (the default). It builds `packages/us-bank-data`, checks
exports/import identity against the engine, and publishes with short-lived OIDC
credentials. No API token belongs in source, chat or workflows. Verify a fresh
public-index install before advertising a new version.

The older engine's active publisher and OpenBB's pending publisher still refer
to the former repository name. They were not retargeted by the latest approval,
which authorized only `us-bank-data`. Matching trust must be reviewed before
future `core`, `openbb` or `all` runs; do not assume those targets are ready.

PyPI permits only one pending project per identical publisher configuration.
Publish new projects sequentially so each pending publisher becomes active.
Account creation, 2FA and new publishing trust require the account owner's
action/authorization. Reference:
https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/

## Release integrity

Build and run data tests, notebook execution, installed-wheel checks and relevant
integration checks before tagging. Keep pinned sample bytes and existing release
tags immutable. Upload checksummed release artifacts. Never bundle private
website source, user records, prospect lists, API keys or account exports.
