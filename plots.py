import os
import pandas as pd
from Analysis import chckMake
np = pd.np

class MatplotlibPlotter(object):
    def __init__(self,path, analysis):
        self.path = path
        self.analysis = analysis

    def plot_multiple(self, windSpeedCol, powerCol, meanPowerCurveObj):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            plotTitle = "Power Curve"

            meanPowerCurve = meanPowerCurveObj.powerCurveLevels[[windSpeedCol,powerCol,'Data Count']][meanPowerCurveObj.powerCurveLevels['Data Count'] > 0 ].reset_index().set_index(windSpeedCol)
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
            print "Tried to make a power curve scatter chart for multiple data source (%s). Couldn't." % meanPowerCurveObj.name

    def plotPowerCurveSensitivityVariationMetrics(self):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            (self.analysis.powerCurveSensitivityVariationMetrics*100.).plot(kind = 'bar', title = 'Summary of Power Curve Variation by Variable. Significance Threshold = %.2f%%' % (self.analysis.sensitivityAnalysisThreshold * 100), figsize = (12,8))
            plt.ylabel('Variation Metric (%)')
            file_out = self.path + os.sep + 'Power Curve Sensitivity Analysis Variation Metric Summary.png'
            plt.savefig(file_out)
            plt.close('all')
        except:
            print "Tried to plot summary of Power Curve Sensitivity Analysis Variation Metric. Couldn't."
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
            print "Tried to make a plot of power curve sensitivity to %s. Couldn't." % sensCol

    def plotBy(self,by,variable,df):
        import turbine
        if not isinstance(df,turbine.PowerCurve):
            kind = 'scatter'
        else:
            kind = 'line'
            df=df.powerCurveLevels[df.powerCurveLevels['Input Hub Wind Speed'] <= self.analysis.allMeasuredPowerCurve.cutOutWindSpeed]
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            ax = df.plot(kind=kind,x=by ,y=variable,title=variable+" By " +by,alpha=0.6,legend=None)
            ax.set_xlim([df[by].min()-1,df[by].max()+1])
            ax.set_xlabel(by)
            ax.set_ylabel(variable)
            file_out = self.path + "/"+variable.replace(" ","_")+"_By_"+by.replace(" ","_")+".png"
            chckMake(self.path)
            plt.savefig(file_out)
            plt.close()
            return file_out
        except:
            print "Tried to make a " + variable.replace(" ","_") + "_By_"+by.replace(" ","_")+" chart. Couldn't."

    def plotPowerCurve(self, windSpeedCol, powerCol, meanPowerCurveObj, anon = False, row_filt = None, fname = None, show_analysis_pc = True, mean_title = 'Mean Power Curve', mean_pc_color = '#00FF00'):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            df = self.analysis.dataFrame.loc[row_filt, :] if row_filt is not None else self.analysis.dataFrame
            if (windSpeedCol == self.analysis.densityCorrectedHubWindSpeed) or ((windSpeedCol == self.analysis.inputHubWindSpeed) and (self.analysis.densityCorrectionActive)):
                plotTitle = "Power Curve (corrected to {dens} kg/m^3)".format(dens=self.analysis.referenceDensity)
            else:
                plotTitle = "Power Curve"
            ax = df.plot(kind='scatter', x=windSpeedCol, y=powerCol, title=plotTitle, alpha=0.15, label='Filtered Data')
            if self.analysis.specifiedPowerCurve is not None:
                has_spec_pc = len(self.analysis.specifiedPowerCurve.powerCurveLevels.index) != 0
            else:
                has_spec_pc = False
            if has_spec_pc:
                ax = self.analysis.specifiedPowerCurve.powerCurveLevels.sort_index()['Specified Power'].plot(ax = ax, color='#FF0000',alpha=0.9,label='Specified')
            if self.analysis.specifiedPowerCurve != self.analysis.powerCurve:
                if ((self.analysis.powerCurve.name != 'All Measured') and show_analysis_pc):
                    ax = self.analysis.powerCurve.powerCurveLevels.sort_index()['Actual Power'].plot(ax = ax, color='#A37ACC',alpha=0.9,label=self.analysis.powerCurve.name)
            meanPowerCurve = meanPowerCurveObj.powerCurveLevels[[windSpeedCol,powerCol,'Data Count']][self.analysis.allMeasuredPowerCurve.powerCurveLevels.loc[meanPowerCurveObj.powerCurveLevels.index, 'Data Count'] > 0].reset_index().set_index(windSpeedCol)
            ax = meanPowerCurve[powerCol].plot(ax = ax,color=mean_pc_color,alpha=0.95,linestyle='--',
                                  label=mean_title)
            ax.legend(loc=4, scatterpoints = 1)
            if has_spec_pc:
                ax.set_xlim([self.analysis.specifiedPowerCurve.powerCurveLevels.index.min(), self.analysis.specifiedPowerCurve.powerCurveLevels.index.max()+2.0])
            else:
                ax.set_xlim([min(df[windSpeedCol].min(),meanPowerCurve.index.min()), max(df[windSpeedCol].max(),meanPowerCurve.index.max()+2.0)])
            ax.set_xlabel(self.analysis.inputHubWindSpeedSource + ' (m/s)')
            ax.set_ylabel(powerCol + ' (kW)')
            if anon:
                ax.xaxis.set_ticklabels([])
                ax.yaxis.set_ticklabels([])
            fname = ("PowerCurve - " + powerCol + " vs " + windSpeedCol + ".png") if fname is None else fname
            file_out = self.path + os.sep + fname
            chckMake(self.path)
            plt.savefig(file_out)
            plt.close()
            return file_out
        except:
            raise
            print "Tried to make a power curve scatter chart for %s. Couldn't." % meanPowerCurveObj.name

    def plotTurbCorrectedPowerCurve(self, windSpeedCol, powerCol, meanPowerCurveObj):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            if (windSpeedCol == self.analysis.densityCorrectedHubWindSpeed) or ((windSpeedCol == self.analysis.inputHubWindSpeed) and (self.analysis.densityCorrectionActive)):
                plotTitle = "Power Curve (corrected to {dens} kg/m^3)".format(dens=self.analysis.referenceDensity)
            else:
                plotTitle = "Power Curve"
            ax = self.analysis.dataFrame.plot(kind='scatter', x=windSpeedCol, y=powerCol, title=plotTitle, alpha=0.15, label='Filtered Data')
            if self.analysis.specifiedPowerCurve is not None:
                has_spec_pc = len(self.analysis.specifiedPowerCurve.powerCurveLevels.index) != 0
            else:
                has_spec_pc = False
            if has_spec_pc:
                ax = self.analysis.specifiedPowerCurve.powerCurveLevels.sort_index()['Specified Power'].plot(ax = ax, color='#FF0000',alpha=0.9,label='Specified')
            meanPowerCurve = meanPowerCurveObj.powerCurveLevels[[windSpeedCol,powerCol,'Data Count']][self.analysis.allMeasuredPowerCurve.powerCurveLevels['Data Count'] > 0 ].reset_index().set_index(windSpeedCol)
            ax = meanPowerCurve[powerCol].plot(ax = ax,color='#00FF00',alpha=0.95,linestyle='--',
                                  label='Mean Power Curve')
            ax2 = ax.twinx()
            if has_spec_pc:
                ax.set_xlim([self.analysis.specifiedPowerCurve.powerCurveLevels.index.min(), self.analysis.specifiedPowerCurve.powerCurveLevels.index.max()+2.0])
                ax2.set_xlim([self.analysis.specifiedPowerCurve.powerCurveLevels.index.min(), self.analysis.specifiedPowerCurve.powerCurveLevels.index.max()+2.0])
            else:
                ax.set_xlim([min(self.analysis.dataFrame[windSpeedCol].min(),meanPowerCurve.index.min()), max(self.analysis.dataFrame[windSpeedCol].max(),meanPowerCurve.index.max()+2.0)])
                ax2.set_xlim([min(self.analysis.dataFrame[windSpeedCol].min(),meanPowerCurve.index.min()), max(self.analysis.dataFrame[windSpeedCol].max(),meanPowerCurve.index.max()+2.0)])
            
            ax.set_xlabel(self.analysis.inputHubWindSpeedSource + ' (m/s)')
            ax.set_ylabel(powerCol + ' (kW)')
            refTurbCol = 'Specified Turbulence' if self.analysis.powerCurveMode == 'Specified' else self.analysis.hubTurbulence
            ax2.plot(self.analysis.powerCurve.powerCurveLevels.sort_index().index, self.analysis.powerCurve.powerCurveLevels.sort_index()[refTurbCol] * 100., 'm--', label = 'Reference TI')
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
            print "Tried to make a TI corrected power curve scatter chart for %s. Couldn't." % meanPowerCurveObj.name

    def plotPowerLimits(self):
        try:
            from matplotlib import pyplot as plt
            plt.ioff()
            windSpeedCol = self.analysis.densityCorrectedHubWindSpeed
            ax = self.analysis.dataFrame.plot(kind='scatter',x=windSpeedCol,y=self.analysis.actualPower ,title="Power Values Corrected to {dens} kg/m^3".format(dens=self.analysis.referenceDensity),alpha=0.5,label='Power Mean')
            ax = self.analysis.dataFrame.plot(ax=ax,kind='scatter',x=windSpeedCol,y="Power Min",alpha=0.2,label='Power Min',color = 'orange')
            ax = self.analysis.dataFrame.plot(ax=ax,kind='scatter',x=windSpeedCol,y="Power Max",alpha=0.2,label='Power Max',color = 'green')
            ax = self.analysis.dataFrame.plot(ax=ax,kind='scatter',x=windSpeedCol,y="Power SD",alpha=0.2,label='Power SD',color = 'purple')
            ax = self.analysis.specifiedPowerCurve.powerCurveLevels.sort_index()['Specified Power'].plot(ax = ax, color='#FF0000',alpha=0.9,label='Specified')
            ax.set_xlim([self.analysis.specifiedPowerCurve.powerCurveLevels.index.min(), self.analysis.specifiedPowerCurve.powerCurveLevels.index.max()+2.0])
            ax.legend(loc=4, scatterpoints = 1)
            ax.set_xlabel(windSpeedCol)
            ax.set_ylabel("Power [kW]")
            file_out = self.path + "/PowerValues.png"
            chckMake(self.path)
            plt.savefig(file_out)
            plt.close()
            return file_out
        except:
            print "Tried to make a full power scatter chart. Couldn't."

    def plotCalibrationSectors(self):
        for datasetConf in self.analysis.datasetConfigs:
            try:
                from matplotlib import pyplot as plt
                plt.ioff()
                df = datasetConf.data.calibrationCalculator.calibrationSectorDataframe[['pctSpeedUp','LowerLimit','UpperLimit']].rename(columns={'pctSpeedUp':'% Speed Up','LowerLimit':"IEC Lower",'UpperLimit':"IEC Upper"})
                df.plot(kind = 'line', title = 'Variation of wind speed ratio with direction', figsize = (12,8))
                plt.ylabel('Wind Speed Ratio (Vturb/Vref) as %')
                file_out = self.path + os.sep + 'Wind Speed Ratio with Direction - All Sectors {nm}.png'.format(nm=datasetConf.name)
                plt.savefig(file_out)
                df = df.loc[np.logical_and(df.index > datasetConf.data.fullDataFrame[datasetConf.data.referenceDirectionBin].min()-5.0 , df.index < datasetConf.data.fullDataFrame[datasetConf.data.referenceDirectionBin].max()+5.0),:]
                df.plot(kind = 'line', title = 'Variation of wind speed ratio with direction', figsize = (12,8))
                plt.ylabel('Wind Speed Ratio (Vturb/Vref) as %')
                file_out = self.path + os.sep + 'Wind Speed Ratio with Direction - Selected Sectors {nm}.png'.format(nm=datasetConf.name)
                chckMake(self.path)
                plt.savefig(file_out)
                plt.close('all')
            except:
                print "Tried to plot variation of wind speed ratio with direction. Couldn't."
