import unittest

from parameterized import parameterized  # pyright: ignore
from utils.channel_access import ChannelAccess  # pyright: ignore
from utils.ioc_launcher import get_default_ioc_dir  # pyright: ignore
from utils.test_modes import TestModes  # pyright: ignore
from utils.testing import get_running_lewis_and_ioc, parameterized_list  # pyright: ignore

from .common_tests.ips_common import IpsBaseTests

# Tell ruff to ignore the N802 warning (function name should be lowercase).
# Names contain GIVEN, WHEN, THEN
# Ignore line length as well, as this is a common pattern in tests.
# ruff: noqa: N802, E501

DEVICE_PREFIX = "IPS_01"
EMULATOR_NAME = "ips"


IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("IPS"),
        "emulator": EMULATOR_NAME,
        "lewis_protocol": "ips_legacy",
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

TEST_VALUES = [-0.12345, 6.54321]  # Should be able to handle negative polarities
TEST_SWEEP_RATES = [0.001, 0.9876]  # Rate can't be negative or >1

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

    def _get_device_prefix(self) -> str:
        return DEVICE_PREFIX

    def _get_ioc_config(self) -> list:
        return IOCS

    def setUp(self) -> None:
        ioc_config = self._get_ioc_config()

        # Time to wait for the heater to warm up/cool down (extracted from IOC macros above)
        heater_wait_time = float((ioc_config[0].get("macros").get("HEATER_WAITTIME")))

        self._lewis, self._ioc = get_running_lewis_and_ioc(EMULATOR_NAME, DEVICE_PREFIX)
        # Some changes happen on the order of heater_wait_time seconds.
        # Use a significantly longer timeout to capture a few heater wait times
        # plus some time for PVs to update.
        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX, default_timeout=heater_wait_time * 10)

        # Wait for some critical pvs to be connected.
        for pv in ["MAGNET:FIELD:PERSISTENT", "FIELD", "FIELD:SP:RBV", "HEATER:STATUS"]:
            self.ca.assert_that_pv_exists(pv)

        # Ensure in the correct mode
        self.ca.set_pv_value("CONTROL:SP", "Remote & Unlocked")
        self.ca.set_pv_value("ACTIVITY:SP", "To Setpoint")

        # Don't run reset as the sudden change of state confuses the IOC's state machine.
        # No matter what the initial state of the device the SNL should be able to deal with it.
        # self._lewis.backdoor_run_function_on_device("reset")

        self.ca.set_pv_value("FIELD:RATE:SP", 10)
        # self.ca.assert_that_pv_is_number("FIELD:RATE:SP", 10)

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
            self.ca.assert_that_pv_is_one_of("HEATER:STATUS", HEATER_OFF_STATES)

    @parameterized.expand(field for field in parameterized_list(TEST_VALUES))
    def test_GIVEN_magnet_quenches_while_at_field_THEN_ioc_displays_this_quench_in_statuses(
        self, _: str, field: float
    ) -> None:
        self._set_and_check_persistent_mode(False)
        self.ca.set_pv_value("FIELD:SP", field)
        self._assert_field_is(field)
        self.ca.assert_that_pv_is("STATEMACHINE", "At field")

        with self._backdoor_magnet_quench():
            self.ca.assert_that_pv_is("STS:SYSTEM:FAULT", "Quenched")
            self.ca.assert_that_pv_alarm_is("STS:SYSTEM:FAULT", self.ca.Alarms.MAJOR)
            self.ca.assert_that_pv_is("CONTROL", "Auto-Run-Down")
            self.ca.assert_that_pv_alarm_is("CONTROL", self.ca.Alarms.MAJOR)

            # The trip field should be the field at the point when the magnet quenched.
            self.ca.assert_that_pv_is_number("FIELD:TRIP", field, tolerance=TOLERANCE)

            # Field should be set to zero by emulator
            # (mirroring what the field ought to do in the real device)
            self.ca.assert_that_pv_is_number("FIELD", 0, tolerance=TOLERANCE)
            self.ca.assert_that_pv_is_number("FIELD:USER", 0, tolerance=TOLERANCE)
            self.ca.assert_that_pv_is_number("MAGNET:FIELD:PERSISTENT", 0, tolerance=TOLERANCE)

    # These tests for locking and unlocking the remote control are only applicable
    # to the legacy protocol. SCPI does not have a remote control lock.
    @parameterized.expand(
        control_command for control_command in parameterized_list(CONTROL_COMMANDS_WITH_VALUES)
    )
    def test_WHEN_control_command_value_set_THEN_remote_unlocked_set(
        self, _: str, control_pv: str, set_value: str
    ) -> None:
        self.ca.set_pv_value("CONTROL", "Local & Locked")
        self.ca.set_pv_value(control_pv, set_value)
        self.ca.assert_that_pv_is("CONTROL", "Remote & Unlocked")

    @parameterized.expand(
        control_pv for control_pv in parameterized_list(CONTROL_COMMANDS_WITHOUT_VALUES)
    )
    def test_WHEN_control_command_processed_THEN_remote_unlocked_set(
        self, _: str, control_pv: str
    ) -> None:
        self.ca.set_pv_value("CONTROL", "Local & Locked")
        self.ca.process_pv(control_pv)
        self.ca.assert_that_pv_is("CONTROL", "Remote & Unlocked")
