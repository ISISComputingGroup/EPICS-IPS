/* alarms.c
 *
 * This C code contains the implementation of the aSub record for handling system alarm status.
 * It is part of the OxInstIPS application and is used to process alarm messages from the
 * system, specifically for the temperature, levels and pressure control boards.
 * Board identifiers are provided as macros and passed to the aSub as input fields B-E.
 *
 * The aSub record processes alarm messages received from the system. The input is a string
 * containing the alarm message, which includes the board identifier and its status.
 * It extracts the board identifier and the alarm message, and writes them to the appropriate
 * output fields. The output fields (OUTA) reference mbbidirect records, where the bit patterns will be
 * established according to active alarms.
 *
 * INPA - Input string containing the alarm message.
 * INPB - Board identifier form the magnet temperature controller (e.g. "MB1.T1")
 * INPC - Board identifier form the 10T magnet temperature controller (e.g. "DB8.T1")
 * INPD - Board identifier form the Levels controller (e.g. "DB1.L1")
 * INPE - Board identifier form the pressure controller (e.g. "DB5.P1")
 *
 * OUTA - Output field for the magnet temperature alarm status (mbbidirect).
 * OUTA - Output field for the magnet 10T temperature alarm status (mbbidirect).
 * OUTA - Output field for the levels alarm status (mbbidirect).
 * OUTA - Output field for the pressure alarm status (mbbidirect).
 *
 * Incoming alarm messages are expected to be in the format:
 * "STAT:SYS:ALRM:DB8.T1<9>Open Circuit;MB1.T1<9>Open Circuit;"
 * where <9> is the tab character.
 */

#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <registryFunction.h>
#include <aSubRecord.h>
#include <menuFtype.h>
#include <errlog.h>
#include <epicsTypes.h>
#include <epicsString.h>
#include <epicsExport.h>
#include "alarms.h"

// The number of control boards we are monitoring
#define NBOARDS 4

// The maximum number of tokens we expect in the status string
#define MAX_TOKENS 32

static const char *STATUS_TEXT_TEMPERATURE[] = {
    "Open circuit",
    "Short circuit",
    "Calibration error",
    "Firmware error",
    "Board not configured",
};

static const char *STATUS_TEXT_LEVEL[] = {
    "Open circuit",
    "Short circuit",
    "ADC error",
    "Over demand",
    "Over temperature",
    "Firmware error",
    "Board not configured",
    "No reserve"
};

static const char *STATUS_TEXT_PRESSURE[] = {
    "Open circuit",
    "Short circuit",
    "Calibration error",
    "Firmware error",
    "Board not configured",
    "Over current",
    "Current leakage",
    "Power on fail",
    "Checksum fail",
    "Clock fail",
    "ADC fail",
    "Mains fail",
    "Reference fail",
    "12V fail",
    "-12V fail",
    "8V fail",
    "-8V fail",
    "Amp gain error",
    "Amp offset error",
    "ADC offset error",
    "ADC PGA error",
    "ADC XTAL error",
    "Excitation + error",
    "Excitation - error"
};

// Predetermine the number of status text entries for each board type
#define NUM_STATUS_TEXT_TEMPERATURE (sizeof(STATUS_TEXT_TEMPERATURE) / sizeof(STATUS_TEXT_TEMPERATURE[0]))
#define NUM_STATUS_TEXT_LEVEL (sizeof(STATUS_TEXT_LEVEL) / sizeof(STATUS_TEXT_LEVEL[0]))
#define NUM_STATUS_TEXT_PRESSURE (sizeof(STATUS_TEXT_PRESSURE) / sizeof(STATUS_TEXT_PRESSURE[0]))

static const char **STATUS_TEXT_ARRAY[] = {
    STATUS_TEXT_TEMPERATURE, // Magnet Temperature Controller Board}
    STATUS_TEXT_TEMPERATURE, // 10T Magnet Temperature Controller Board
    STATUS_TEXT_LEVEL,       // Levels Controller Board
    STATUS_TEXT_PRESSURE     // Pressure Controller Board
};

// Helper to reduce code complexity
static const int STATUS_TEXT_ARRAY_SIZE[] = {
    NUM_STATUS_TEXT_TEMPERATURE, // Magnet Temperature Controller Board
    NUM_STATUS_TEXT_TEMPERATURE, // 10T Magnet Temperature Controller Board
    NUM_STATUS_TEXT_LEVEL,       // Levels Controller Board
    NUM_STATUS_TEXT_PRESSURE     // Pressure Controller Board
};

static long handle_system_alarm_status(aSubRecord *prec)
    {
    char* BOARD_ARRAY[NBOARDS];

    if (
        prec->fta != menuFtypeSTRING
     || prec->ftb != menuFtypeSTRING
     || prec->ftc != menuFtypeSTRING
     || prec->ftd != menuFtypeSTRING
     || prec->fte != menuFtypeSTRING
     || prec->ftva != menuFtypeLONG
     || prec->ftvb != menuFtypeLONG
     || prec->ftvc != menuFtypeLONG
     || prec->ftvd != menuFtypeLONG
     )
        {
         errlogPrintf("%s incorrect input type. Should be INPA,B,C,D,E (STRING), VALA,B,C,D (LONG)",
            prec->name);
         return -1;
        }

    errlogPrintf("%s: handle_system_alarm_status: about to copy names.\n", prec->name);

    BOARD_ARRAY[0] = "MB1.T1"; // Magnet Temperature Controller Board
    BOARD_ARRAY[1] = "DB8.T1"; // 10T Magnet Temperature Controller Board
    BOARD_ARRAY[2] = "DB1.L1"; // Levels Controller Board
    BOARD_ARRAY[3] = "DB5.P1"; // Pressure Controller Board

    // Populate the BOARD_ARRAY with the board identifiers from the input fields.
    // Typically: "MB1.T1", "DB8.T1", "DB1.L1", "DB5.P1"
    //strcpy(BOARD_ARRAY[0], (char *)prec->b); // Magnet Temperature Controller Board
    //strcpy(BOARD_ARRAY[1], (char *)prec->c); // 10T Magnet Temperature Controller Board
    //strcpy(BOARD_ARRAY[2], (char *)prec->d); // Levels Controller Board
    //strcpy(BOARD_ARRAY[3], (char *)prec->e); // Pressure Controller Board

    errlogPrintf("%s: handle_system_alarm_status: names copied - getting status from INPA.\n", prec->name);

    char* status = (char *)((epicsOldString*)prec->a);

    errlogPrintf("handle_system_alarm_status: result=%s\n", status);

    // Parse the input string, searching for the board name, followed by its status.
    for (int board_index = 0; board_index < NBOARDS; board_index++)
        {
        epicsInt32 bitpattern = 0L;
        char *board_name = BOARD_ARRAY[board_index];
        char *found_board = strstr(status, board_name);

        if (found_board != NULL)
            {
            // Found the board name, now extract the status.
            // The expected format is "MB1.T1\tstatus", where '\t' is a tab character.
            char *board_status = strchr(found_board, '\t');
            if (board_status == NULL)
                {
                errlogPrintf("%s: handle_system_alarm_status: No tab character found after board name.\n", prec->name);
                return -1;
                }

            // Move past the tab character to get the semicolon delimited status strings.
            board_status++;
            // Split the status string by semicolons to get individual status codes.
            char *token_list[MAX_TOKENS];
            int token_index = 0;
            char *token = strtok(board_status, ";");
            while (token != NULL)
                {
                // Process each token (status code)
                errlogPrintf("Status token: %s\n", token);
                char *new_token = (char*) malloc((strlen(token) + 1)*sizeof(char));
                strcpy(new_token, token);
                token_list[token_index] = new_token;
                token_index++;
                token = strtok(NULL, ";");
                }
            // Look up the status bit position code in the corresponding status text array
            // for each token.
            for (int iLookup_index=0; iLookup_index < token_index; iLookup_index++)
                {
                // Convert the token to an integer to find its position in the status text array.
                //int bit_pos = atoi(token_list[j]);
                bool bMsgFound = false;
                for (int iBoard_status_item = 0; iBoard_status_item < STATUS_TEXT_ARRAY_SIZE[board_index]; iBoard_status_item++)
                    {
                    if (strcmp(token_list[iLookup_index], STATUS_TEXT_ARRAY[board_index][iBoard_status_item]) == 0)
                        {
                        bMsgFound = true;
                        errlogPrintf("%s: handle_system_alarm_status: Found match to: %s .\n", prec->name, STATUS_TEXT_ARRAY[board_index][iBoard_status_item]);
                        // Found a matching status code, set the corresponding bit in the bitpattern.
                        errlogPrintf("%s: handle_system_alarm_status: Setting bit %d.\n", prec->name, iBoard_status_item);
                        bitpattern |= (1UL << iBoard_status_item);
                        }
                    }
                if (bMsgFound == false)
                    {
                    // The incoming message wasn't found in the array of expected messages.
                    errlogPrintf(
                        "handle_system_alarm_status: Invalid status code '%s' for board %s.\n",
                        token_list[iLookup_index], board_name);
                    }
                free(token_list[iLookup_index]); // Free the allocated memory for the token
                }

            // Write the status to the output field
            //memcpy(prec->vala, &bitpattern, sizeof(unsigned long));
            errlogPrintf("%s: handle_system_alarm_status: Setting VALA to bit pattern: %ud\n", prec->name, bitpattern);
            *(epicsInt32*)prec->vala = bitpattern; // Ensure the output is in the correct format
            }
        else
            {
            errlogPrintf("handle_system_alarm_status: Board %s not found in status string.\n", board_name);
            bitpattern = 0L;
            //memcpy(prec->vala, &bitpattern, sizeof(unsigned long));
            *(epicsInt32*)prec->vala = bitpattern; // Ensure the output is in the correct format
            }
        }
    return 0; // Process output links
    }

epicsRegisterFunction(handle_system_alarm_status);
