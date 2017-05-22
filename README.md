# Power Curve Working Group collaborative</h1>
Tool for evaluating the power performance of wind turbines through power curve analysis.
[PCWG Website](http://www.pcwg.org)

## Current Version
v0.7.0

## Release Versions
A full history of release versions can be found at https://github.com/peterdougstuart/PCWG/releases)

## Builds
[![Build status](https://ci.appveyor.com/api/projects/status/v7385dr5ina75l6x?svg=true)](https://ci.appveyor.com/project/peterdougstuart/pcwg)


### AEP:

The power performance AEP can be calculated using the allMeasuredPowerCurve. This will be extended to be able to select the Inner and Outer ranges.
To do this a nominal wind speed distribution is needed. As an XML it should look like so:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<WindSpeedDistribution xmlns:ns1="http://www.pcwg.org" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<Bin><BinCentre>0</BinCentre><BinValue>9.9</BinValue></Bin>
<Bin><BinCentre>0.5</BinCentre><BinValue>28.4</BinValue></Bin>
<Bin><BinCentre>1</BinCentre><BinValue>51.4</BinValue></Bin>
<Bin><BinCentre>1.5</BinCentre><BinValue>86.3</BinValue></Bin>
...
<Bin><BinCentre>29</BinCentre><BinValue>0.091</BinValue></Bin>
<Bin><BinCentre>29.5</BinCentre><BinValue>0.068</BinValue></Bin>
<Bin><BinCentre>30</BinCentre><BinValue>0.011</BinValue></Bin>
<Bin><BinCentre>30.5</BinCentre><BinValue>0.006</BinValue></Bin>
</WindSpeedDistribution>
```
The AEP calculation first re-bins to 0.5 m/s bin widths.


In the analysis config xml the following node should then be added:
```xml
<NominalWindSpeedDistribution>nwd_dist_filename.xml</NominalWindSpeedDistribution>
```


