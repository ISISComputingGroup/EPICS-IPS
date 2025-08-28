/* alarms.cpp
 *
 * This C++ code contains the implementation of the aSub record for handling system alarm status.
 * It is part of the OxInstIPS application and is used to process alarm messages from the
 * system, specifically for the temperature, levels and pressure control boards.
 * Board identifiers are provided as macros and passed to the aSub as input fields B-E.
 *
 * The aSub record processes alarm messages received from the system. The input is a string
 * containing the alarm message, which includes the board identifier and its status.
 * It extracts the board identifier and the alarm message, and writes them to the appropriate
 * output fields. The output fields (OUTA) reference mbbidirect records,
 * where the bit patterns will be established according to active alarms.
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
#include <vector>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <sstream>
#include <stdbool.h>
#include <registryFunction.h>
#include <aSubRecord.h>
#include <menuFtype.h>
#include <errlog.h>
#include <epicsTypes.h>
#include <epicsString.h>
#include <epicsExport.h>
#include "alarms.h"

using namespace std;

// The number of control boards we are monitoring
#define NBOARDS 4

static const vector<string> STATUS_TEXT_TEMPERATURE(
    {
    "Open circuit",
    "Short circuit",
    "Calibration error",
    "Firmware error",
    "Board not configured",
    }
);


static const vector<string> STATUS_TEXT_LEVEL(
    {
    "Open circuit",
    "Short circuit",
    "ADC error",
    "Over demand",
    "Over temperature",
    "Firmware error",
    "Board not configured",
    "No reserve",
    "Magnet Safety"
}
);

static const vector<string> STATUS_TEXT_PRESSURE(
    {
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
});

// Predetermine the number of status text entries for each board type
#define NUM_STATUS_TEXT_TEMPERATURE STATUS_TEXT_TEMPERATURE.size()
#define NUM_STATUS_TEXT_LEVEL STATUS_TEXT_LEVEL.size()
#define NUM_STATUS_TEXT_PRESSURE STATUS_TEXT_PRESSURE.size()

static const vector<vector<string>> STATUS_TEXT_ARRAY(
    {
    STATUS_TEXT_TEMPERATURE, // Magnet Temperature Controller Board}
    STATUS_TEXT_TEMPERATURE, // 10T Magnet Temperature Controller Board
    STATUS_TEXT_LEVEL,       // Levels Controller Board
    STATUS_TEXT_PRESSURE     // Pressure Controller Board
}
);

// Helper to reduce code complexity
static const vector<size_t> STATUS_TEXT_ARRAY_SIZE( {
    STATUS_TEXT_TEMPERATURE.size(), // Magnet Temperature Controller Board
    STATUS_TEXT_TEMPERATURE.size(), // 10T Magnet Temperature Controller Board
    STATUS_TEXT_LEVEL.size(),       // Levels Controller Board
    STATUS_TEXT_PRESSURE.size()     // Pressure Controller Board
});

// Helper function for case-insensitive string comparison
bool strcmp_nocase(const string& a, const string& b)
{
    return std::equal(a.begin(), a.end(),
                      b.begin(), b.end(),
                      [](char a, char b) {
                          return tolower(a) == tolower(b);
                      });
}

static long handle_system_alarm_status(aSubRecord *prec)
    {
    vector<string> token_list;
    vector<string> BOARD_ARRAY;
    // vala, valb, valc, vald accumulated bit patterns.
    // These ultimately will be written to mbbidirect records.
    vector<epicsInt32> out_bit_patterns(NBOARDS, 0);

    if (
        prec->fta != menuFtypeCHAR
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

    BOARD_ARRAY.push_back("MB1.T1"); // Magnet Temperature Controller Board
    BOARD_ARRAY.push_back("DB8.T1"); // 10T Magnet Temperature Controller Board
    BOARD_ARRAY.push_back("DB1.L1"); // Levels Controller Board
    BOARD_ARRAY.push_back("DB5.P1"); // Pressure Controller Board

    // *** The following is not used as we are using fixed board IDs above.                      ***
    // *** It would be better to pass these strings from the EPICS layer but the code below      ***
    // *** caused the subroutine to crash. Probably a pointer issue, but I have to draw the line ***
    // *** somewhere with the intention to do it properly at a later date.                       ***
    // Populate the BOARD_ARRAY with the board identifiers from the input fields.
    // Typically: "MB1.T1", "DB8.T1", "DB1.L1", "DB5.P1"
    //strcpy(BOARD_ARRAY[0], (char *)prec->b); // Magnet Temperature Controller Board
    //strcpy(BOARD_ARRAY[1], (char *)prec->c); // 10T Magnet Temperature Controller Board
    //strcpy(BOARD_ARRAY[2], (char *)prec->d); // Levels Controller Board
    //strcpy(BOARD_ARRAY[3], (char *)prec->e); // Pressure Controller Board

    string status = string((char *)((epicsOldString*)prec->a));

    // Tokenise the input string to extract the list of board+status.
    // Of the form:
    // "STAT:SYS:ALRM:DB8.T1<9>Open Circuit;MB1.T1<9>Short Circuit;DB1.L1<9>Over Demand;DB5.P1<9>Open Circuit;"
    // Or empty if no alarms are present.
    // We'll split the string by semicolons which will produce
    // a list of <board ID><tab>status messages.
    stringstream check(status);
    string token;
    while (getline(check, token, ';'))
        {
        if (!token.empty())
            {
            // Remove the trailing semicolon if present
            if (token.back() == ';')
                token.pop_back();
            // Add the token to the list
            token_list.push_back(token);
            }
        }

    // Debug output to show the tokens we have extracted
    // for(int i = 0; i < token_list.size(); i++)
    //    errlogPrintf("%s: token %d: %s\n", prec->name, i, token_list[i].c_str());

    // Now we have a list of tokens, each of which is of the form "<board ID><tab>status message".
    // We will process each token to extract the board ID and corresponding status message.
    for (const auto& token : token_list)
        {
        size_t tab_pos = token.find('\t');
        if (tab_pos == string::npos)
            {
            errlogPrintf("%s: Invalid token format: %s\n", prec->name, token.c_str());
            continue; // Skip invalid tokens
            }

        // Extract board ID and status message.
        // The board ID is everything before the tab character
        // and the status message is everything after the tab character.
        string board_id = token.substr(0, tab_pos);
        string status_message = token.substr(tab_pos + 1);

        // Find the board index based on the board ID
        int board_index = -1;
        for (int i = 0; i < NBOARDS; ++i)
            {
            if (board_id == BOARD_ARRAY[i])
                {
                board_index = i;
                break;
                }
            }

        if (board_index == -1)
            {
            errlogPrintf("%s: Unknown board ID: %s\n", prec->name, board_id.c_str());
            continue; // Skip unknown boards
            }

        // Now we have the board index and the status message.
        // We need to convert the status message to a numeric value, which will represent
        // the required bit position for the mbbidirect.
        int status_value = -1;
        const vector<string> status_text_array = STATUS_TEXT_ARRAY[board_index];
        int num_status_text = STATUS_TEXT_ARRAY_SIZE[board_index];

        for (int j = 0; j < num_status_text; ++j)
            {
            if (strcmp_nocase(status_message, status_text_array[j]))
                {
                status_value = j;
                break;
                }
            }

        if (status_value == -1)
            {
            errlogPrintf("%s: Unknown status message: %s\n", prec->name, status_message.c_str());
            continue; // Skip unknown status messages
            }

        // Set the bit corresponding to the status value
        out_bit_patterns[board_index] |= (1 << status_value);
        } // for each token

        for (int board_index = 0; board_index < NBOARDS; ++board_index)
            {
            // Write the status value to the appropriate output field
            switch (board_index)
                {
                case 0:
                    // Magnet Temperature Controller Board
                    *(epicsInt32*)prec->vala = out_bit_patterns[board_index];
                    break;
                case 1:
                    // 10T Magnet Temperature Controller Board
                    *(epicsInt32*)prec->valb = out_bit_patterns[board_index];
                    break;
                case 2:
                    // Levels Controller Board
                    *(epicsInt32*)prec->valc = out_bit_patterns[board_index];
                    break;
                case 3:
                    // Pressure Controller Board
                    *(epicsInt32*)prec->vald = out_bit_patterns[board_index];
                    break;
                default:
                    errlogPrintf("%s: Invalid board index: %d\n", prec->name, board_index);
                    break;
                }
            }
    return 0; // Process output links
    }

extern "C" {
epicsRegisterFunction(handle_system_alarm_status);
}

