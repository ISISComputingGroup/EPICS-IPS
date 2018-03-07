#!/bin/sh
#
# Script test_OxInstIPS_detail_GUI.sh
#
# Runs the EDM details screen for the Oxford Instruments IPS 
# superconducting magnet power supply.
#
export EDMDATAFILES=.:../../../data:
export PATH=.:../../../bin/linux-x86_64:${PATH}

edm -x -m "P=TS-EA-SMC-01" OxInstIPS_detail.edl &
#edm -x -m "P=BL10J-EA-SMC-01" OxInstIPS_detail.edl &
exit
