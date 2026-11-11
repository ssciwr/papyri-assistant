# Repository Guidelines

## Project layout

- `backend/` is the Python package `papyri-backend` (FastAPI + LangChain/DeepAgents).
  - Package code lives in `backend/src/papyri_backend/`; agent tools live in `tools/`.
  - Tests live in `backend/tests/` and use pytest.
  - Agent configs live in `backend/configs/`.
  - `backend/skills/` holds runtime skills for the papyrology agent the app serves (mounted at `/skills/`). Edit them only when the task concerns the app agent's behavior.
- `frontend/` is the React/Vite chat UI (npm workspace).
- Put reusable functionality in the package.
- Put one-off scripts in `scripts/`; each must begin with a comment explaining its purpose.
- The database and its vector tables are published by the separate Scrapyrus project; this repository only reads them.

## Development

- Use `uv` for the backend environment; it lives in `backend/.venv`.
- The user creates Git worktrees.
- The agent must not create, remove, or switch worktrees.
- Each worktree has its own `backend/.venv`; never share environments between worktrees.
- Run backend tests from `backend/` using the existing environment:

```bash
cd backend && .venv/bin/python -m pytest
```

- The default run excludes `integration` and `live_model` tests and must keep 90% branch coverage.
- Integration tests need the development PostgreSQL (published at `127.0.0.1:55432`); start it from the repository root and run them from `backend/`:

```bash
docker compose up -d postgres
cd backend && .venv/bin/python -m pytest -m integration
```

- Run `live_model` tests only when the user explicitly asks; they call real provider APIs with real credentials.
- Run the app locally from the repository root with the worktree's environment on `PATH` (`npm run dev` calls whatever `python` is on `PATH`):

```bash
PATH="$PWD/backend/.venv/bin:$PATH" npm run dev
```

- Alternatively, run the development stack with `docker compose up`.
- Verify that the package resolves to the current worktree with:

```bash
cd backend && .venv/bin/python -c "import papyri_backend; print(papyri_backend.__file__)"
```

- If `backend/.venv` is missing or incomplete, ask the user to grant permission to initialize it with:

```bash
cd backend && UV_CACHE_DIR=/tmp/uv-cache uv venv && UV_CACHE_DIR=/tmp/uv-cache uv pip install -e ".[tests]"
```

- After permission is granted, initialize the environment, verify the import path, and continue the requested task.
- If the import path points to another worktree, ask for permission before deleting and recreating only the current worktree’s `backend/.venv`.
- Reinstall only when the environment is missing or dependencies changed.
- Declare backend dependencies in `backend/pyproject.toml`; frontend dependencies in `frontend/package.json`, committing the root `package-lock.json`.
- When adding or changing an environment variable or agent config, update `.env.example` and the corresponding README sections (Configuration, Environment variables) in the same change; add a Compose mapping if the backend container needs the variable.
- Type-check the frontend with `npm run typecheck -w frontend`.
- Do not commit `.venv`, `node_modules`, `.env`, coverage output, or cache directories.

## Restrictions

- do not commit anything to git unless told so explicitly
- never commit secrets into git, e.g., API keys
- never edit code without asking; this includes small fixes that are exempt from the full workflow below
- never modify the PostgreSQL data (`data/postgres` / `POSTGRES_DATA_DIR`), the database contents, or the Scrapyrus repository unless explicitly told to do so.
- never weaken read-only database access without explicit approval: the SQL tool must keep its `sql-data-guard` validation, and the `papyri_query_reader` login must stay limited to `SELECT`.

## Workflow

- when asked to make a larger change that introduces new or changes existing functionality (not just a one-line typo correction or a tiny bugfix), always follow this workflow. Small fixes skip this workflow but still require asking first:
  - follow a test-driven development approach. Tests come first (will fail, red phase), then code that fulfills them, then refactor as desired while preserving functionality and correctness.
  - propose an implementation plan for tests and implementation, surface any open elements that could change behavior or outcome.
  - present plan to the user for confirmation, and ask them to answer any open questions.
  - rework plan if asked for, answer all questions the user might have
  - plan is only ready to go when all open elements have been specified and the user confirms readiness.
  - write tests first and have user review them (red phase). Only proceed when they give the ok.
  - then write code to fulfill the tests (green phase). Present for review.
  - refactor as indicated until code is complete as reviewer judges it.

## Coding guidelines

- Adhere to SOLID principles:
  - single responsibility principle: One code unit (function, class, module) should have one single purpose
  - open-closed principle: Code should be open to extension, but closed to modification, i.e., we should not have to modify existing code extensively to extend the functionality of the system
  - liskov substitution: derived or child classes must be able to replace their parent classes, i.e., child classes should extend the parent classes without breaking the behavioral contract
  - interface segregation: A client should not be forced to depend on parts of an interface that is not relevant to it
  - dependency inversion: Higher-level elements of the code should not depend on lower-level elements of the code, both should depend on abstractions that define behavior, not restrict implementation.
- keep control flow and data flow as flat as possible. Go with the minimum amount of hierarchical depth that solves the problem at hand.
- avoid module-level variables
- use classes as soon as data and functions work together to create a functionality
- avoid deeply nested branching
- branches should be self-explanatory
- make branches explicit. Do not rely on handling a case by leaving it as the last one that's missing, rather use explicit if-elif-else blocks
- when writing tests, test behavior and state, not its implementation details
- keep the hot path of a function clean: configuration, parameter handling and preparation should happen on as high a level as possible
- handle edge cases explicitly. Do not rely on silent defaults that can alter behavior without the user knowing
- exceptions should be handled explicitly and early when they are expected or anticipated. In cases where unexpected/unanticipated things happen, make them bubble up to the highest level and handle them there. Lower-level code never catches `Exception`; only the top-level boundary (e.g., the API request handler) does. When re-raising as a project exception, chain with `from e` so the original traceback is kept. Define project-specific exceptions in `backend/src/papyri_backend/exceptions.py`:

```python
def low_level_step() -> Result:
    """Handles only anticipated exceptions; everything else propagates."""
    try:
        return func()
    except AnticipatedException1:  # might happen and we know what to do
        return handle_e1()
    except AnticipatedException2 as e:  # anticipated, re-raised in project terms
        raise SpecificErrorForThisCase("Specific message here") from e
    # no `except Exception` here: unexpected errors bubble up


def top_level_entry_point() -> Response:
    """The single place where unexpected exceptions are caught and handled."""
    try:
        return Response(low_level_step())
    except SpecificErrorForThisCase as e:
        return error_response(str(e))
    except Exception:
        logger.exception("Unexpected error")
        return internal_error_response()
```

- no changes to the code are made without a corresponding test of the new or changed functionality, but the removal of legacy functionality needs not be tested.
- all public methods and classes should have google style docstrings
- all private methods or classes should have at least freeform docstrings
- documentation is considered part of the code base and must be maintained alongside it.
- code should have explanatory comments that explain decisions taken where multiple alternatives would be possible or where a certain algorithm to solve a problem is first introduced
- all function arguments have type hints.
- adhere to clean code principles with practical application of the principles of "Clean Code" by Robert C. Martin, and "Refactoring" by Martin Fowler, but with relaxed rules on naming conventions and function length. The code should be readable and understandable, but not necessarily follow strict naming conventions or have very short functions. The focus is on clarity and maintainability rather than strict adherence to style guides.
