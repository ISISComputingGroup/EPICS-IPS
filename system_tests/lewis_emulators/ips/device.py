from collections import OrderedDict
from typing import Callable

from lewis.core.logging import has_log
from lewis.devices import StateMachineDevice

from .modes import (
    Activity,
    Control,
    LevelMeterBoardStatus,
    LevelMeterHeliumReadRate,
    MagnetSupplyStatus,
    Mode,
    PressureBoardStatus,
    SweepMode,
    TemperatureBoardStatus,
)
from .states import HeaterOffState, HeaterOnState, MagnetQuenchedState, State

# Do not attempt to import DefaultState - it breaks the tests!

# As long as no magnetic saturation effects are present,
# there is a linear relationship between Teslas and Amps.
#
# This is called the load line. For more detailed (technical) discussion about the load line see:
# - http://aries.ucsd.edu/LIB/REPORT/SPPS/FINAL/chap4.pdf (section 4.3.3)
# - http://www.prizz.fi/sites/default/files/tiedostot/linkki1ID346.pdf (slide 11)
LOAD_LINE_GRADIENT = 0.01


def amps_to_tesla(amps: float) -> float:
    return amps * LOAD_LINE_GRADIENT


def tesla_to_amps(tesla: float) -> float:
    return tesla / LOAD_LINE_GRADIENT


def set_bit_value(value: int, bit_value: int) -> int:
    """Sets a bit at the position implied by the value."""
    return value | bit_value


def clear_bit_value(value: int, bit_value: int) -> int:
    """Clears a bit at the specified position implied by the value."""
    return value & ~bit_value


@has_log
class SimulatedIps(StateMachineDevice):
    # Currents that correspond to the switch heater being on and off
    HEATER_OFF_CURRENT, HEATER_ON_CURRENT = 0, 10

    # If there is a difference in current of more than this between the magnet
    # and the power supply, and the switch is resistive, then the magnet will quench.
    # No idea what this number should be for a physically realistic system so just guess.
    QUENCH_CURRENT_DELTA = 0.1

    # Maximum rate at which the magnet can safely ramp without quenching.
    MAGNET_RAMP_RATE = 1000

    # Fixed rate at which switch heater can ramp up or down
    HEATER_RAMP_RATE = 5

    def _initialize_data(self) -> None:
        """Initialize all of the device's attributes."""
        self.reset()

    def reset(self) -> None:
        # Within the cryostat, there is a wire that is made superconducting because it is
        # in the cryostat. The wire has a heater which can be used to make the wire go back
        # to a non-superconducting state.
        # When the heater is ON, the wire has a high resistance and the magnet is powered
        # directly by the power supply.
        #
        # When the heater is OFF, the wire is superconducting, which means that the power
        # supply can be ramped down and the magnet will stay active (this is "persistent" mode)
        self.heater_on: bool = False
        self.heater_current: float = 0.0

        # "Leads" are the non-superconducting wires between the superconducting magnet and
        # the power supply.
        # Not sure what a realistic value is for these leads, so I've guessed.
        self.lead_resistance: float = 50.0

        # Current = what the power supply is providing.
        self.current: float = 0.0
        self.current_setpoint: float = 0.0

        # Current for the magnet. May be different from the power supply current if the magnet
        # is in persistent mode.
        self.magnet_current: float = 0.0

        # Measured current may be different from what the PSU is attempting to provide
        self.measured_current: float = 0.0

        # If the device trips, store the last current which caused a trip in here.
        # This could be used for diagnostics e.g. finding maximum field which magnet is capable
        # of in a certain config.
        self.trip_current: float = 0.0

        # Ramp rate == sweep rate
        self.current_ramp_rate: float = 1 / LOAD_LINE_GRADIENT

        # Set to true if the magnet is quenched - this will cause lewis to enter the quenched state
        self.quenched: bool = False

        # Mode of the magnet e.g. HOLD, TO SET POINT, TO ZERO, CLAMP
        self.activity: Activity = Activity.TO_SETPOINT

        # No idea what a sensible value is.
        # Hard-code this here for now - can't be changed on real device.
        self.inductance: float = 0.005

        # No idea what sensible values are here.
        # Also not clear what the behaviour is of the controller when these limits are hit.
        self.neg_current_limit, self.pos_current_limit = -(10**6), 10**6

        # Local and locked is the zeroth mode of the control command
        self.control: Control = Control.LOCAL_LOCKED

        # The only sweep mode we are interested in is tesla fast
        # This appears to be unsupported by the SCPI protocol, so the
        # corresponding EPICS records have been removed in the SCPI database template
        self.sweep_mode: SweepMode = SweepMode.TESLA_FAST

        # Not sure what is the sensible value here
        self.mode: Mode = Mode.SLOW

        # SCPI mode specific
        self.bipolar: bool = True

        self.magnet_supply_status = MagnetSupplyStatus.OK

        self.voltage_limit: float = 10.0

        # Daughter boards status - returned by READ:SYS:ALRM
        self.tempboard_status: TemperatureBoardStatus = TemperatureBoardStatus.OPEN_CIRCUIT
        self.tempboard_10T_status: TemperatureBoardStatus = TemperatureBoardStatus.OK
        self.levelboard_status: LevelMeterBoardStatus = LevelMeterBoardStatus.OK
        self.pressureboard_status: PressureBoardStatus = PressureBoardStatus.OK

        self.helium_empty_resistance: float = 25.0
        self.helium_full_resistance: float = 0.12
        self.helium_fill_start_level: int = 10
        self.helium_fill_stop_level: int = 95
        self.helium_level: int = 50
        self.helium_read_rate: int = LevelMeterHeliumReadRate.FAST.value

        self.nitrogen_read_interval: int = 750  # milliseconds
        self.nitrogen_frequency_at_zero: float = 1.0
        self.nitrogen_frequency_at_full: float = 100.0
        self.nitrogen_fill_start_level: int = 10
        self.nitrogen_fill_stop_level: int = 95
        self.nitrogen_level: int = 50

        self.magnet_temperature: float = 4.2345  # Kelvin
        self.lambda_plate_temperature: float = 4.3456  # Kelvin
        self.pressure: float = 28.3898  # mBar

    def _get_state_handlers(self) -> dict[str, State]:
        return {
            "heater_off": HeaterOffState(),
            "heater_on": HeaterOnState(),
            "quenched": MagnetQuenchedState(),
        }

    def _get_initial_state(self) -> str:
        return "heater_off"

    def _get_transition_handlers(self) -> dict[tuple[str, str], Callable[[], bool]]:
        return OrderedDict(
            [
                (("heater_off", "heater_on"), lambda: self.heater_on),
                (("heater_on", "heater_off"), lambda: not self.heater_on),
                (("heater_on", "quenched"), lambda: self.quenched),
                (("heater_off", "quenched"), lambda: self.quenched),
                # Only triggered when device is reset or similar
                (("quenched", "heater_off"), lambda: not self.quenched and not self.heater_on),
                (("quenched", "heater_on"), lambda: not self.quenched and self.heater_on),
            ]
        )

    def quench(self, reason: str) -> None:
        self.log.info("Magnet quenching at current={} because: {}".format(self.current, reason))
        self.trip_current = self.current
        self.magnet_current = 0
        self.current = 0
        self.measured_current = 0
        self.quenched = True  # Causes LeWiS to enter Quenched state
        # For the SCPI protocol, we set the magnet supply status to indicate a quench
        self.magnet_supply_status = set_bit_value(
            self.magnet_supply_status, MagnetSupplyStatus.QUENCH_DETECTED
        )

    def unquench(self) -> None:
        self.quenched = False
        # For the SCPI protocol, we set the magnet supply status to clear a quench status
        self.magnet_supply_status = clear_bit_value(
            self.magnet_supply_status, MagnetSupplyStatus.QUENCH_DETECTED
        )

    def get_voltage(self) -> float:
        """Gets the voltage of the PSU.

        Everything except the leads is superconducting,
        we use Ohm's law here with the PSU current and the lead resistance.

        In reality would also need to account for inductance effects from the magnet
        but I don't think that extra complexity is necessary for this emulator.
        """
        return self.current * self.lead_resistance

    def set_heater_status(self, new_status: bool) -> None:
        if new_status and abs(self.current - self.magnet_current) > self.QUENCH_CURRENT_DELTA:
            raise ValueError(
                "Can't set the heater to on while the magnet current and PSU current are mismatched"
            )
        self.heater_on = new_status

    def set_tempboard_status(self, status_value: int) -> None:
        """Sets the temperature board status."""
        if status_value in list(iter(TemperatureBoardStatus)):
            status: TemperatureBoardStatus = TemperatureBoardStatus(status_value)
            self.tempboard_status = status
        else:
            raise ValueError(
                (
                    f"Invalid temperature board status value: {status_value}."
                    f" Must be one of {list(TemperatureBoardStatus)}"
                )
            )

    def set_tempboard_10t_status(self, status_value: int) -> None:
        """Sets the temperature board 10T status."""
        if status_value in list(iter(TemperatureBoardStatus)):
            status: TemperatureBoardStatus = TemperatureBoardStatus(status_value)
            self.tempboard_10T_status = status
        else:
            raise ValueError(
                (
                    f"Invalid temperature board 10T status value: {status_value}."
                    f" Must be one of {list(TemperatureBoardStatus)}"
                )
            )

    def set_levelboard_status(self, status_value: int) -> None:
        """Sets the temperature board status."""
        if status_value in list(iter(LevelMeterBoardStatus)):
            status: LevelMeterBoardStatus = LevelMeterBoardStatus(status_value)
            self.levelboard_status = status
        else:
            raise ValueError(
                (
                    f"Invalid level board status value: {status_value}."
                    f" Must be one of {list(LevelMeterBoardStatus)}"
                )
            )

    def set_pressureboard_status(self, status_value: int) -> None:
        """Sets the pressure board status."""
        if status_value in list(iter(PressureBoardStatus)):
            status: PressureBoardStatus = PressureBoardStatus(status_value)
            self.pressureboard_status = status
        else:
            raise ValueError(
                (
                    f"Invalid pressure board status value: {status_value}."
                    f" Must be one of {list(PressureBoardStatus)}"
                )
            )

    def get_nitrogen_refilling(self) -> bool:
        """Returns whether the nitrogen refilling is in progress."""
        return self.nitrogen_fill_start_level < self.nitrogen_level < self.nitrogen_fill_stop_level
