# `process clean` Command

This document explains the data cleaning workflow, which uses a two-step process: first recommending a configuration, and then executing the cleaning process based on that configuration.

## Prerequisites

Before running the cleaning commands, you must have successfully run the `project parse-sensors` command. The cleaning process depends on the standardized output from that step, which should be located in the `raw/` directory of your project.

## Step 1: Recommend a Configuration

The first step is to generate a configuration file for the cleaning process. The `recommend process-clean` command is designed to do this automatically.

### Command Execution

Run the following command from outside your project directory, using `nushell`:

```nushell
> julia path/to/CleanMastProject/bin/CleanMast.jl recommend process-clean path/to/my-project
```

### How it Works

This command will:
1.  Read your `parse-sensors.toml` file to find all the datasets you have processed.
2.  Identify which of those datasets are **mast data** (by checking if their time range is less than 5 years).
3.  For each mast dataset, it will create an entry in a new configuration file.
4.  It automatically sets the **input** for the cleaning step to be the **output** from the `parse-sensors` step.
5.  It sets up a default output path (`clean/`) and assigns a default set of cleaning rules (`formats/clean/default.toml`).

### Expected Result

This command will create a new file in your project directory: `process-clean.toml`.

**Example `process-clean.toml`:**
```toml
[[masts]]
  name = "MyMast"
  
  [masts.input]
    data = "raw/MyMast.csv"
    sensors = "raw/MyMast.sensors.toml"
    
  [masts.output]
    data = "./clean/MyMast.csv"
    sensors = "./clean/MyMast.sensors.toml"
    
  rules = "formats/clean/default.toml"
```

You can review and edit this file if you need to apply different cleaning rules or change the output paths.

## Step 2: Execute the Cleaning Process

Once you have a `process-clean.toml` file, you can run the `process clean` command.

### Command Execution

Run the following command from outside your project directory, using `nushell`:

```nushell
> julia path/to/CleanMastProject/bin/CleanMast.jl process clean path/to/my-project
```
*Note: The command implicitly finds and uses the `process-clean.toml` file within the specified project directory.*

### How it Works

The command will:
1.  Read the `process-clean.toml` file.
2.  Iterate through each `[[masts]]` entry.
3.  Load the specified input data and sensor metadata from the `raw/` directory.
4.  Apply the set of cleaning rules specified in the `rules` field.
5.  Log a summary of all the rule violations that were found and fixed.
6.  Save the cleaned `TimeSeriesData` to the specified `output` paths in the `clean/` directory.

### Expected Result

After the command completes, you will have a new `clean/` directory in your project containing the cleaned data and corresponding sensor files. The terminal will also display a summary of the cleaning process, detailing any violations that were corrected. 