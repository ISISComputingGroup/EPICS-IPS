#!/bin/sh
#
# Script test_OxInstIPS_asyn_gui.sh
#
# Runs the EDM asyn record screen for the asyn record for communicating
# with the Oxford Instruments IPS superconducting magnet power supply.
#

# NOTE: This needs reworking to parameterise the path.
cd /dls_sw/prod/R3.14.12.3/support/asyn/4-21/opi/edm

edm -x -m "P=TS-EA-SMC-01,R=:DBG:ASYN" asynOctet.edl
#edm -x -m "P=BL10J-EA-SMC-01,R=:DBG:ASYN" asynOctet.edl

exit

