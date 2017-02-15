
from share1 import ShareAnalysis1
from share1_dot_1 import ShareAnalysis1Dot1
from share2 import ShareAnalysis2

class ShareAnalysisFactory(object):

	def __init__(self, share_name):

		self.share_name = share_name

	def new_share_analysis(self, config):

		if self.share_name == "Share01":
			return ShareAnalysis1(config)
		elif self.share_name == "Share01.1":
			return ShareAnalysis1Dot1(config)
		elif self.share_name == "Share02":
			return ShareAnalysis2(config)
		else:
			raise Exception("Unexpected share: {0}".format(self.share_name))