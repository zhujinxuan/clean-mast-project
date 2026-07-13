Preprocessed mast data in standard NRG/lidar CSV or Parquet format.

Place one file per site in this directory. File names are used as mast/lidar
names in downstream processing. Lidar names must begin with "L".

For raw logger exports, first put them in `pre-masts/` and run the
preprocessing pipeline to produce the files here.
