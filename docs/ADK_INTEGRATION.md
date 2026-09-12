# Google ADK Integration

The project keeps a deterministic local adapter for unit tests and provides an optional real Google ADK adapter in `app/agents/adk_adapter.py`.

## Install

```bash
python -m pip install -e '.[adk,test]'
```

The adapter uses the current Google ADK Python APIs:

- `google.adk.agents.LlmAgent` for a configured specialist.
- `google.adk.tools.AgentTool` for Agent-as-a-Tool wrapping.

## Credentials

Put credentials only in an ignored `.env` file or the process environment:

```bash
export GOOGLE_API_KEY
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

Never commit, print, or place the key in YAML, tests, logs, or source code.

## Design

`build_adk_agent()` is lazy and dependency-guarded. Therefore:

- Unit and BDD tests do not consume Gemini quota.
- The local CLI remains runnable without Google ADK.
- A real ADK-backed resolver can be introduced by replacing the factory seam.
- Registry validation and allowed-agent selection remain in force before construction.

The optional integration test should be explicitly marked and run only when a configured environment is available.
