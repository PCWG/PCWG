# Power Curve Working Group collaborative</h1>
[PCWG Website](http://www.pcwg.org)

## Current Version
v0.5.1

## Release Versions
A full history of release versions can be found on [SourceForge](http://sourceforge.net/projects/pcwg/files/ "SourceForge")

v0.5.0 - 02/10/2014 - First release - [.exe(SourceForge)](http://sourceforge.net/projects/pcwg/files/pcwg-tool-0.5.0.zip/download "v0.5.0")

v0.5.1 - 20/03/2015 - Release prior to Hamburg meeting - [.exe(SourceForge)](http://sourceforge.net/projects/pcwg/files/pcwg-tool-0.5.1.zip/download "v0.5.1") 


### Filtering:
To apply filters to your data a simple filter node can be added to the configuration xml.

To filter timestamps when the shear exponent is above 0.2:
```xml
<ns1:Filter>
			<ns1:DataColumn>Shear Exponent</ns1:DataColumn>
			<ns1:FilterType>Above</ns1:FilterType>
			<ns1:Inclusive>0</ns1:Inclusive>
			<ns1:FilterValue>0.2</ns1:FilterValue>
			<ns1:Active>1</ns1:Active>
</ns1:Filter>
```

A filter can be applied that is a function of another data column.
The derivation is calculated in the form (A*COLUMN +B)^C
A, B and C are optional and default to 1,0 and 1 respectively.

For example, to apply the filter [Turbulence] > “WS_stddev/(0.75*WSmean+5.6)”:
```xml
<ns1:Filter>	
	<ns1:FilterType>Above</ns1:FilterType>
	<ns1:DataColumn>Hub Turbulence</ns1:DataColumn>
	<ns1:Inclusive>0</ns1:Inclusive>
	<ns1:Active>1</ns1:Active>			
	<ns1:FilterValue>
		<ns1:ColumnFactor>
			<ns1:ColumnName>Mast1_60m_StdDeviation</ns1:ColumnName>
			<ns1:A>1</ns1:A><ns1:B>0</ns1:B><ns1:C>-1</ns1:C>
		</ns1:ColumnFactor>	
		<ns1:ColumnFactor>
			<ns1:ColumnName>Mast1_60m_WindSpeed</ns1:ColumnName>
			<ns1:A>0.75</ns1:A><ns1:B>5.6</ns1:B><ns1:C>1</ns1:C>
		</ns1:ColumnFactor>	
	</ns1:FilterValue>	
</ns1:Filter>
```

Finally, data can be excluded using OR and AND relationships.
For example, to filter timestamps when [Power] < 0 AND 14.5 < [Wind speed] <= 20 :

```xml
<ns1:Filter>			
	<ns1:Active>1</ns1:Active>
	<ns1:Relationship>
		<ns1:Conjunction>AND</ns1:Conjunction>
		<ns1:Clause>
			<ns1:DataColumn>Actual Power</ns1:DataColumn>
			<ns1:FilterType>Below</ns1:FilterType>
			<ns1:Inclusive>0</ns1:Inclusive>
			<ns1:FilterValue>0</ns1:FilterValue>					
		</ns1:Clause>
		<ns1:Clause>
			<ns1:DataColumn>Hub Wind Speed</ns1:DataColumn>
			<ns1:FilterType>Between</ns1:FilterType>
			<ns1:Inclusive>0</ns1:Inclusive>
			<ns1:FilterValue>14.5,20.000001</ns1:FilterValue>					
		</ns1:Clause>	
	</ns1:Relationship>
</ns1:Filter>
```		

### AEP:

The power performance AEP can be calculated using the allMeasuredPowerCurve. This will be extended to be able to select the Inner and Outer ranges.
To do this a nominal wind speed distribution is needed. As an XML it should look like so:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns1:WindSpeedDistribution xmlns:ns1="http://www.pcwg.org" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<ns1:Bin><ns1:BinCentre>0</ns1:BinCentre><ns1:BinValue>9.9</ns1:BinValue></ns1:Bin>
<ns1:Bin><ns1:BinCentre>0.5</ns1:BinCentre><ns1:BinValue>28.4</ns1:BinValue></ns1:Bin>
<ns1:Bin><ns1:BinCentre>1</ns1:BinCentre><ns1:BinValue>51.4</ns1:BinValue></ns1:Bin>
<ns1:Bin><ns1:BinCentre>1.5</ns1:BinCentre><ns1:BinValue>86.3</ns1:BinValue></ns1:Bin>
...
<ns1:Bin><ns1:BinCentre>29</ns1:BinCentre><ns1:BinValue>0.091</ns1:BinValue></ns1:Bin>
<ns1:Bin><ns1:BinCentre>29.5</ns1:BinCentre><ns1:BinValue>0.068</ns1:BinValue></ns1:Bin>
<ns1:Bin><ns1:BinCentre>30</ns1:BinCentre><ns1:BinValue>0.011</ns1:BinValue></ns1:Bin>
<ns1:Bin><ns1:BinCentre>30.5</ns1:BinCentre><ns1:BinValue>0.006</ns1:BinValue></ns1:Bin>
</ns1:WindSpeedDistribution>
```
The AEP calculation first re-bins to 0.5 m/s bin widths.
