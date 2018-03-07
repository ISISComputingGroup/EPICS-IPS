#!/bin/sh
#
# Script test_OxInstIPSMain_GUI.sh
#
# Runs the EDM Main screen for the Oxford Instruments IPS 
# superconducting magnet power supply.
#
export EDMDATAFILES=.:../../../data:
export PATH=.:../../../bin/linux-x86_64:${PATH}

edm -x -m "P=TS-EA-SMC-01" OxInstIPSMain.edl
#edm -x -m "P=BL10J-EA-SMC-01" OxInstIPSMain.edl

exit
