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
import random

from programmingtheiot.common import ConfigConst
from programmingtheiot.data.ActuatorData import ActuatorData
from programmingtheiot.cda.sim.BaseActuatorSimTask import BaseActuatorSimTask

class HvacActuatorSimTask(BaseActuatorSimTask):
	"""
	Shell representation of class for student implementation.
	
	"""

	def __init__(self):
		super(HvacActuatorSimTask, self).__init__(name = ConfigConst.HVAC_ACTUATOR_NAME, typeID = ConfigConst.HVAC_ACTUATOR_TYPE, simpleName="HVAC")


	def _activateActuator(self, val: float = ConfigConst.DEFAULT_VAL, stateData: str = None) -> int:
		duty = max(0.0, min(100.0, float(val)))

		logging.info("[HVAC] ON duty=%.1f state=%s", duty, stateData)

		return 0

	def _deactivateActuator(self, val: float = ConfigConst.DEFAULT_VAL, stateData: str = None) -> int:
		logging.info("[HVAC] OFF state=%s", stateData)
		return 0