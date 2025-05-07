import unittest
from .ips_common import IpsBaseTests

from utils.channel_access import ChannelAccess
from utils.ioc_launcher import ProcServLauncher, get_default_ioc_dir
from utils.test_modes import TestModes
from utils.testing import get_running_lewis_and_ioc, parameterized_list, unstable_test

DEVICE_PREFIX = "IPS_01"
EMULATOR_NAME = "ips"


IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("IPS"),
        "emulator": EMULATOR_NAME,
        "lewis_protocol": "ips_legacy",
        "ioc_launcher_class": ProcServLauncher,
        "macros": {
            "STREAMPROTOCOL": "LEGACY",
            "MANAGER_ASG": "DEFAULT",
            "MAX_SWEEP_RATE": "1.0",
            "HEATER_WAITTIME": "10",  # On a real system the macro has a default of 60s,
            # but speed it up a bit for the sake of tests.
        },
    },
]


# Only run tests in DEVSIM. Unable to produce detailed enough functionality to be useful in recsim.
TEST_MODES = [TestModes.DEVSIM]

TEST_VALUES = -0.12345, 6.54321  # Should be able to handle negative polarities
TEST_SWEEP_RATES = 0.001, 0.9876  # Rate can't be negative or >1

TOLERANCE = 0.0001

HEATER_OFF_STATES = ["Off Mag at 0", "Off Mag at F"]

ACTIVITY_STATES = ["Hold", "To Setpoint", "To Zero", "Clamped"]

# Generate all the control commands to test that remote and unlocked is set for
# Chain flattens the list
CONTROL_COMMANDS_WITH_VALUES = [
    ("FIELD", 0.1),
    ("FIELD:RATE", 0.1),
    ("SWEEPMODE:PARAMS", "Tesla Fast"),
]
for activity_state in ACTIVITY_STATES:
    CONTROL_COMMANDS_WITH_VALUES.append(("ACTIVITY", activity_state))
for heater_off_state in HEATER_OFF_STATES:
    CONTROL_COMMANDS_WITH_VALUES.append(("HEATER:STATUS", heater_off_state))

CONTROL_COMMANDS_WITHOUT_VALUES = ["SET:COMMSRES"]


class IpsLegacyTests(IpsBaseTests, unittest.TestCase):
    """
    Tests for the Ips legacy protocol IOC.
    """
    def _get_device_prefix(self):
        return DEVICE_PREFIX

    def _get_ioc_config(self):
        return IOCS

    def setUp(self):
        ioc_config = self._get_ioc_config()

        # Time to wait for the heater to warm up/cool down (extracted from IOC macros above)
        heater_wait_time = float((ioc_config[0].get("macros").get("HEATER_WAITTIME")))

        self._lewis, self._ioc = get_running_lewis_and_ioc(EMULATOR_NAME, DEVICE_PREFIX)
        # Some changes happen on the order of heater_wait_time seconds. Use a significantly longer timeout
        # to capture a few heater wait times plus some time for PVs to update.
        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX, default_timeout=heater_wait_time * 10)

        # Wait for some critical pvs to be connected.
        for pv in ["MAGNET:FIELD:PERSISTENT", "FIELD", "FIELD:SP:RBV", "HEATER:STATUS"]:
            self.ca.assert_that_pv_exists(pv)

        # Ensure in the correct mode
        self.ca.set_pv_value("CONTROL:SP", "Remote & Unlocked")
        self.ca.set_pv_value("ACTIVITY:SP", "To Setpoint")

        # Don't run reset as the sudden change of state confuses the IOC's state machine. No matter what the initial
        # state of the device the SNL should be able to deal with it.
        # self._lewis.backdoor_run_function_on_device("reset")

        self.ca.set_pv_value("FIELD:RATE:SP", 10)
        # self.ca.assert_that_pv_is_number("FIELD:RATE:SP", 10)

        self.ca.process_pv("FIELD:SP")

        # Wait for statemachine to reach "at field" state before every test.
        self.ca.assert_that_pv_is("STATEMACHINE", "At field")
