import typing
from lewis.adapters.stream import StreamInterface  # pyright: ignore [reportMissingImports]
from lewis.core.logging import has_log
from lewis.utils.command_builder import CmdBuilder

from ..device import amps_to_tesla, tesla_to_amps
from ..modes import (Activity,
                     Control,
                     LevelMeterHeliumReadRate,
                     TemperatureBoardStatus,
                     LevelMeterBoardStatus, PressureBoardStatus)

if typing.TYPE_CHECKING:
    from ..device import SimulatedIps


MODE_MAPPING = {
    'HOLD': Activity.HOLD,
    'RTOS': Activity.TO_SETPOINT,
    'RTOZ': Activity.TO_ZERO,
    'CLMP': Activity.CLAMP,
}

CONTROL_MODE_MAPPING = {
    0: Control.LOCAL_LOCKED,
    1: Control.REMOTE_LOCKED,
    2: Control.LOCAL_UNLOCKED,
    3: Control.REMOTE_UNLOCKED,
}


class DeviceUID:
    """
    Predefined UIDs for all devices attached to the iPS controller.
    """
    magnet_temperature_sensor = "MB1.T1"
    level_meter = "DB1.L1"
    magnet_supply = "GRPZ"
    temperature_sensor_10T = "DB8.T1"
    pressure_sensor_10t = "DB5.P1"


@has_log
class IpsStreamInterface(StreamInterface):
    protocol = "ips_scpi"
    in_terminator = "\n"
    out_terminator = "\n"

    # Commands that we expect via serial during normal operation
    commands = {
        CmdBuilder("get_version")
            .escape("*IDN?").eos().build(),
        CmdBuilder("get_magnet_supply_status")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:STAT").eos().build(),
        CmdBuilder("get_activity")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:ACTN").eos().build(),
        CmdBuilder("get_current")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:SIG:CURR").eos().build(),
        CmdBuilder("get_supply_voltage")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:SIG:VOLT").eos().build(),
        CmdBuilder("get_current_setpoint")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:SIG:CSET").eos().build(),
        CmdBuilder("get_current_sweep_rate")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:SIG:RCST").eos().build(),
        CmdBuilder("get_field")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:SIG:FLD").eos().build(),
        CmdBuilder("get_field_setpoint")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:SIG:FSET").eos().build(),
        CmdBuilder("get_field_sweep_rate")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:SIG:RFST").eos().build(),
        CmdBuilder("get_software_voltage_limit")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:VLIM").eos().build(),
        CmdBuilder("get_persistent_magnet_current")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:SIG:PCUR").eos().build(),
        CmdBuilder("get_persistent_magnet_field")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:SIG:PFLD").eos().build(),
        CmdBuilder("get_heater_current")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:SHTC").eos().build(),
        CmdBuilder("get_pos_current_limit")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:CLIM").eos().build(),
        CmdBuilder("get_lead_resistance")
            .escape(f"READ:DEV:{DeviceUID.magnet_temperature_sensor}:TEMP:SIG:RES").eos().build(),
        CmdBuilder("get_magnet_inductance")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:IND").eos().build(),
        CmdBuilder("get_heater_status")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:SIG:SWHT").eos().build(),
        CmdBuilder("get_bipolar_mode")
            .escape(f"READ:DEV:{DeviceUID.magnet_supply}:PSU:BIPL").eos().build(),
        CmdBuilder("get_system_alarms")
            .escape("READ:SYS:ALRM").eos().build(),
        CmdBuilder("set_activity")
            .escape(f"SET:DEV:{DeviceUID.magnet_supply}:PSU:ACTN:").string().eos().build(),
        CmdBuilder("set_current")
            .escape(f"SET:DEV:{DeviceUID.magnet_supply}:PSU:SIG:CSET:").float().eos().build(),
        CmdBuilder("set_field")
            .escape(f"SET:DEV:{DeviceUID.magnet_supply}:PSU:SIG:FSET:").float().eos().build(),
        CmdBuilder("set_field_sweep_rate")
            .escape(f"SET:DEV:{DeviceUID.magnet_supply}:PSU:SIG:RFST:").float().eos().build(),
        CmdBuilder("set_heater_on")
            .escape(f"SET:DEV:{DeviceUID.magnet_supply}:PSU:SIG:SWHT:ON").eos().build(),
        CmdBuilder("set_heater_off")
            .escape(f"SET:DEV:{DeviceUID.magnet_supply}:PSU:SIG:SWHT:OFF").eos().build(),
        CmdBuilder("set_bipolar_mode")
            .escape(f"SET:DEV:{DeviceUID.magnet_supply}:PSU:BIPL:").string().eos().build(),

        CmdBuilder("get_nit_read_interval")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:NIT:PPS").eos().build(),
        CmdBuilder("set_nit_read_interval")
            .escape(f"SET:DEV:{DeviceUID.level_meter}:LVL:NIT:PPS:").int().eos().build(),
        CmdBuilder("get_nit_freq_zero")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:NIT:FREQ:ZERO").eos().build(),
        CmdBuilder("set_nit_freq_zero")
            .escape(f"SET:DEV:{DeviceUID.level_meter}:LVL:NIT:FREQ:ZERO:").float().eos().build(),
        CmdBuilder("get_nit_freq_full")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:NIT:FREQ:FULL").eos().build(),
        CmdBuilder("set_nit_freq_full")
            .escape(f"SET:DEV:{DeviceUID.level_meter}:LVL:NIT:FREQ:FULL:").float().eos().build(),
        CmdBuilder("get_nit_fill_start_level")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:NIT:LOW").eos().build(),
        CmdBuilder("set_nit_fill_start_level")
            .escape(f"SET:DEV:{DeviceUID.level_meter}:LVL:NIT:LOW:").int().eos().build(),
        CmdBuilder("get_nit_fill_stop_level")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:NIT:HIGH").eos().build(),
        CmdBuilder("set_nit_fill_stop_level")
            .escape(f"SET:DEV:{DeviceUID.level_meter}:LVL:NIT:HIGH:").int().eos().build(),
        CmdBuilder("get_nit_refilling")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:NIT:RFL").eos().build(),
        CmdBuilder("get_nitrogen_level")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:SIG:NIT:LEV").eos().build(),

        CmdBuilder("get_helium_level")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:SIG:HEL:LEV").eos().build(),
        CmdBuilder("get_he_empty_resistance")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:HEL:RES:ZERO").eos().build(),
        CmdBuilder("get_he_full_resistance")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:HEL:RES:FULL").eos().build(),
        CmdBuilder("set_he_empty_resistance")
            .escape(f"SET:DEV:{DeviceUID.level_meter}:LVL:HEL:RES:ZERO:").float().eos().build(),
        CmdBuilder("set_he_full_resistance")
            .escape(f"SET:DEV:{DeviceUID.level_meter}:LVL:HEL:RES:FULL:").float().eos().build(),
        CmdBuilder("get_he_fill_start_level")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:HEL:LOW").eos().build(),
        CmdBuilder("set_he_fill_start_level")
            .escape(f"SET:DEV:{DeviceUID.level_meter}:LVL:HEL:LOW:").int().eos().build(),
        CmdBuilder("get_he_fill_stop_level")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:HEL:HIGH").eos().build(),
        CmdBuilder("set_he_fill_stop_level")
            .escape(f"SET:DEV:{DeviceUID.level_meter}:LVL:HEL:HIGH:").int().eos().build(),
        CmdBuilder("get_he_refilling")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:HEL:RFL").eos().build(),
        CmdBuilder("get_he_read_rate")
            .escape(f"READ:DEV:{DeviceUID.level_meter}:LVL:HEL:PULS:SLOW").eos().build(),
        CmdBuilder("set_he_read_rate")
            .escape(f"SET:DEV:{DeviceUID.level_meter}:LVL:HEL:PULS:SLOW:").enum("OFF", "ON").eos().build(),
        CmdBuilder("get_magnet_temperature")
            .escape(f"READ:DEV:{DeviceUID.magnet_temperature_sensor}:TEMP:SIG:TEMP").eos().build(),
        CmdBuilder("get_lambda_plate_temperature")
            .escape(f"READ:DEV:{DeviceUID.temperature_sensor_10T}:TEMP:SIG:TEMP").eos().build(),
        CmdBuilder("get_pressure")
            .escape(f"READ:DEV:{DeviceUID.pressure_sensor_10t}:PRES:SIG:PRES").eos().build(),

    }

    def __init__(self) -> None:
        super(StreamInterface, self).__init__()
        self.device: "SimulatedIps"


    def handle_error(self, request: str, error: str) -> None:
        err_string = "command was: {}, error was: {}: {}\n".format(
            request, error.__class__.__name__, error
        )
        print(err_string)
        self.log.error(err_string) # pyright: ignore

    @staticmethod
    def get_version() -> str:
        """ get_version()
        The format of the reply is:
            IDN:OXFORD INSTRUMENTS:MERCURY dd:ss:ff
            Where:
                dd is the basic instrument type (iPS , iPS, Cryojet etc.)
                ss is the serial number of the main board
                ff is the firmware version of the instrument
        :return: Simulated identity string
        """
        return "IDN:OXFORD INSTRUMENTS:MERCURY IPS:simulated:0.0.0"

    def get_activity(self) -> str:
        testmode: str = ""
        for tm in MODE_MAPPING:
            if self.device.activity == MODE_MAPPING[tm]:
                testmode = tm
                break
        return f"STAT:DEV:{DeviceUID.magnet_supply}:PSU:ACTN:{testmode}"

    def set_activity(self, mode: str) -> str:
        # Set the default return value to invalid (guilty until proven innocent)
        ret = f"STAT:SET:DEV:{DeviceUID.magnet_supply}:PSU:ACTN:{mode}:INVALID"
        
        for testmode in MODE_MAPPING:
            if mode == MODE_MAPPING[testmode].value:
                break
                
        try:
            self.device.activity = MODE_MAPPING[mode]
            ret = f"STAT:SET:DEV:{DeviceUID.magnet_supply}:PSU:ACTN:{mode}:VALID"
        except KeyError:
            ret = f"STAT:SET:DEV:{DeviceUID.magnet_supply}:PSU:ACTN:{mode}:INVALID"
            raise ValueError("Invalid mode specified")
        return ret

    def get_magnet_supply_status(self) -> str:
        """
        The format of the reply is:
            STAT:DEV:{DeviceUID.magnet_supply}:PSU:STAT:00000000

            Where :
                | Status                               | Bit Value | Bit Position |
                |--------------------------------------|-----------|--------------|
                | Switch Heater Mismatch               | 00000001  | 0            |
                | Over Temperature [Rundown Resistors] | 00000002  | 1            |
                | Over Temperature [Sense Resistor]    | 00000004  | 2            |
                | Over Temperature [PCB]               | 00000008  | 3            |
                | Calibration Failure                  | 00000010  | 4            |
                | MSP430 Firmware Error                | 00000020  | 5            |
                | Rundown Resistors Failed             | 00000040  | 6            |
                | MSP430 RS-485 Failure                | 00000080  | 7            |
                | Quench detected                      | 00000100  | 8            |
                | Catch detected                       | 00000200  | 9            |
                | Over Temperature [Sense Amplifier]   | 00001000  | 12           |
                | Over Temperature [Amplifier 1]       | 00002000  | 13           |
                | Over Temperature [Amplifier 2]       | 00004000  | 14           |
                | PWM Cutoff                           | 00008000  | 15           |
                | Voltage ADC error                    | 00010000  | 16           |
                | Current ADC error                    | 00020000  | 17           |

            This information is not published and was derived from
            direct questions to Oxford Instruments.
        """
        resp = (f"STAT:DEV:{DeviceUID.magnet_supply}"
                f":PSU:STAT:{self.device.magnet_supply_status:08x}")
        return resp

    def get_current_setpoint(self) -> str:
        return (f"STAT:DEV:{DeviceUID.magnet_supply}"
                f":PSU:SIG:CSET:{self.device.current_setpoint:.4f}A")

    def get_supply_voltage(self) -> str:
        return f"STAT:DEV:{DeviceUID.magnet_supply}:PSU:SIG:VOLT:{self.device.get_voltage():.4f}V"

    def get_current(self) -> str:
        """Gets the demand current of the PSU."""
        return (f"STAT:DEV:{DeviceUID.magnet_supply}"
                f":PSU:SIG:CURR:{self.device.measured_current:.4f}A")

    def get_current_sweep_rate(self) -> str:
        # Returns the current ramp rate in amps per second.
        # of the form: STAT:DEV:GRPZ:PSU:SIG:RCST:5.3612A/m
        return (f"STAT:DEV:{DeviceUID.magnet_supply}"
                f":PSU:SIG:RCST:{self.device.current_ramp_rate:.4f}A/m")

    def get_field(self) -> str:
        return (f"STAT:DEV:{DeviceUID.magnet_supply}"
                f":PSU:SIG:FLD:{amps_to_tesla(self.device.current):.4f}T")

    def get_field_setpoint(self) -> str:
        return (f"STAT:DEV:{DeviceUID.magnet_supply}"
                f":PSU:SIG:FSET:{amps_to_tesla(self.device.current_setpoint):.4f}T")

    def get_field_sweep_rate(self) -> str:
        field = amps_to_tesla(self.device.current_ramp_rate)
        return f"STAT:DEV:{DeviceUID.magnet_supply}:PSU:SIG:RFST:{field:.4f}T/m"

    def get_software_voltage_limit(self) -> str:
        # According to the manual, this should return with a unit ":V" suffix
        # but in reality it does not.
        return f"STAT:DEV:{DeviceUID.magnet_supply}:PSU:VLIM:{self.device.voltage_limit}"

    def get_persistent_magnet_current(self) -> str:
        return f"STAT:DEV:{DeviceUID.magnet_supply}:PSU:SIG:PCUR:{self.device.magnet_current:.4f}A"

    # TBD
    def get_trip_current(self) -> str:
        return f"R{self.device.trip_current}"

    def get_persistent_magnet_field(self) -> str:
        return (f"STAT:DEV:{DeviceUID.magnet_supply}"
                f":PSU:SIG:PFLD:{amps_to_tesla(self.device.magnet_current):.4f}T")

    def get_heater_current(self) -> str:
        return f"STAT:DEV:{DeviceUID.magnet_supply}:PSU:SHTC:{self.device.heater_current:.4f}mA"

    def get_neg_current_limit(self) -> str:
        ret = f"STAT:DEV:{DeviceUID.magnet_supply}:PSU:CLIM:{self.device.neg_current_limit:.4f}"
        return ret

    def get_pos_current_limit(self) -> str:
        ret = f"STAT:DEV:{DeviceUID.magnet_supply}:PSU:CLIM:{self.device.pos_current_limit:.4f}"
        return ret

    def get_lead_resistance(self) -> str:
        ret = (f"STAT:DEV:{DeviceUID.magnet_temperature_sensor}"
               f":TEMP:SIG:RES:{self.device.lead_resistance:.4f}R")
        return ret

    def get_magnet_inductance(self) -> str:
        ret = f"STAT:DEV:{DeviceUID.magnet_supply}:PSU:IND:{self.device.inductance:.4f}"
        return ret

    def get_heater_status(self) -> str:
        return (f"STAT:DEV:{DeviceUID.magnet_supply}"
                f":PSU:SIG:SWHT:{'ON' if self.device.heater_on else 'OFF'}")

    def get_bipolar_mode(self) -> str:
        return (f"STAT:DEV:{DeviceUID.magnet_supply}"
                f":PSU:BIPL:{'ON' if self.device.bipolar else 'OFF'}")

    def get_system_alarms(self) -> str:
        """
        Returns the system alarms in the format:
        STAT:SYS:ALRM:MB1.T1<tab>Open Circuit;DB1.L1<tab>Short Circuit;
        """
        alarms = ["STAT:SYS:ALRM:",]
        if self.device.tempboard_status != TemperatureBoardStatus.OK:
            alarms.append((f"{DeviceUID.magnet_temperature_sensor}\t"
                           f"{TemperatureBoardStatus.names()[self.device.tempboard_status.value]};"))
        if self.device.tempboard_10T_status != TemperatureBoardStatus.OK:
            alarms.append((f"{DeviceUID.temperature_sensor_10T}\t"
                           f"{TemperatureBoardStatus.names()[self.device.tempboard_10T_status.value]};"))
        if self.device.levelboard_status.value != LevelMeterBoardStatus.OK:
            alarms.append((f"{DeviceUID.level_meter}\t"
                           f"{LevelMeterBoardStatus.names()[self.device.levelboard_status.value]};"))
        if self.device.pressureboard_status.value != PressureBoardStatus.OK:
            alarms.append((f"{DeviceUID.pressure_sensor_10t}\t"
                           f"{PressureBoardStatus.names()[self.device.pressureboard_status.value]};"))
        alarm_list_str = "".join(alarms)
        return alarm_list_str

    def set_current(self, current: float) -> str:
        self.device.current_setpoint = current
        return f"STAT:SET:DEV:{DeviceUID.magnet_supply}:PSU:SIG:CSET:{current:1.4f}:VALID"

    def set_field(self, field: float) -> str:
        ret = f"STAT:SET:DEV:{DeviceUID.magnet_supply}:PSU:SIG:FSET:{field:.4f}:VALID"
        self.device.current_setpoint = tesla_to_amps(field)
        return ret

    def set_heater_on(self) -> str:
        self.device.set_heater_status(True)
        ret = f"STAT:SET:DEV:{DeviceUID.magnet_supply}:PSU:SIG:SWHT:ON:VALID"
        return ret

    def set_heater_off(self) -> str:
        self.device.set_heater_status(False)
        ret = f"STAT:SET:DEV:{DeviceUID.magnet_supply}:PSU:SIG:SWHT:OFF:VALID"
        return ret

    def set_field_sweep_rate(self, tesla_per_min: float) -> str:
        self.device.current_ramp_rate = tesla_to_amps(tesla_per_min)
        ret = f"STAT:SET:DEV:{DeviceUID.magnet_supply}:PSU:SIG:RFST:{tesla_per_min:1.4f}:VALID"
        return ret

    def set_bipolar_mode(self, mode: bool) -> str:
        self.device.bipolar = bool(mode)
        return (f"STAT:DEV:{DeviceUID.magnet_supply}"
                f":PSU:BIPL:{'ON' if self.device.bipolar else 'OFF'}")

    def get_nit_read_interval(self) -> str:
        """
        Gets the nitrogen read interval in milliseconds.
        :return: A string indicating the nitrogen read interval.
        """
        return (f"STAT:DEV:{DeviceUID.level_meter}"
                f":LVL:NIT:PPS:{self.device.nitrogen_read_interval:d}")
    
    def set_nit_read_interval(self, interval: int) -> str:
        """
        Sets the nitrogen read interval in milliseconds.
        :param interval: The nitrogen read interval to set.
        :return: A string indicating the success of the operation.
        """
        self.device.nitrogen_read_interval = interval
        return f"STAT:SET:DEV:{DeviceUID.level_meter}:LVL:NIT:PPS:{interval:d}:VALID"   
    
    def get_nit_freq_zero(self) -> str:
        ret = (f"STAT:DEV:{DeviceUID.level_meter}"
               f":LVL:NIT:FREQ:ZERO:{self.device.nitrogen_frequency_at_zero:.2f}")
        return ret

    def set_nit_freq_zero(self, freq: float) -> str:
        self.device.nitrogen_frequency_at_zero = freq
        ret = (f"STAT:SET:DEV:{DeviceUID.level_meter}"
               f":LVL:NIT:FREQ:ZERO:{self.device.nitrogen_frequency_at_zero:.2f}:VALID")
        return ret

    def get_nit_freq_full(self) -> str:
        ret = (f"STAT:DEV:{DeviceUID.level_meter}"
               f":LVL:NIT:FREQ:FULL:{self.device.nitrogen_frequency_at_full:.2f}")
        return ret

    def set_nit_freq_full(self, freq: float) -> str:
        self.device.nitrogen_frequency_at_full = freq
        ret = (f"STAT:SET:DEV:{DeviceUID.level_meter}"
               f":LVL:NIT:FREQ:FULL:{self.device.nitrogen_frequency_at_full:.2f}:VALID")
        return ret

    def get_he_empty_resistance(self) -> str:
        ret = (f"STAT:DEV:{DeviceUID.level_meter}"
               f":LVL:HEL:RES:ZERO:{self.device.helium_empty_resistance:.2f}")
        return ret

    def get_he_full_resistance(self) -> str:
        ret = (f"STAT:DEV:{DeviceUID.level_meter}"
               f":LVL:HEL:RES:FULL:{self.device.helium_full_resistance:.2f}")
        return ret

    def set_he_empty_resistance(self, resistance: float) -> str:
        self.device.helium_empty_resistance = resistance
        ret = (f"STAT:SET:DEV:{DeviceUID.level_meter}"
               f":LVL:HEL:RES:ZERO:{self.device.helium_empty_resistance:.2f}:VALID")
        return ret

    def set_he_full_resistance(self, resistance: float) -> str:
        self.device.helium_full_resistance = resistance
        ret = (f"STAT:SET:DEV:{DeviceUID.level_meter}"
               f":LVL:HEL:RES:FULL:{self.device.helium_full_resistance:.2f}:VALID")
        return ret

    def get_he_fill_start_level(self) -> str:
        """
        Gets the helium fill start level.
        :return: A string indicating the helium fill start level.
        """
        return (f"STAT:DEV:{DeviceUID.level_meter}"
                f":LVL:HEL:LOW:{self.device.helium_fill_start_level:d}")

    def set_he_fill_start_level(self, level: int) -> str:
        """
        Sets the helium fill start level.
        :param level: The helium fill start level to set.
        :return: A string indicating the success of the operation.
        """
        self.device.helium_fill_start_level = level
        return f"STAT:SET:DEV:{DeviceUID.level_meter}:LVL:HEL:LOW:{level:d}:VALID"

    def get_he_fill_stop_level(self) -> str:
        """
        Gets the helium fill stop level.
        :return: A string indicating the helium fill stop level.
        """
        return (f"STAT:DEV:{DeviceUID.level_meter}"
                f":LVL:HEL:HIGH:{self.device.helium_fill_stop_level:d}")

    def set_he_fill_stop_level(self, level: int) -> str:
        """
        Sets the helium fill stop level.
        :param level: The helium fill stop level to set.
        :return: A string indicating the success of the operation.
        """
        self.device.helium_fill_stop_level = level
        return f"STAT:SET:DEV:{DeviceUID.level_meter}:LVL:HEL:HIGH:{level:d}:VALID"

    def get_he_refilling(self) -> str:
        """
        Gets the helium refilling status.
        :return: A string indicating whether helium is refilling.
        """
        refilling: bool = self.device.helium_level <= self.device.helium_fill_start_level
        
        return (f"STAT:DEV:{DeviceUID.level_meter}"
                f":LVL:HEL:RFL:{'ON' if refilling else 'OFF'}")

    def get_nit_fill_start_level(self) -> str:
        """
        Gets the nitrogen fill start level.
        :return: A string indicating the nitrogen fill start level.
        """
        return (f"STAT:DEV:{DeviceUID.level_meter}"
                f":LVL:NIT:LOW:{self.device.nitrogen_fill_start_level:d}")

    def set_nit_fill_start_level(self, level: int) -> str:
        """
        Sets the nitrogen fill start level.
        :param level: The nitrogen fill start level to set.
        :return: A string indicating the success of the operation.
        """
        self.device.nitrogen_fill_start_level = level
        return f"STAT:SET:DEV:{DeviceUID.level_meter}:LVL:NIT:LOW:{level:d}:VALID"
    
    def get_nit_fill_stop_level(self) -> str:
        """
        Gets the nitrogen fill stop level.
        :return: A string indicating the nitrogen fill stop level.
        """
        return (
                f"STAT:DEV:{DeviceUID.level_meter}:LVL:NIT:HIGH:"
                f"{self.device.nitrogen_fill_stop_level:d}"
        )

    def set_nit_fill_stop_level(self, level: int) -> str:
        """
        Sets the nitrogen fill stop level.
        :param level: The nitrogen fill stop level to set.
        :return: A string indicating the success of the operation.
        """
        self.device.nitrogen_fill_stop_level = level
        return f"STAT:SET:DEV:{DeviceUID.level_meter}:LVL:NIT:HIGH:{level:d}:VALID"

    def get_nit_refilling(self) -> str:
        """
        Gets the nitrogen refilling status.
        :return: A string indicating whether nitrogen is refilling.
        """
        state: str = 'ON' if (self.device.nitrogen_level 
                              <= self.device.nitrogen_fill_start_level) else 'OFF'
        
        return (
                f"STAT:DEV:{DeviceUID.level_meter}:LVL:NIT:RFL:{state}")

    def get_nitrogen_level(self) -> str:
        """
        Gets the current nitrogen level.
        :return: A string indicating the nitrogen level.
        """
        return f"STAT:DEV:{DeviceUID.level_meter}:LVL:SIG:NIT:LEV:{self.device.nitrogen_level:d}"

    def get_helium_level(self) -> str:
        """
        Gets the current helium level.
        :return: A string indicating the helium level.
        """
        return f"STAT:DEV:{DeviceUID.level_meter}:LVL:SIG:HEL:LEV:{self.device.helium_level:d}"

    def get_he_read_rate(self) -> str:
        """
        Gets the helium read rate.
        :return: A string indicating the helium read rate.
        """
        state: str = 'ON' if (self.device.helium_read_rate == LevelMeterHeliumReadRate.SLOW.value)\
                    else 'OFF'

        return f"STAT:DEV:{DeviceUID.level_meter}:LVL:HEL:PULS:SLOW:{state}"

    def set_he_read_rate(self, slow_rate: str) -> str:
        """
        Sets the helium read slow_rate (from bo)
        :param slow_rate: The helium read slow rate to set: OFF -> FAST, ON -> SLOW
        :return: A string indicating the success of the operation.
        """
        self.device.helium_read_rate = LevelMeterHeliumReadRate.FAST.value if (slow_rate == "OFF") \
            else LevelMeterHeliumReadRate.SLOW.value

        return f"STAT:SET:DEV:{DeviceUID.level_meter}:LVL:HEL:PULS:SLOW:{slow_rate}:VALID"

    def get_magnet_temperature(self) -> str:
        """
        Gets the temperature of the magnet.
        :return: The temperature in Kelvin.
        """
        return (f"STAT:DEV:{DeviceUID.magnet_temperature_sensor}:TEMP:SIG:TEMP:"
               f"{self.device.magnet_temperature:.4f}K")

    def get_lambda_plate_temperature(self) -> str:
        """
        Gets the temperature of the lambda plate.
        :return: The temperature in Kelvin.
        """
        return (f"STAT:DEV:{DeviceUID.temperature_sensor_10T}:TEMP:SIG:TEMP:"
                f"{self.device.lambda_plate_temperature:.4f}K")


    def get_pressure(self) -> str:
        """
        Gets the pressure in mBar.
        :return: The pressure in mBar.
        """
        #return self.device.pressure
        return (f"STAT:DEV:{DeviceUID.pressure_sensor_10t}:PRES:SIG:PRES:"
                f"{self.device.pressure:.4f}mB")
