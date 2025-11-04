# Parallel Cross-Mast Reconstruction

## Problem Description

### Symptom
During cross-mast reconstruction, the process fails with a file locking error:

```
❌ Step 10 failed: Base.IOError("unlink(\"projects/tgl-group1-10masts\\./reconstruct-cross\\originals\\M06.csv\"): resource busy or locked (EBUSY)", -4082)
```

This occurs specifically on Windows when multiple reconstruction jobs target the same mast.

### Root Cause Analysis

**Current Implementation:**
- Cross-mast reconstruction executes jobs **sequentially** in a single priority level
- Jobs are grouped by target mast: all jobs for M04, then all jobs for M02, etc.
- Example job sequence:
  ```
  Jobs 1-8:    M04 (reconstruct M04 from 8 different sources)
  Jobs 9-16:   M02 (reconstruct M02 from 8 different sources)
  ...
  Jobs 106-110: M06 (reconstruct M06 from 5 different sources)
  ```

**The File Locking Issue:**
1. Each job tries to backup the original input file before reconstruction
2. Multiple jobs targeting the same mast (e.g., M06) backup the same source file
3. On Windows, `cp(..., force=true)` tries to delete the existing backup file
4. File handles aren't released immediately, causing EBUSY error

**Example:**
- Job 109: M06 ← M11 creates backup `originals/M06.csv` (succeeds)
- Job 110: M06 ← M05 tries to overwrite `originals/M06.csv` (fails - file locked)

### Performance Issue

Beyond the file locking bug, the current implementation has a **critical performance problem**:
- All 110 jobs run **sequentially** despite being in the same priority level
- Jobs targeting different masts (M04, M02, M07, etc.) could run in parallel safely
- Current design wastes parallelization opportunities

**Job Structure Analysis:**
```
Current (Sequential):
  Job 1:  M04 ← M05  |
  Job 2:  M04 ← M02  | Sequential (cannot parallelize)
  Job 9:  M02 ← M04  |
  Job 10: M02 ← M01  |
  Job 17: M07 ← M04  |
  ...

Potential (Parallel):
  Batch 1: [M04←M05, M02←M04, M07←M04, M10←M04, ...] (all different targets)
  Batch 2: [M04←M02, M02←M01, M07←M02, M10←M02, ...] (all different targets)
  Batch 3: [M04←M03, M02←M03, M07←M01, M10←M01, ...] (all different targets)
```

## Proposed Solution: Option A - Parallel Job Scheduling

### Design Goals
1. **Eliminate file locking**: Ensure each target mast is backed up only once
2. **Enable parallelization**: Run jobs for different target masts concurrently
3. **Preserve reconstruction logic**: Maintain cumulative reconstruction semantics
4. **Thread safety**: Ensure no race conditions when accessing shared data

### Implementation Strategy

#### 1. Job Grouping Algorithm
Reorganize jobs into batches where each batch contains jobs with **unique target masts**:

```julia
function create_job_batches(jobs::Vector{ReconstructionJob})::Vector{Vector{ReconstructionJob}}
    batches = Vector{Vector{ReconstructionJob}}()
    remaining_jobs = copy(jobs)

    while !isempty(remaining_jobs)
        batch = Vector{ReconstructionJob}()
        used_targets = Set{String}()

        # Select jobs with unique targets for this batch
        jobs_to_remove = Int[]
        for (i, job) in enumerate(remaining_jobs)
            if !(job.target_mast in used_targets)
                push!(batch, job)
                push!(used_targets, job.target_mast)
                push!(jobs_to_remove, i)
            end
        end

        # Remove selected jobs from remaining
        deleteat!(remaining_jobs, jobs_to_remove)
        push!(batches, batch)
    end

    return batches
end
```

#### 2. Parallel Execution with ThreadsX

Replace the current sequential loop with parallel batch execution:

```julia
# Current (Sequential)
for priority_level in config.reconstruction_priorities
    for job in priority_level.jobs
        result = execute_reconstruction_job(job, mast_data, config, project_dir)
        push!(job_results, result)
    end
end

# Proposed (Parallel)
for priority_level in config.reconstruction_priorities
    # Group jobs into batches with unique targets
    job_batches = create_job_batches(priority_level.jobs)

    for batch in job_batches
        # Execute batch in parallel using ThreadsX
        batch_results = ThreadsX.map(batch) do job
            execute_reconstruction_job(job, mast_data, config, project_dir)
        end
        append!(job_results, batch_results)
    end
end
```

#### 3. Thread-Safe Backup Management

Implement backup tracking to ensure each target is backed up only once:

```julia
# Global backup tracking (thread-safe with locks)
const backup_lock = ReentrantLock()
const backed_up_targets = Set{String}()

function backup_original_files_threadsafe(job::ReconstructionJob,
                                          config::ReconstructCrossConfiguration,
                                          project_dir::String)
    lock(backup_lock) do
        if !(job.target_mast in backed_up_targets)
            backup_original_files(job, config, project_dir)
            push!(backed_up_targets, job.target_mast)
        end
    end
end
```

#### 4. Thread-Safe File I/O

Ensure that file writes for different targets don't interfere:
- Each target mast writes to a unique output file (already implemented)
- Use locks only for the backup operation
- Reconstruction I/O is naturally thread-safe due to unique output paths

#### 5. Parallel-Safe Logging

Replace sequential `println` logging with the project's existing `CleanMastLogging` infrastructure:

**Current Issue:**
- ProcessReconstructCrossCommand uses raw `println` calls for output
- `println` calls from multiple threads can interleave output
- Progress reporting becomes garbled in parallel execution

**Solution: Use Existing CleanMastLogging Infrastructure**

The project already has a comprehensive logging system under `src/Logging/` with:
- `CleanMastLogger`: Main logger creation with worker IDs
- `JSONLFileLogger`: Thread-safe file logging with `ReentrantLock` (line 14, 59)
- `TerminalFormatter`: Structured terminal output with color coding
- `LogRotation`: Automatic log file management

**Implementation:**

```julia
# At module level
using Logging
using ...CleanMastLogging: create_cleanmast_logger

function execute(config_path::String)::ReconstructionSummary
    config_dir = dirname(config_path)
    config_basename = splitext(basename(config_path))[1]

    # Create thread-safe logger (JSONLFileLogger already has ReentrantLock)
    logger = create_cleanmast_logger(
        job_name="reconstruct-cross",
        worker_id=1,
        config_dir=config_dir,
        config_basename=config_basename,
        terminal_level=Logging.Info,
        file_level=Logging.Debug
    )
    global_logger(logger)

    @info "Starting cross-mast reconstruction..."

    # Parallel execution with structured logging
    for priority_level in config.reconstruction_priorities
        job_batches = create_job_batches(priority_level.jobs)

        for (batch_idx, batch) in enumerate(job_batches)
            @info "Processing batch $batch_idx/$(length(job_batches))" n_jobs=length(batch)

            # Execute batch in parallel - logger is thread-safe
            batch_results = ThreadsX.map(batch) do job
                @info "Job started" target=job.target_mast source=job.source_mast
                result = execute_reconstruction_job(job, mast_data, config, project_dir)

                if result.success
                    @info "Job completed" target=job.target_mast source=job.source_mast
                else
                    @error "Job failed" target=job.target_mast error=result.error_message
                end

                return result
            end

            append!(job_results, batch_results)
        end
    end

    @info "Cross-mast reconstruction completed"
end
```

**Key Benefits:**
- ✅ **Thread-safe by design**: `JSONLFileLogger` already uses `ReentrantLock` for file writes
- ✅ **Structured logging**: All logs include worker_id, timestamps, job context
- ✅ **Consistent format**: Matches existing CleanMast logging patterns (e.g., ReportMesoTimeSeries)
- ✅ **File + Terminal**: Logs go to both JSONL file and formatted terminal output
- ✅ **No new dependencies**: Uses existing logging infrastructure

**Note:** The existing `JSONLFileLogger` at `src/Logging/JSONLLogger.jl:14` already implements thread-safe logging with a `ReentrantLock`, so no additional synchronization is needed for file I/O.

### Expected Benefits
1. **Eliminates file locking errors**: Each target backed up only once
2. **~10x speedup**: 11 targets can process in parallel (11 batches vs 110 sequential jobs)
3. **Better resource utilization**: Uses multiple CPU cores effectively
4. **Maintains correctness**: Same cumulative reconstruction semantics

### Implementation Checklist
- [ ] Add ThreadsX.jl dependency to Project.toml
- [ ] Implement `create_job_batches()` function
- [ ] Refactor main execution loop to use job batches
- [ ] Add thread-safe backup tracking
- [ ] Replace `println` calls with `CleanMastLogging` infrastructure
- [ ] Update progress reporting to use structured logging (`@info`, `@error`)
- [ ] Add configuration option for thread count
- [ ] Test with various job configurations
- [ ] Verify log file output is clean and parseable (JSONL format)

## Test Requirements

### Test Set: Job Scheduling Logic

Create a new test set `test/reconstruct_cross_scheduling.jl` to verify:

#### 1. Job Batching Tests
```julia
@testset "create_job_batches" begin
    # Test case: 3 targets, multiple jobs per target
    jobs = [
        ReconstructionJob(target_mast="M01", source_mast="M02", ...),
        ReconstructionJob(target_mast="M02", source_mast="M01", ...),
        ReconstructionJob(target_mast="M01", source_mast="M03", ...),
        ReconstructionJob(target_mast="M03", source_mast="M01", ...),
    ]

    batches = create_job_batches(jobs)

    # Verify batch properties
    @test length(batches) == 2  # Should create 2 batches

    # Verify batch 1 has unique targets
    targets_batch1 = Set([job.target_mast for job in batches[1]])
    @test length(targets_batch1) == length(batches[1])  # All unique

    # Verify all jobs are scheduled
    @test sum(length(b) for b in batches) == length(jobs)
end
```

#### 2. Backup Deduplication Tests
```julia
@testset "backup_deduplication" begin
    # Test that backup happens only once per target
    # Even when multiple jobs target the same mast
end
```

#### 3. Parallel Execution Tests
```julia
@testset "parallel_execution_correctness" begin
    # Test that parallel execution produces same results as sequential
    # Verify no race conditions in file I/O
    # Verify correct cumulative reconstruction
end
```

#### 4. Thread Safety Tests
```julia
@testset "thread_safety" begin
    # Test concurrent backup operations don't cause errors
    # Test concurrent file writes to different targets
end
```

#### 5. Logging Tests
```julia
@testset "parallel_logging" begin
    # Test that parallel logging produces clean, non-interleaved output
    # Verify JSONL log file is valid and parseable
    # Test that all job events are logged correctly
    # Verify structured logging fields (target, source, worker_id)
end
```

#### 6. Performance Benchmarks
```julia
@testset "performance_comparison" begin
    # Benchmark sequential vs parallel execution
    # Verify expected speedup with multiple threads
end
```

## Alternative Solutions (Not Recommended)

### Option B: Fix Backup Logic Only
- Track which targets have been backed up
- Skip redundant backups
- **Pros**: Quick fix, minimal code changes
- **Cons**: Doesn't enable parallelization, wastes performance

### Option C: Disable Backups
- Set `backup_originals = false` in config
- **Pros**: Immediate workaround
- **Cons**: Loses safety feature, doesn't address performance issue

## References

- Issue location: `src/ReconstructCross/ProcessReconstructCrossCommand.jl:502`
- Related config: `src/Types/ReconstructCrossConfig.jl:77`
- Example config: `projects/tgl-group1-10masts/reconstruct-cross.toml`
