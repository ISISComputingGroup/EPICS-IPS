# edl Makefile for OxInstIPS
#
TOP = ../../..
include $(TOP)/configure/CONFIG

DATA += $(patsubst ../%, %, $(wildcard ../*.edl))
DATA += $(patsubst ../%, %, $(wildcard ../*.gif))
DATA += $(patsubst ../%, %, $(wildcard ../*.png))
DATA += $(patsubst ../%, %, $(wildcard ../test_*_GUI.sh))
DATA += launch_OxInstIPS_manualviewer.sh

include $(TOP)/configure/RULES

launch_OxInstIPS_manualviewer.sh: ../launch_OxInstIPS_manualviewer.sh
	cp ../launch_OxInstIPS_manualviewer.sh .
