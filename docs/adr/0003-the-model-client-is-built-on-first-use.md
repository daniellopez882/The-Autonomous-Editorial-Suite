# ADR 0003 — The model client is built on first use; the container is booted in CI

**Status:** accepted · **Date:** 2026-09-06

## Context

`content_generation_crew.py` built the model client at import time:

```python
api_key = os.getenv("DEEPSEEK_API_KEY")
deepseek_llm = ChatOpenAI(model="deepseek-chat", openai_api_key=api_key, ...)
```

With the key unset, `api_key` is `None` and the constructor raises
`OpenAIError: Missing credentials` (reproduced on 2026-09-06 against the pinned
`langchain-openai` range). `app.py` imported the crew at the top of the script,
so a deployment without the key showed neither a login form nor an error about
the key: Streamlit rendered the import traceback. The same import also wrote the
key into `OPENAI_API_KEY` for the whole process as a side effect.

The image ran as root, single-stage, with `build-essential` in the runtime layer
and `curl` installed for the health check; CI built it and never ran it.

## Decision

1. `llm.build_llm()` is the one place the client is built. It is called when a
   crew is created — which happens when a logged-in user clicks generate — and
   raises `LLMNotConfigured` with an instruction the operator can act on.
   `app.py` imports the crew inside `get_crew()` and shows that error in the
   page. Nothing model-related runs at import.
2. `preflight.py` reports whether the key is present at container start. Its
   absence is a warning, not a refusal: the login page is served and every
   generation attempt is refused until the key exists.
3. The image has two stages, runs as uid 10001, probes `/_stcore/health` with
   Python, defaults to `ENVIRONMENT=production`, and starts through an entrypoint
   that runs the preflight and then `exec`s streamlit. `.dockerignore` keeps
   `.git`, virtualenvs and every `.env` but the example out of the context.
4. CI boots the image with a real signing key and password and asserts: the
   health check answers, `GET /` is 200, the log holds the preflight line and no
   traceback, the process is not root, and a production start without a
   password is refused.

## Consequences

- The app boots, logs in and explains itself with no model key at all; the
  first model call is where a missing key is felt, and it is reported as a
  sentence rather than a traceback.
- `OPENAI_API_KEY` is mirrored from the DeepSeek key only when nothing else set
  it, because CrewAI and LangChain look for it in places that do not take the
  client as an argument.
- A regression of the "secret needed at import" kind fails CI, because CI now
  starts the image without a model key.
