#####
# 
# This class is part of the Programming the Internet of Things
# project, and is available via the MIT License, which can be
# found in the LICENSE file at the top level of this repository.
# 
# You may find it more helpful to your design to adjust the
# functionality, constants and interfaces (if there are any)
# provided within in order to meet the needs of your specific
# Programming the Internet of Things project.
# 

import logging
import programmingtheiot.common.ConfigConst as ConfigConst

from programmingtheiot.data.BaseIotData import BaseIotData

logging.basicConfig(format = '%(asctime)s:%(name)s:%(levelname)s:%(message)s', level = logging.DEBUG)
class SystemPerformanceData(BaseIotData):
	"""
	Shell representation of class for student implementation.
	
	"""
	DEFAULT_VAL = 0.0
	
	def __init__(self, typeID: int = ConfigConst.SYSTEM_PERF_TYPE, name = ConfigConst.SYSTEM_PERF_MSG, d = None):
		super(SystemPerformanceData, self).__init__(name = name, typeID = typeID, d = d)
		self.cpuUtil = ConfigConst.DEFAULT_VAL
		self.diskUtil = ConfigConst.DEFAULT_VAL
		self.memUtil = ConfigConst.DEFAULT_VAL

	def getCpuUtilization(self):
		return self.cpuUtil

	def getDiskUtilization(self):
		return self.diskUtil

	def getMemoryUtilization(self):
		return self.memUtil

	def setCpuUtilization(self, cpuUtil):
		self.cpuUtil = cpuUtil
		self.updateTimeStamp()

	def setDiskUtilization(self, diskUtil):
		self.diskUtil = diskUtil
		self.updateTimeStamp()

	def setMemoryUtilization(self, memUtil):
		self.memUtil = memUtil
		self.updateTimeStamp()

	def _handleUpdateData(self, data):
		if data and isinstance(data, SystemPerformanceData):
			self.cpuUtil = data.getCpuUtilization()
			self.diskUtil = data.getDiskUtilization()
			self.memUtil = data.getMemoryUtilization()
		else:
			self.hasError = True
			logging.error("Invalid data object passed to SystemPerformanceData _handleUpdateData.")
			return

	def __str__(self):
		"""
		Returns a string representation of this instance.

		@return str
		"""
		return "SystemPerformanceData [name=%s, typeID=%d, cpuUtil=%.2f, diskUtil=%.2f, memUtil=%.2f, timeStamp=%s]" % (self.name, self.typeID, self.cpuUtil, self.diskUtil, self.memUtil, self.timeStamp)