
from matplotlib import pyplot as plt
from ..core.status import Status

class PlotBase(object):

    def __init__(self, analysis):
        self.analysis = analysis

    def plot_by(self, by, variable, df, gridLines = False):

        ax = df.plot(kind='scatter',x=by ,y=variable,title=variable+" By " +by,alpha=0.6,legend=None)
        
        ax.set_xlim([df[by].min()-1,df[by].max()+1])
        ax.set_xlabel(by)
        ax.set_ylabel(variable)
        
        if gridLines:
            ax.grid(True)

        plt.show()