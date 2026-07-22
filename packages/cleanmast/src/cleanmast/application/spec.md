## Code rules

### Purpose
Application usecases orchestrate: load data via repository protocol, invoke domain
services, persist results. They are the boundary between infrastructure (I/O)
and domain (pure computation).

### Rules
- Usecases accept `TimeSeriesRepository` protocol as a parameter; never construct
  concrete repos.
- Usecases load `TimeSeriesData` via `repo.load()`, then pass `TimeSeriesData`
  to domain functions — domain never sees `TimeSeriesSource`.
- One mast at a time: usecases loop, load per mast, call domain per mast.

### Anti-patterns
- `from cleanmast.infrastructure.file_repository import FileTimeSeriesRepository`
  inside an application usecase.
- Passing `TimeSeriesSource` across the boundary into dataprocessing.

### When in doubt
- If a function loads data → it belongs in application, not dataprocessing.
