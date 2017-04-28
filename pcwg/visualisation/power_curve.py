
from matplotlib import pyplot as plt
from ..core.status import Status

class PowerCurvePlotter(object):

    def __init__(self, analysis):
        self.analysis = analysis

    def plot(self, windSpeedCol, powerCol, meanPowerCurveObj, show_scatter = True, row_filt = None, fname = None, show_analysis_pc = True, specified_title = 'Specified', mean_title = 'Mean Power Curve', mean_pc_color = '#00FF00', gridLines = False):
        
        #plt.plot([1,2,3,4])
        #plt.ylabel('some numbers')
        #plt.show()
        #return

        #plt.ioff()
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
        rows = self.analysis.allMeasuredPowerCurve.data_frame.loc[index, 'Data Count'] > 0

        meanPowerCurve = meanPowerCurveObj.data_frame[columns][rows].reset_index().set_index(windSpeedCol)

        ax = meanPowerCurve[powerCol].plot(ax = ax,color=mean_pc_color,alpha=0.95,linestyle='--',label=mean_title)
        ax.legend(loc=4, scatterpoints = 1)
        
        if has_spec_pc:
            ax.set_xlim([self.analysis.specified_power_curve.data_frame.index.min(), self.analysis.specified_power_curve.data_frame.index.max()+2.0])
        else:
            ax.set_xlim([min(df[windSpeedCol].min(),meanPowerCurve.index.min()), max(df[windSpeedCol].max(),meanPowerCurve.index.max()+2.0)])
        
        ax.set_xlabel(self.analysis.baseline.wind_speed_column + ' (m/s)')
        ax.set_ylabel(powerCol + ' (kW)')
                
        if gridLines:
            ax.grid(True)

        plt.show()
        
    def plot_multiple(self, windSpeedCol, powerCol, meanPowerCurveObj):

        #plt.ioff()
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


