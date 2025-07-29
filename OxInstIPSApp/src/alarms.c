#include <stdlib.h>
#include <string.h>
#include <registryFunction.h>
#include <aSubRecord.h>
#include <menuFtype.h>
#include <errlog.h>
#include <epicsTypes.h>
#include <epicsString.h>
#include <epicsExport.h>
#include "alarms.h"

static const char* BOARD_ARRAY[] = {
    "MB1.T1",  // 0
    "DB1.L1",  // 1
    "DB8.T1",   // 2
    "DB5.P1",  // 3
};

#define BOARD_ARRAY (sizeof(BOARD_ARRAY) / sizeof(const char*))

static long handle_system_alarm_status(aSubRecord *prec)
    {
    epicsInt32 i;
    epicsOldString* status = (epicsOldString*)prec->vala;
    i = *(epicsInt32*)prec->a;
    if (prec->fta != menuFtypeSTRING || prec->ftva != menuFtypeLONG)
        {
         errlogPrintf("%s incorrect input type. Should be A (STRING), VALA (LONG)", prec->name);
         return -1;
        }

    errlogPrintf("handle_system_alarm_status: result=%s\n", status);

    // Parse the input string, searching for the board name, followed by its status.
    const char * board_name = "MB1.T1";
    char *found_board = strstr(status, board_name);

    if (found_board != NULL)
        {
        // Found the board name, now extract the status.
        // The expected format is "MB1.T1\tstatus", where '\t' is a tab character.
        board_status = strchr(found_board, '\t');
        if (board_status == NULL)
            {
            errlogPrintf("handle_system_alarm_status: No tab character found after board name.\n");
            return -1;
            }

        // Move past the tab character to get the status.
        found_board++;
        }
    else
        {
        errlogPrintf("handle_system_alarm_status: Board %s not found in status string.\n", board_name);
        return -1;
        }
    char *board_status = found_board+1; // jump over the tab character (9)

    }

epicsRegisterFunction(handle_system_alarm_status);
