import os
import pandas as pd

from ..core.status import Status
from ..core.turbine import PowerCurve

np = pd.np

def chckMake(path):
    """Make a folder if it doesn't exist"""
    if not os.path.exists(path):
        os.makedirs(path)

def _is_save_path_valid(full_path):
    if ((os.name == 'nt') and (len(full_path)>=260)):
        Status.add("Cannot save following file as path exceeds the Windows character limit of 259:")
        Status.add(full_path)
        return False
    else:
        return True
        

class MatplotlibPlotter(object):
    def __init__(self,path, analysis):
        self.path = path
        self.calibration_path = self.path + os.sep + 'Calibration Plots'
        self.analysis = analysis

    def plot_multiple(self, windSpeedCol, powerCol, meanPowerCurveObj):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            plotTitle = "Power Curve"

            meanPowerCurve = meanPowerCurveObj.data_frame[[windSpeedCol,powerCol,'Data Count']][meanPowerCurveObj.data_frame['Data Count'] > 0 ].reset_index().set_index(windSpeedCol)
            ax = meanPowerCurve[powerCol].plot(color='#00FF00',alpha=0.95,linestyle='--',label='Mean Power Curve')

            colourmap = plt.cm.gist_ncar
            colours = [colourmap(i) for i in np.linspace(0, 0.9, len(self.analysis.dataFrame[self.analysis.nameColumn].unique()))]

            for i,name in enumerate(self.analysis.dataFrame[self.analysis.nameColumn].unique()):
                ax = self.analysis.dataFrame[self.analysis.dataFrame[self.analysis.nameColumn] == name].plot(ax = ax, kind='scatter', x=windSpeedCol, y=powerCol, title=plotTitle, alpha=0.2, label=name, color = colours[i])

            ax.legend(loc=4, scatterpoints = 1)
            ax.set_xlim([min(self.analysis.dataFrame[windSpeedCol].min(),meanPowerCurve.index.min()), max(self.analysis.dataFrame[windSpeedCol].max(),meanPowerCurve.index.max()+2.0)])
            ax.set_xlabel(windSpeedCol + ' (m/s)')
            ax.set_ylabel(powerCol + ' (kW)')
            file_out = self.path + "/Multiple Dataset PowerCurve - " + powerCol + " vs " + windSpeedCol + ".png"
            chckMake(self.path)
            plt.savefig(file_out)
            plt.close()
            return file_out
        except:
            Status.add("Tried to make a power curve scatter chart for multiple data source (%s). Couldn't." % meanPowerCurveObj.name, verbosity=2)

    def plotPowerCurveSensitivityVariationMetrics(self):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            (self.analysis.powerCurveSensitivityVariationMetrics.dropna()*100.).plot(kind = 'bar', title = 'Summary of Power Curve Variation by Variable. Significance Threshold = %.2f%%' % (self.analysis.sensitivityAnalysisThreshold * 100), figsize = (12,8), fontsize = 6)
            plt.ylabel('Variation Metric (%)')
            file_out = self.path + os.sep + 'Power Curve Sensitivity Analysis Variation Metric Summary.png'
            plt.tight_layout()
            plt.savefig(file_out)
            plt.close('all')
        except:
            Status.add("Tried to plot summary of Power Curve Sensitivity Analysis Variation Metric. Couldn't.", verbosity=2)
        self.analysis.powerCurveSensitivityVariationMetrics.to_csv(self.path + os.sep + 'Power Curve Sensitivity Analysis Variation Metric.csv')

    def plotPowerCurveSensitivity(self, sensCol):
        try:
            df = self.analysis.powerCurveSensitivityResults[sensCol].reset_index()
            from matplotlib import pyplot as plt
            plt.ioff()
            fig = plt.figure(figsize = (12,5))
            fig.suptitle('Power Curve Sensitivity to %s' % sensCol)
            ax1 = fig.add_subplot(121)
            ax1.hold(True)
            ax2 = fig.add_subplot(122)
            ax2.hold(True)
            power_column = self.analysis.measuredTurbulencePower if self.analysis.turbRenormActive else self.analysis.actualPower
            for label in self.analysis.sensitivityLabels.keys():
                filt = df['Bin'] == label
                ax1.plot(df['Wind Speed Bin'][filt], df[power_column][filt], label = label, color = self.analysis.sensitivityLabels[label])
                ax2.plot(df['Wind Speed Bin'][filt], df['Energy Delta MWh'][filt], label = label, color = self.analysis.sensitivityLabels[label])
            ax1.set_xlabel('Wind Speed (m/s)')
            ax1.set_ylabel('Power (kW)')
            ax2.set_xlabel('Wind Speed (m/s)')
            ax2.set_ylabel('Energy Difference from Mean (MWh)')
            box1 = ax1.get_position()
            box2 = ax2.get_position()
            ax1.set_position([box1.x0 - 0.05 * box1.width, box1.y0 + box1.height * 0.17,
                         box1.width * 0.95, box1.height * 0.8])
            ax2.set_position([box2.x0 + 0.05 * box2.width, box2.y0 + box2.height * 0.17,
                         box2.width * 1.05, box2.height * 0.8])
            handles, labels = ax1.get_legend_handles_labels()
            fig.legend(handles, labels, loc='lower center', ncol = len(self.analysis.sensitivityLabels.keys()), fancybox = True, shadow = True)
            file_out = self.path + os.sep + 'Power Curve Sensitivity to %s.png' % sensCol
            chckMake(self.path)
            fig.savefig(file_out)
            plt.close()
        except:
            Status.add("Tried to make a plot of power curve sensitivity to %s. Couldn't." % sensCol, verbosity=2)

    def plotBy(self,by,variable,df, gridLines = False):

        if not isinstance(df,PowerCurve):
            kind = 'scatter'
        else:
            kind = 'line'
            df=df.data_frame[df.data_frame[self.analysis.baseline.wind_speed_column] <= self.analysis.allMeasuredPowerCurve.cut_out_wind_speed]
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            ax = df.plot(kind=kind,x=by ,y=variable,title=variable+" By " +by,alpha=0.6,legend=None)
            ax.set_xlim([df[by].min()-1,df[by].max()+1])
            ax.set_xlabel(by)
            ax.set_ylabel(variable)
            if gridLines:
                ax.grid(True)
            file_out = self.path + "/"+variable.replace(" ","_")+"_By_"+by.replace(" ","_")+".png"
            chckMake(self.path)
            plt.savefig(file_out)
            plt.close()
            return file_out
        except:
            Status.add("Tried to make a " + variable.replace(" ","_") + "_By_"+by.replace(" ","_")+" chart. Couldn't.", verbosity=2)

    def plotPowerCurve(self, windSpeedCol, powerCol, meanPowerCurveObj, show_scatter = True, anon = False, row_filt = None, fname = None, show_analysis_pc = True, specified_title = 'Specified', mean_title = 'Mean Power Curve', mean_pc_color = '#00FF00', gridLines = False):
        
        try:
            
            from matplotlib import pyplot as plt
            
            plt.ioff()
            df = self.analysis.dataFrame.loc[row_filt, :] if row_filt is not None else self.analysis.dataFrame
            
            plotTitle = "Power Curve ({0})".format(windSpeedCol)
            
            if show_scatter:
                ax = df.plot(kind='scatter', x=windSpeedCol, y=powerCol, title=plotTitle, alpha=0.15, label='Filtered Data')
            else:
                ax = df.plot(kind='scatter', x=windSpeedCol, y=powerCol, title=plotTitle, alpha=0.0)

            if self.analysis.specified_power_curve is not None:
                has_spec_pc = len(self.analysis.specified_power_curve.data_frame.index) != 0
            else:
                has_spec_pc = False

            if has_spec_pc:
                ax = self.analysis.specified_power_curve.data_frame.sort_index()['Specified Power'].plot(ax = ax, color='#FF0000',alpha=0.9,label=specified_title)
            
            if self.analysis.specified_power_curve != self.analysis.powerCurve:
                if ((self.analysis.powerCurve.name != 'All Measured') and show_analysis_pc):
                    ax = self.analysis.powerCurve.data_frame.sort_index()['Actual Power'].plot(ax = ax, color='#A37ACC',alpha=0.9,label=self.analysis.powerCurve.name)
            
            index = meanPowerCurveObj.data_frame.index
            columns = [windSpeedCol,powerCol,'Data Count']

            rows = meanPowerCurveObj.data_frame.loc[index, 'Data Count'] > 0

            meanPowerCurve = meanPowerCurveObj.data_frame[columns][rows].reset_index().set_index(windSpeedCol)

            ax = meanPowerCurve[powerCol].plot(ax = ax,color=mean_pc_color,alpha=0.95,linestyle='--',label=mean_title)
            ax.legend(loc=4, scatterpoints = 1)
            
            if has_spec_pc:
                ax.set_xlim([self.analysis.specified_power_curve.data_frame.index.min(), self.analysis.specified_power_curve.data_frame.index.max()+2.0])
            else:
                ax.set_xlim([min(df[windSpeedCol].min(),meanPowerCurve.index.min()), max(df[windSpeedCol].max(),meanPowerCurve.index.max()+2.0)])
            
            ax.set_xlabel(self.analysis.baseline.wind_speed_column + ' (m/s)')
            ax.set_ylabel(powerCol + ' (kW)')
            
            if anon:
                ax.xaxis.set_ticklabels([])
                ax.yaxis.set_ticklabels([])
            
            if gridLines:
                ax.grid(True)
            
            fname = ("PowerCurve - " + powerCol + " vs " + windSpeedCol + ".png") if fname is None else fname
            file_out = self.path + os.sep + fname
            chckMake(self.path)
            plt.savefig(file_out)
            plt.close()
        
            return file_out
        
        except:
            raise
            Status.add("Tried to make a power curve scatter chart for %s. Couldn't." % meanPowerCurveObj.name)

    def plotTurbCorrectedPowerCurve(self, windSpeedCol, powerCol, meanPowerCurveObj):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            if (windSpeedCol == self.analysis.densityCorrectedHubWindSpeed) or ((windSpeedCol == self.analysis.baseline.wind_speed_column) and (self.analysis.densityCorrectionActive)):
                plotTitle = "Power Curve (corrected to {dens} kg/m^3)".format(dens=self.analysis.referenceDensity)
            else:
                plotTitle = "Power Curve"
            ax = self.analysis.dataFrame.plot(kind='scatter', x=windSpeedCol, y=powerCol, title=plotTitle, alpha=0.15, label='Filtered Data')
            if self.analysis.specified_power_curve is not None:
                has_spec_pc = len(self.analysis.specified_power_curve.power_curve_levels.index) != 0
            else:
                has_spec_pc = False
            if has_spec_pc:
                ax = self.analysis.specified_power_curve.power_curve_levels.sort_index()['Specified Power'].plot(ax = ax, color='#FF0000',alpha=0.9,label='Specified')
            meanPowerCurve = meanPowerCurveObj.power_curve_levels[[windSpeedCol,powerCol,'Data Count']][self.analysis.allMeasuredPowerCurve.power_curve_levels['Data Count'] > 0 ].reset_index().set_index(windSpeedCol)
            ax = meanPowerCurve[powerCol].plot(ax = ax,color='#00FF00',alpha=0.95,linestyle='--',
                                  label='Mean Power Curve')
            ax2 = ax.twinx()
            if has_spec_pc:
                ax.set_xlim([self.analysis.specified_power_curve.power_curve_levels.index.min(), self.analysis.specified_power_curve.power_curve_levels.index.max()+2.0])
                ax2.set_xlim([self.analysis.specified_power_curve.power_curve_levels.index.min(), self.analysis.specified_power_curve.power_curve_levels.index.max()+2.0])
            else:
                ax.set_xlim([min(self.analysis.dataFrame[windSpeedCol].min(),meanPowerCurve.index.min()), max(self.analysis.dataFrame[windSpeedCol].max(),meanPowerCurve.index.max()+2.0)])
                ax2.set_xlim([min(self.analysis.dataFrame[windSpeedCol].min(),meanPowerCurve.index.min()), max(self.analysis.dataFrame[windSpeedCol].max(),meanPowerCurve.index.max()+2.0)])
            
            ax.set_xlabel(self.analysis.baseline.wind_speed_column + ' (m/s)')
            ax.set_ylabel(powerCol + ' (kW)')
            refTurbCol = 'Specified Turbulence' if self.analysis.powerCurveMode == 'Specified' else self.analysis.hubTurbulence
            ax2.plot(self.analysis.powerCurve.power_curve_levels.sort_index().index, self.analysis.powerCurve.power_curve_levels.sort_index()[refTurbCol] * 100., 'm--', label = 'Reference TI')
            ax2.set_ylabel('Reference TI (%)')
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1+h2, l1+l2, loc=4, scatterpoints = 1)
            file_out = self.path + "/PowerCurve TI Corrected - " + powerCol + " vs " + windSpeedCol + ".png"
            chckMake(self.path)
            plt.savefig(file_out)
            plt.close()
            return file_out
        except:
            Status.add("Tried to make a TI corrected power curve scatter chart for %s. Couldn't." % meanPowerCurveObj.name, verbosity=2)

    def plotPowerLimits(self, specified_title = 'Specified', gridLines = False):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            windSpeedCol = self.analysis.densityCorrectedHubWindSpeed
            ax = self.analysis.dataFrame.plot(kind='scatter',x=windSpeedCol,y=self.analysis.actualPower ,title="Power Values Corrected to {dens} kg/m^3".format(dens=self.analysis.referenceDensity),alpha=0.5,label='Power Mean')
            ax = self.analysis.dataFrame.plot(ax=ax,kind='scatter',x=windSpeedCol,y="Power Min",alpha=0.2,label='Power Min',color = 'orange')
            ax = self.analysis.dataFrame.plot(ax=ax,kind='scatter',x=windSpeedCol,y="Power Max",alpha=0.2,label='Power Max',color = 'green')
            ax = self.analysis.dataFrame.plot(ax=ax,kind='scatter',x=windSpeedCol,y="Power SD",alpha=0.2,label='Power SD',color = 'purple')
            ax = self.analysis.specified_power_curve.power_curve_levels.sort_index()['Specified Power'].plot(ax = ax, color='#FF0000',alpha=0.9,label=specified_title)
            ax.set_xlim([self.analysis.specified_power_curve.power_curve_levels.index.min(), self.analysis.specified_power_curve.power_curve_levels.index.max()+2.0])
            ax.legend(loc=4, scatterpoints = 1)
            ax.set_xlabel(windSpeedCol)
            ax.set_ylabel("Power [kW]")
            if gridLines:
                ax.grid(True)
            file_out = self.path + "/PowerValues.png"
            chckMake(self.path)
            plt.savefig(file_out)
            plt.close()
            return file_out
        except:
            Status.add("Tried to make a full power scatter chart. Couldn't.", verbosity=2)

    def plotCalibrationSectors(self):
        from matplotlib import pyplot as plt
        for datasetConf in self.analysis.datasetConfigs:
            if (datasetConf.calibrationMethod in ['York','LeastSquares']):
                chckMake(self.calibration_path)
                path = self.calibration_path + os.sep + datasetConf.name
                chckMake(path)
                if hasattr(datasetConf.data, 'calibrationSectorConverge'):
                    file_out = path + os.sep + 'Convergence Check Data.csv'
                    if _is_save_path_valid(file_out):
                        datasetConf.data.calibrationSectorConverge.to_csv(file_out)
                if hasattr(datasetConf.data, 'calibrationSectorConvergeSummary'):
                    file_out = path + os.sep + 'Convergence Check Summary.csv'
                    if _is_save_path_valid(file_out):
                        datasetConf.data.calibrationSectorConvergeSummary.to_csv(file_out)
                dir_bin_width = 360. / datasetConf.siteCalibrationNumberOfSectors / 2.
                try:
                    plt.ioff()
                    xlab, ylab = 'Direction Sector (deg)', '% Speed Up at 10m/s'
                    df = datasetConf.data.calibrationCalculator.calibrationSectorDataframe[['pctSpeedUp','LowerLimit','UpperLimit']].rename(columns={'pctSpeedUp':'% Speed Up','LowerLimit':"IEC Lower",'UpperLimit':"IEC Upper"})
                    df.plot(kind = 'line', figsize = (12,8), grid = True)
                    plt.xlabel(xlab)
                    plt.ylabel(ylab)
                    file_out = path + os.sep + 'Wind Speed Ratio with Direction - All Sectors.png'
                    plt.savefig(file_out)
                    df = df.loc[np.logical_and(df.index > datasetConf.data.fullDataFrame[datasetConf.data.referenceDirectionBin].min()-dir_bin_width , df.index < datasetConf.data.fullDataFrame[datasetConf.data.referenceDirectionBin].max()+dir_bin_width),:]
                    df.plot(kind = 'line', figsize = (12,8), grid = True)
                    plt.xlabel(xlab)
                    plt.ylabel(ylab)
                    file_out = path + os.sep + 'Wind Speed Ratio with Direction - Selected Sectors.png'
                    plt.savefig(file_out)
                    plt.close('all')
                except:
                    Status.add("Tried to plot variation of wind speed ratio with direction. Couldn't.", verbosity=2)
                xlim_u = datasetConf.data.filteredCalibrationDataframe[datasetConf.data.referenceWindSpeed].max()
                ylim_u = datasetConf.data.filteredCalibrationDataframe[datasetConf.data.turbineLocationWindSpeed].max()
                for directionBinCenter in datasetConf.data.filteredCalibrationDataframe[datasetConf.data.referenceDirectionBin].unique():
                    try:
                        plt.ioff()
                        df = datasetConf.data.filteredCalibrationDataframe.loc[datasetConf.data.filteredCalibrationDataframe[datasetConf.data.referenceDirectionBin] == directionBinCenter, [datasetConf.data.referenceWindSpeed, datasetConf.data.turbineLocationWindSpeed]]
                        ax = df.plot(kind='scatter', x=datasetConf.data.referenceWindSpeed, y=datasetConf.data.turbineLocationWindSpeed, alpha=0.6, legend=None)
                        ax.set_title("Site Calibration: Sector %s - %s" % (int(directionBinCenter-dir_bin_width), int(directionBinCenter+dir_bin_width)), fontsize=18)
                        ax.set_xlim([0, xlim_u])
                        ax.set_ylim([0, ylim_u])
                        ax.set_xlabel("Reference Mast Wind Speed (m/s)")
                        ax.set_ylabel("Turbine Mast Wind Speed (m/s)")
                        ax.grid(True)
                        xValuesForLine = [0, xlim_u]
                        slope = datasetConf.data.calibrationCalculator.calibrationSectorDataframe.loc[directionBinCenter,'Slope']
                        intercept = datasetConf.data.calibrationCalculator.calibrationSectorDataframe.loc[directionBinCenter,'Offset']
                        yValuesForLine = [x * slope + intercept for x in xValuesForLine]
                        plt.hold(True)
                        plt.plot(xValuesForLine, yValuesForLine)
                        file_out = path + os.sep + "SiteCalibrationScatter_(Sector_%03d_to_%03d).png" % (int(directionBinCenter-dir_bin_width), int(directionBinCenter+dir_bin_width))
                        plt.savefig(file_out)
                        plt.close()
                    except:
                        Status.add("Tried to plot reference vs turbine location wind speed for sector %s. Couldn't." % directionBinCenter, verbosity=2)