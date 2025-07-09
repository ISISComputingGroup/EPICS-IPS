from abc import abstractmethod
from enum import Enum, IntEnum


class Activity(Enum):
    HOLD = "Hold"
    TO_SETPOINT = "To Setpoint"
    TO_ZERO = "To Zero"
    CLAMP = "Clamped"


class Control(Enum):
    LOCAL_LOCKED = "Local & Locked"
    REMOTE_LOCKED = "Remote & Unlocked"
    LOCAL_UNLOCKED = "Local & Unlocked"
    REMOTE_UNLOCKED = "Remote & Unlocked"
    AUTO_RUNDOWN = "Auto-Run-Down"


class SweepMode(Enum):
    TESLA_FAST = "Tesla Fast"


class Mode(Enum):
    FAST = "Fast"
    SLOW = "Slow"


class MagnetSupplyStatus(IntEnum):
    """
    This class represents the status of the magnet supply
    and is only applicable to the IPS SCPI protocol.
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
    OK = 0x00000000
    SWITCH_HEATER_MISMATCH = 0x00000001
    OVER_TEMPERATURE_RUNDOWN_RESISTORS = 0x00000002
    OVER_TEMPERATURE_SENSE_RESISTOR = 0x00000004
    OVER_TEMPERATURE_PCB = 0x00000008
    CALIBRATION_FAILURE = 0x00000010
    MSP430_FIRMWARE_ERROR = 0x00000020
    RUNDOWN_RESISTORS_FAILED = 0x00000040
    MSP430_RS_485_FAILURE = 0x00000080
    QUENCH_DETECTED = 0x00000100
    CATCH_DETECTED = 0x00000200
    OVER_TEMPERATURE_SENSE_AMPLIFIER = 0x00001000
    OVER_TEMPERATURE_AMPLIFIER_1 = 0x00002000
    OVER_TEMPERATURE_AMPLIFIER_2 = 0x00004000
    PWM_CUTOFF = 0x00008000
    VOLTAGE_ADC_ERROR = 0x00010000
    CURRENT_ADC_ERROR = 0x00020000

class BoardStatus(IntEnum):
    """
    Provides the base functionality for board status enums and provides methods to lookup
    mbbi strings from given values and vice-versa.
    Strings can not be stored as member variables in a IntEnum, so an abstract method is defined
    to return a list of strings that represent the status values. This abstract method must be
    implemented in any subclass of BoardStatus.
    """
    @classmethod
    @abstractmethod
    def names(cls)->list[str]:
        return []

    def text(self)->str:
        try:
            ret = self.__class__.names()[self.value]
        except IndexError:
            ret = "Unknown"
        return ret


class TemperatureBoardStatus(BoardStatus):
    """
    This class represents the status of the temperature board
    and is only applicable to the IPS SCPI protocol.
    These alarms are returned in response to the READ:SYS:ALRM commnand returning errors as strings
    with the following example: STAT:SYS:ALRM:MB1.T1<tab>Open Circuit;
    
    | Status        | Description                                | Bit Value | Bit Position |
    |---------------|--------------------------------------------|-----------|--------------|
    | Open Circuit  | Heater off - Open circuit on sensor input  | 00000001  | 0            |
    | Short Circuit | Short circuit on sensor input              | 00000002  | 1            |

"""
    OK = 0
    OPEN_CIRCUIT = 1
    SHORT_CIRCUIT = 2
    CALIBRATION_ERROR = 3
    FIRMWARE_ERROR = 4
    BOARD_NOT_CONFIGURED = 5

    @classmethod
    def names(cls) -> list[str]:
        return ["", "Open Circuit", "Short Circuit", "Calibration Error",
                "Firmware Error", "Board Not Configured"]



class LevelMeterBoardStatus(BoardStatus):
    """
    This class represents the status of the level meter board
    and is only applicable to the IPS SCPI protocol.
    These alarms are returned in response to the READ:SYS:ALRM commnand returning errors as strings
    with the following example: STAT:SYS:ALRM:MB1.L1<tab>Open Circuit;

    | Status               | Description                               | Bit Value | Bit Position |
    |----------------------|-------------------------------------------|-----------|--------------|
    | Open Circuit         | Heater off - Open circuit on probe input  | 00000001  | 0            |
    | Short Circuit        | Short circuit on probe input              | 00000002  | 1            |
    | ADC Error            | On-board diagnostic: recalibrate          | 00000004  | 2            |
    | Over Demand          | On-board diagnostic: recalibrate          | 00000008  | 3            |
    | Over Temperature     |                                           | 00000010  | 4            |
    | Firmware Error       | Error in board firmware: restart iPS      | 00000020  | 5            |
    | Board Not Configured | Firmware not loaded correctly: update f/w | 00000040  | 6            |
    | No Reserve           | Autofill valve open but not filling       | 00000080  | 7            |

"""
    OK = 0
    OPEN_CIRCUIT = 1
    SHORT_CIRCUIT = 2
    ADC_ERROR = 3
    OVER_DEMAND = 4
    OVER_TEMPERATURE = 5
    FIRMWARE_ERROR = 6
    BOARD_NOT_CONFIGURED = 7
    NO_RESERVE = 8
    
    @classmethod
    def names(cls) -> list[str]:
        return ["", "Open Circuit", "Short Circuit", "ADC Error", "Over Demand",
                "Over Temperature", "Firmware Error", "Board Not Configured", "No Reserve"]

class LevelMeterHeliumReadRate(IntEnum):
    """
    This class represents the read rate of the helium level meter.
    It is only applicable to the IPS SCPI protocol.
    The read rate is used to determine how often the helium level is read, using the 
    DEV:<UID>:LVL:HEL:PULS:SLOW:[0|1] command.
    """
    SLOW = 0
    FAST = 1

    @classmethod
    def names(cls) -> list[str]:
        return ["Slow", "Fast"]
    