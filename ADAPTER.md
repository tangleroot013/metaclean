Adapter for stunning-octo-funicular

This repository contains a minimal adapter (stunning_octo_adapter.py) that
exposes an `adapter` object with a `run(args)` method. The adapter is intended
for safe integration with stunning-octo-funicular and is dry-run by default.

To execute the adapter in this repo (example):

  PYTHONPATH=/path/to/metaclean python -c "import stunning_octo_adapter; stunning_octo_adapter.adapter.run(['--exec'])"
