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
		self.cpuUtilization = ConfigConst.DEFAULT_VAL
		self.diskUtilization = ConfigConst.DEFAULT_VAL
		self.memoryUtilization = ConfigConst.DEFAULT_VAL
	
	def getCpuUtilization(self):
		return self.cpuUtilization
	
	def getDiskUtilization(self):
		return self.diskUtilization
	
	def getMemoryUtilization(self):
		return self.memoryUtilization
	
	def setCpuUtilization(self, cpuUtil):
		self.cpuUtilization = cpuUtil
		self.updateTimeStamp()
	
	def setDiskUtilization(self, diskUtil):
		self.diskUtilization = diskUtil
		self.updateTimeStamp()
	
	def setMemoryUtilization(self, memUtil):
		self.memoryUtilization = memUtil
		self.updateTimeStamp()
	
	def _handleUpdateData(self, data):
		if data and isinstance(data, SystemPerformanceData):
			self.cpuUtilization = data.getCpuUtilization()
			self.diskUtilization = data.getDiskUtilization()
			self.memoryUtilization = data.getMemoryUtilization()
		else:
			self.hasError = True
			logging.error("Invalid data object passed to SystemPerformanceData _handleUpdateData.")
			return

	def __str__(self):
		"""
		Returns a string representation of this instance.
		
		@return str
		"""
		return "SystemPerformanceData [name=%s, typeID=%d, cpuUtilization=%.2f, diskUtilization=%.2f, memoryUtilization=%.2f, timeStamp=%s]" % (self.name, self.typeID, self.cpuUtilization, self.diskUtilization, self.memoryUtilization, self.timeStamp)