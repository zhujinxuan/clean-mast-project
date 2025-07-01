# `tower-shading` Command

This document explains the tower shading workflow, which uses a two-step process: first recommending a configuration, and then executing the tower shading correction based on that configuration.

## Prerequisites

Before running the tower shading commands, you must have successfully run the `process clean` command. The tower shading process depends on the cleaned data from that step, which should be located in the `clean/` directory of your project.

## Step 1: Recommend a Configuration

The first step is to generate a configuration file for the tower shading process. The `recommend tower-shading` command is designed to do this automatically.

### Command Execution

Run the following command from outside your project directory, using `nushell`:

```nushell
> julia path/to/CleanMastProject/bin/CleanMast.jl recommend tower-shading path/to/my-project
```

### How it Works

This command will:
1. Read your `process-clean.toml` file to find all the cleaned datasets.
2. For each mast dataset, it will create an entry in a new configuration file.
3. It automatically sets the **input** for the tower shading step to be the **output** from the `process clean` step.
4. It sets up a default output path (`tower-shading/`) for the corrected data.

### Expected Result

This command will create a new file in your project directory: `tower-shading.toml`.

**Example `tower-shading.toml`:**
```toml
# Tower Shading Configuration
# Merges wind speed sensors at nearby heights (within 2m) to handle tower shading effects

[[masts]]
name = "nrg-mast"

[masts.input]
  data = "./clean/nrg-mast.csv"
  sensors = "./clean/nrg-mast.sensors.yaml"

[masts.output]
  data = "./tower-shading/nrg-mast.csv"
  sensors = "./tower-shading/nrg-mast.sensors.yaml"
```

You can review and edit this file if you need to change the output paths or process specific masts only.

## Step 2: Execute the Tower Shading Process

Once you have a `tower-shading.toml` file, you can run the `process tower-shading` command.

### Command Execution

Run the following command from outside your project directory, using `nushell`:

```nushell
> julia path/to/CleanMastProject/bin/CleanMast.jl process tower-shading path/to/my-project/tower-shading.toml
```
*Note: Unlike some other commands, you need to specify the full path to the `tower-shading.toml` file.*

### How it Works

The command will:
1. Read the `tower-shading.toml` file.
2. Iterate through each `[[masts]]` entry.
3. Load the specified input data and sensor metadata from the `clean/` directory.
4. Identify wind speed sensors at similar heights (within 2 meters by default).
5. Merge sensors at the same height by taking the maximum value at each timestamp.
   - This corrects for tower shading effects where one sensor might be in the wake of the tower.
6. Create new merged sensors with standardized names (e.g., `WindSpeed_60m_avg_m/s`).
7. Remove the original directional sensors that were merged.
8. Save the corrected `TimeSeriesData` to the specified `output` paths in the `tower-shading/` directory.

### Tower Shading Algorithm Details

The tower shading correction works by:
- Finding all wind speed sensors at each unique height
- For sensors within 2m of each other, grouping them together
- For each group, creating a single merged sensor that takes the maximum value
- Preserving all non-wind speed sensors unchanged
- Maintaining separate sensors for different statistical types (avg, sd, min, max)

### Expected Result

After the command completes, you will have a new `tower-shading/` directory in your project containing the corrected data and corresponding sensor files. The terminal will display a summary showing:
- Which masts were processed
- The output file locations

**Example output:**
```
Processing tower shading...
Processing mast: nrg-mast
Tower shading processing completed for mast: nrg-mast
- Saved processed data to ./tower-shading/nrg-mast.csv
- Saved updated sensors to ./tower-shading/nrg-mast.sensors.yaml

Tower shading processing completed successfully.
```

The resulting sensor metadata will show merged sensors with generic direction indicators (N/A) instead of specific directional sensors (like 270° and 90°). 