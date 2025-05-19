# Request

Please add WIS file support to read and export sensors' infomation. WIS is a xml file from Windograph. I will attach the wis file later.

Please analyze the wis file under example_project/nrg-data.wis.xml. 

Please do these
1. Separate the SensorColumn and ParsedSensor definition to a different file src/Types/SensorColumn.jl. And for all other files, search the SensorColumn import and change import path. Please remember to save
2. Under src/Types/SensorColumn.jl. Declare a function from_wis and to_wis without implementation for SensorColumn
3. Implement from_disk and to_disk. If yaml, use from_disk and to_disk. If wis, use from_wis and to_wis
4. Use from_disk and to_disk in commands. Both yaml and wis files shall be created. And the read SensorColumns shall be yaml first, wis second.
5. Change parse-sensors. If wis is given, get wis infomation and then generate yaml for sensorcolumns

After all these are implemented, then I will ask you to implement from_wis and to_wis

# Implementation Progress

# Result