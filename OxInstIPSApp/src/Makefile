TOP=../..

include $(TOP)/configure/CONFIG

# -------------------------------
# Build an Diamond Support Module
# -------------------------------

PROD_IOC += OxInstIPS

# xxxRecord.h will be created from xxxRecord.dbd
#DBDINC += xxx.h

# The following are compiled and added to the support library
#xxx_SRCS += xxxCodeA.c
#xxx_SRCS += xxxCodeB.c

# We need to link against the EPICS Base libraries
#xxx_LIBS += $(EPICS_BASE_IOC_LIBS)

# OxInstIPS.dbd will be installed into <top>/dbd
DBD += OxInstIPS.dbd

# OxInstIPS.dbd will be created from these files
OxInstIPS_DBD += base.dbd
OxInstIPS_DBD += asyn.dbd
OxInstIPS_DBD += stream.dbd
OxInstIPS_DBD += calcSupport.dbd

# OxInstIPS_registerRecordDeviceDriver.cpp will be created
# OxInstIPS.dbd
OxInstIPS_SRCS += OxInstIPS_registerRecordDeviceDriver.cpp

# These two lines are needed for non-vxWorks builds, such as Linux
OxInstIPS_SRCS_DEFAULT += OxInstIPSMain.cpp
OxInstIPS_SRCS_vxWorks += -nil-

# Add locally compiled object code
#OxInstIPS_SRCS +=

# The following adds object code from base/src/vxWorks
OxInstIPS_OBJS_vxWorks += $(EPICS_BASE_BIN)/vxComLibrary

# This line says that this IOC Application depends on the
# xxx Support Module
OxInstIPS_LIBS += stream asyn calc sscan pcre

# We need to link this IOC Application against the EPICS Base libraries
OxInstIPS_LIBS += $(EPICS_BASE_IOC_LIBS)

# ---------------------------------------------------

# NOTE: To build SNL programs, SNCSEQ must be defined
# in the <top>/configure/RELEASE file
#
# The difference between a file with an "st" extension
# and one with an "stt" extension is:
# The "st" extension files get passed through the C preprocessor
# whereas the "stt" files do not.

#ifneq ($(SNCSEQ),)
    # This builds sncExample as a component of OxInstIPS
#    OxInstIPS_SNCFLAGS += +r
#    OxInstIPS_DBD      += sncExample.dbd
#    OxInstIPS_SRCS     += sncExample.stt
#    OxInstIPS_LIBS     += seq pv

    # The following builds sncExample as a standalone application
#    PROD_HOST           += sncExample
#    sncExample_SNCFLAGS += +m
#    sncExample_SRCS     += sncExample.stt
#    sncExample_LIBS     += seq pv
    # Here, we need to specify the dependency on EPICS Base libraries
    # again because this is a standalone application and
    # not part of OxInstIPS
#    sncExample_LIBS     += $(EPICS_BASE_HOST_LIBS)
#endif

include $(TOP)/configure/RULES
