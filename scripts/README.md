# Manual verification scripts

Ad-hoc scripts that were sitting in the repository root named `test_*.py`.
Pytest collects anything matching that pattern, so they were picked up as tests
while being interactive scripts that call live APIs — which is part of why the
suite could never be trusted.

They are kept because they are useful for manual smoke-testing against a real
provider, but they are not tests. The real suite is in `tests/`.

| Script | Purpose |
|---|---|
| `test_llm.py` | Check an LLM provider responds with the configured key |
| `test_mini_gen.py` | Generate one short piece end to end |
| `test_project.py` | Import-and-wire smoke check |
| `verify_generation.py` | Inspect a generated artefact by hand |
| `verify_imports.py` | Confirm every module imports |

Run them deliberately, with credentials present:

```bash
python scripts/test_llm.py
```
