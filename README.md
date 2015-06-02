# Power Curve Working Group collaborative</h1>
Tool for evaluating the power performance of wind turbines through power curve analysis.
[PCWG Website](http://www.pcwg.org)

## Current Version
v0.5.5

## Release Versions
A full history of release versions can be found on [SourceForge](http://sourceforge.net/projects/pcwg/files/ "SourceForge")



### Filtering:
To apply filters to your data a simple filter node can be added to the configuration xml.

To filter timestamps when the shear exponent is above 0.2:
```xml
<Filter>
			<DataColumn>Shear Exponent</DataColumn>
			<FilterType>Above</FilterType>
			<Inclusive>0</Inclusive>
			<FilterValue>0.2</FilterValue>
			<Active>1</Active>
</Filter>
```

A filter can be applied that is a function of another data column.
The derivation is calculated in the form (A*COLUMN +B)^C
A, B and C are optional and default to 1,0 and 1 respectively.

For example, to apply the filter [Turbulence] > “WS_stddev/(0.75*WSmean+5.6)”:
```xml
<Filter>	
	<FilterType>Above</FilterType>
	<DataColumn>Hub Turbulence</DataColumn>
	<Inclusive>0</Inclusive>
	<Active>1</Active>			
	<FilterValue>
		<ColumnFactor>
			<ColumnName>Mast1_60m_StdDeviation</ColumnName>
			<A>1</A><B>0</B><C>-1</C>
		</ColumnFactor>	
		<ColumnFactor>
			<ColumnName>Mast1_60m_WindSpeed</ColumnName>
			<A>0.75</A><B>5.6</B><C>1</C>
		</ColumnFactor>	
	</FilterValue>	
</Filter>
```

Data can be excluded using OR and AND relationships.
For example, to filter timestamps when [Power] < 0 AND 14.5 < [Wind speed] <= 20 :

```xml
<Filter>			
	<Active>1</Active>
	<Relationship>
		<Conjunction>AND</Conjunction>
		<Clause>
			<DataColumn>Actual Power</DataColumn>
			<FilterType>Below</FilterType>
			<Inclusive>0</Inclusive>
			<FilterValue>0</FilterValue>					
		</Clause>
		<Clause>
			<DataColumn>Hub Wind Speed</DataColumn>
			<FilterType>Between</FilterType>
			<Inclusive>0</Inclusive>
			<FilterValue>14.5,20.000001</FilterValue>					
		</Clause>	
	</Relationship>
</Filter>
```	

Time of day filters can be applied. Anything after StartTime AND before EndTime is excluded.
The days of the week are entered and separated by commas. MONDAY = 1, Sunday = 7 	

```xml
		<TimeOfDayFilter>
			<StartTime>08:00</StartTime>
			<EndTime>21:00</EndTime>
			<DaysOfTheWeek>1,2,3,4,5</DaysOfTheWeek>
			<Months>9,10,11</Months>
			<Active>1</Active>
		</TimeOfDayFilter>
```

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


