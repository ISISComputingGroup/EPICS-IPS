import unittest

from parameterized import parameterized # pyright: ignore
from utils.channel_access import ChannelAccess # pyright: ignore
from utils.ioc_launcher import get_default_ioc_dir # pyright: ignore
from utils.test_modes import TestModes # pyright: ignore
from utils.testing import get_running_lewis_and_ioc, parameterized_list # pyright: ignore

from .ips_common import IpsBaseTests

DEVICE_PREFIX = "IPS_01"
EMULATOR_NAME = "ips"

# Tell ruff to ignore the N802 warning (function name should be lowercase).
# Names contain GIVEN, WHEN, THEN
# Ignore line length as well, as this is a common pattern in tests.
# ruff: noqa: N802, E501

IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("IPS"),
        "emulator": EMULATOR_NAME,
        "lewis_protocol": "ips_scpi",
        # "ioc_launcher_class": ProcServLauncher,
        "macros": {
            "STREAMPROTOCOL": "SCPI",
            "MANAGER_ASG": "DEFAULT",
            "MAX_SWEEP_RATE": "1.0",
            "HEATER_WAITTIME": "10",  # On a real system the macro has a default of 60s,
            # but speed it up a bit for the sake of tests.
        },
    },
]


# Only run tests in DEVSIM. Unable to produce detailed enough functionality to be useful in recsim.
TEST_MODES = [TestModes.DEVSIM]

TEST_VALUES = [-0.12345, 6.54321]  # Should be able to handle negative polarities
TEST_SWEEP_RATES = [0.001, 0.9876]  # Rate can't be negative or >1
TEST_NITROGEN_LEVEL_FREQ_VALUES = [5000, 32000, 65000]  # Frequency values for testing
TEST_HE_LEVEL_RESISTANCE_VALUES = [0.0, 0.1, 10, 25]  # Resistance values for testing
TEST_NITROGEN_LEVEL_VALUES = [0, 10, 50, 95]  # Nitrogen level values for testing
TEST_HELIUM_LEVEL_VALUES = [0, 10, 50, 95]  # Helium level values for testing

# Setting the default nitrogen fill start and stop levels
NITROGEN_FILL_START_LEVEL = 10
NITROGEN_FILL_STOP_LEVEL = 90

TOLERANCE = 0.0001

HEATER_OFF_STATES = ["Off",]

ACTIVITY_STATES = ["Hold", "To Setpoint", "To Zero", "Clamped"]


class IpsSCPITests(IpsBaseTests, unittest.TestCase):
    """
    Tests for the Ips SCPI protocol IOC.
    """
    def _get_device_prefix(self) -> str:
        return DEVICE_PREFIX

    def _get_ioc_config(self) -> list[dict]:
        return IOCS

    def setUp(self) -> None:
        ioc_config = self._get_ioc_config()

        # Time to wait for the heater to warm up/cool down (extracted from IOC macros above)
        heater_wait_time = float((ioc_config[0].get("macros").get("HEATER_WAITTIME"))) # pyright: ignore

        self._lewis, self._ioc = get_running_lewis_and_ioc(EMULATOR_NAME, DEVICE_PREFIX)
        # Some changes happen on the order of HEATER_WAIT_TIME seconds.
        # Use a significantly longer timeout to capture a few heater wait times
        # plus some time for PVs to update.
        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX, default_timeout=heater_wait_time * 10)

        # Wait for some critical pvs to be connected.
        for pv in ["MAGNET:FIELD:PERSISTENT", "FIELD", "FIELD:SP:RBV", "HEATER:STATUS"]:
            self.ca.assert_that_pv_exists(pv)

        # Ensure in the correct mode
        # The following call was in the original legacy test code but is not needed
        # in the SCPI version.
        # self.ca.set_pv_value("CONTROL:SP", "Off") 
        # Remote and Unlocked

        self.ca.set_pv_value("ACTIVITY:SP", "To Setpoint")

        # Don't run reset as the sudden change of state confuses the IOC's state machine. 
        # No matter what the initial state of the device the SNL should be able to deal with it.
        # self._lewis.backdoor_run_function_on_device("reset")

        self.ca.set_pv_value("FIELD:RATE:SP", 1)
        self.ca.assert_that_pv_is_number("FIELD:RATE:SP", 1, tolerance=TOLERANCE)

        self.ca.process_pv("FIELD:SP")

        # Wait for statemachine to reach "at field" state before every test.
        self.ca.assert_that_pv_is("STATEMACHINE", "At field")

    def _assert_heater_is(self, heater_state: bool) -> None:
        self.ca.assert_that_pv_is("HEATER:STATUS:SP", "On" if heater_state else "Off")
        if heater_state:
            self.ca.assert_that_pv_is(
                "HEATER:STATUS",
                "On",
            )
        else:
            self.ca.assert_that_pv_is(
                "HEATER:STATUS",
                "Off",
            )


    @parameterized.expand(field for field in parameterized_list(TEST_VALUES))
    def test_GIVEN_magnet_quenches_while_at_field_THEN_ioc_displays_this_quench_in_statuses(
        self, _: str, field: float ) -> None:
        
        self._set_and_check_persistent_mode(False)
        self.ca.set_pv_value("FIELD:SP", field)
        self._assert_field_is(field)
        self.ca.assert_that_pv_is("STATEMACHINE", "At field")

        with self._backdoor_magnet_quench():
            self.ca.assert_that_pv_is("STS:SYSTEM:FAULT", "Quenched")
            self.ca.assert_that_pv_alarm_is("STS:SYSTEM:FAULT", self.ca.Alarms.MAJOR)

            # Field should be set to zero by emulator
            # (mirroring what the field ought to do in the real device)
            self.ca.assert_that_pv_is_number("FIELD", 0, tolerance=TOLERANCE)
            self.ca.assert_that_pv_is_number("FIELD:USER", 0, tolerance=TOLERANCE)
            self.ca.assert_that_pv_is_number("MAGNET:FIELD:PERSISTENT",
                                        0, tolerance=TOLERANCE)

    def test_GIVEN_magnet_temperature_sensor_open_circuit_THEN_ioc_states_open_circuit(
        self) -> None:
        # Simulate an open circuit on the temperature sensor
        self._lewis.backdoor_run_function_on_device("set_tempboard_status", [1])
        self.ca.assert_that_pv_is("STS:SYSTEM:ALARM:TBOARD.B0", "1", timeout=10)

    def test_GIVEN_level_sensor_short_circuit_THEN_ioc_states_short_circuit(
        self) -> None:
        # Simulate an short circuit on the level sensor
        self._lewis.backdoor_run_function_on_device("set_levelboard_status", [2])
        self.ca.assert_that_pv_is("STS:SYSTEM:ALARM:LBOARD.B1", "1", timeout=10)

    def test_WHEN_SYSALARM_Tboard_is_firmware_error_THEN_ioc_states_firmware_error(
        self) -> None:
        """
        Test that the SYSALARM TBOARD PV is set to 'Firmware Error' when the temperature board
        firmware is in error state.
        """
        self._lewis.backdoor_run_function_on_device("set_tempboard_status", [3])
        self.ca.assert_that_pv_is("STS:SYSTEM:ALARM:TBOARD.B2", '1', timeout=10)

    @parameterized.expand(val for val in parameterized_list(TEST_NITROGEN_LEVEL_FREQ_VALUES))
    def test_GIVEN_level_freq_at_zero_THEN_ioc_states_freq(self, _: str, val: float) -> None:
        # Simulate the nitrogen frequency at zero
        self.ca.set_pv_value("LVL:NIT:FREQ:ZERO:SP", val)
        self.ca.assert_that_pv_is_number("LVL:NIT:FREQ:ZERO", val,
                                         tolerance=TOLERANCE, timeout=10)

    @parameterized.expand(val for val in parameterized_list(TEST_NITROGEN_LEVEL_FREQ_VALUES))
    def test_GIVEN_level_freq_at_full_THEN_ioc_states_freq(self, _: str, val: float) -> None:
        # Simulate the nitrogen frequency at full
        self.ca.set_pv_value("LVL:NIT:FREQ:FULL:SP", val)
        self.ca.assert_that_pv_is_number("LVL:NIT:FREQ:FULL", val, tolerance=TOLERANCE, timeout=10)

    @parameterized.expand(val for val in parameterized_list(TEST_HE_LEVEL_RESISTANCE_VALUES))
    def test_given_level_resistance_empty_THEN_ioc_states_resistance(self, _: str,
                                                                     val: float) -> None:
        # Simulate the helium level resistance when empty
        self.ca.set_pv_value("LVL:HE:EMPTY:RES:SP", val)
        self.ca.assert_that_pv_is_number("LVL:HE:EMPTY:RES", val,
                                         tolerance=TOLERANCE, timeout=10)

    @parameterized.expand(val for val in parameterized_list(TEST_HE_LEVEL_RESISTANCE_VALUES))
    def test_given_level_resistance_full_THEN_ioc_states_resistance(self, _: str,
                                                                    val: float) -> None:
        # Simulate the helium level resistance when empty
        self.ca.set_pv_value("LVL:HE:FULL:RES:SP", val)
        self.ca.assert_that_pv_is_number("LVL:HE:FULL:RES", val,
                                         tolerance=TOLERANCE, timeout=10)

    def test_WHEN_nitrogen_read_interval_set_THEN_ioc_updates_read_interval(self) -> None:
        """
        Test that the nitrogen read interval can be set and is reflected in the IOC.
        """
        # Set the nitrogen read interval
        self.ca.set_pv_value("LVL:NIT:READ:INTERVAL:SP", 1000)
        self.ca.assert_that_pv_is_number("LVL:NIT:READ:INTERVAL",
                                         1000, tolerance=TOLERANCE)
        
    def test_WHEN_helium_read_rate_set_THEN_ioc_updates_read_rate(self) -> None:
        """
        Test that the helium read rate can be set and is reflected in the IOC.
        """
        # Set the helium read rate
        self.ca.set_pv_value("LVL:HE:PULSE:READ:RATE:SP", 1)
        self.ca.assert_that_pv_is("LVL:HE:PULSE:READ:RATE", "Slow")
        self.ca.set_pv_value("LVL:HE:PULSE:READ:RATE:SP", 0)
        self.ca.assert_that_pv_is("LVL:HE:PULSE:READ:RATE", "Fast")

