# Gemini Portal (v2)

This repository contains the code powering https://portal.mozz.us.

The origin version was written with Flask, maintained in a personal
repository and never publicly released. This repository is a full
rewrite (version 2) with following goals:

- Switching to an ASGI framework (quartz) to better support the load
  profile experienced by an HTTP proxy server (IO bottleneck).
- Making the codebase more maintainable in the long term by adding
  unit tests, type hints, and linters.

This is probably only useful for myself. You are welcome to use the
code, but I am not writing this with the goal of making a general
purpose gemini-to-http proxy, of which there are already many other
open source alternatives.

## Development

```bash
# Download the source
git clone https://github.com/michael-lazar/gemini-portal
cd gemini-portal/

# Initialize a virtual environment and install pip dependencies, etc.
tools/boostrap

# Initialize pre-commit hooks
pre-commit install

# Launch the dev server
tools/quart run

# Run the tests, linters, etc.
tools/pytest
tools/mypy

# Rebuild requirements
tools/pip-compile
tools/pip-install
```

## License

[The Human Software License](https://license.mozz.us)

> A hobbyist software license that promotes maintainer happiness
> through personal interactions. Non-human
> [legal entities](https://en.wikipedia.org/wiki/Legal_person) such as
> corporations and agencies aren't allowed to participate.
