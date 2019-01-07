#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: ts=4
###
# 
# Copyright (c) 2018 Pod Group Ltd.
# Authors : J. Félix Ontañón <felix.ontanon@podgroup.com>

# Import package form parent dir https://gist.github.com/JungeAlexander/6ce0a5213f3af56d7369
import os,sys,inspect
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Now it can be imported :)
from gsmmodem_manager import HuaweiMS2131
modem = HuaweiMS2131(len(sys.argv) >= 2 and sys.argv[1] or '/dev/ttyUSB0', '9600')

# The testing suite also works with HuaweiMS2372h
# from gsmmodem_manager import HuaweiMS2372h
# modem = HuaweiMS2372h(len(sys.argv) >= 2 and sys.argv[1] or '/dev/ttyUSB0', 115200)

def test_generic_commands(modem):
    print modem.get_imsi()

def test_tech_switch(modem):
    print modem.get_access_technology()
    print modem.set_access_technology(modem.ACT_UMTS)
    print modem.get_access_technology()
    print modem.set_access_technology(modem.ACT_UMTS)
    print modem.get_access_technology()

def test_op_switch(modem):
    print modem.get_operator()
    print modem.set_operator('21401') # Spain Vodafone
    print modem.get_operator()
    print modem.set_operator('21403') # Spain Orange
    print modem.get_operator()

def test_act_op(modem, act, op, data_session_time=10):
    status, command, response = modem.set_access_technology(act)
    if status:
        print "Access Techology selected successfully", act
        status, command, response = modem.set_operator(op)
        if status:
            print "Operator selected successfully", op
            status, command, response = modem.register()
            if status: 
                print "Register OK"
                status, command, response = modem.activate_pdp_context()
                if status: 
                    print "PDP context activated ..."

                    # Initiating checks
                    status, command, cur_act = modem.get_access_technology()
                    status, command, cur_op = modem.get_operator()
                    status, command, sq = modem.get_signal_quality()
                    rssi_dBm = modem.sq_to_rssidBm(sq.split(',')[0])
                    status, command, cur_reg = modem.get_registration_info()

                    print '... CHECK Access Tech: ' + str(cur_act['acqorder'] == act) + ', ' + cur_act['acqorder']
                    print '... CHECK Roaming Enabled: ' + str(cur_act['roam'] == modem.ROAM_YES) + ', ' + cur_act['roam']
                    print '... CHECK Operator Selected: ' + str(cur_op == op) + ', ' + cur_op
                    print '... RSSI, BER: (' + str(rssi_dBm[0]) + ', ' + rssi_dBm[1] + '), ' + sq.split(',')[1]
                    print '... STAT: ' + cur_reg.get('stat', '')
                    print '... LAC: ' + cur_reg.get('lac', '')
                    print '... CID: ' + cur_reg.get('cid', '')

                    # time.sleep(5) # Perhaps not useful after the time checks above take
                    status, command, response  = modem.deactivate_pdp_context()
                    if status:
                        print "PDP context deactivated"
                    else:
                        print "Aborting: PDP context deactivation not possible", command, response
                else:
                    print "Aborting: cannot activate PDP context", command, response
            else:
                print "Aborting: cannot register", command, response
        else:
            print "Aborting: cannot set operator", command, response
    else:
        print "Aborting: cannot set access technology", command, response

if __name__ == '__main__':
    import sys

    test_generic_commands(modem)
    test_op_switch(modem)
    test_act_op(modem, modem.ACT_UMTS, '310480') # 3G EEUU iConnect. This will fail in Spain
    test_act_op(modem, modem.ACT_GSM, '21401') # 2G Spain Vodafone.
    test_act_op(modem, modem.ACT_UMTS, '21401') # 3G Spain Vodafone.
    test_act_op(modem, modem.ACT_GSM, '21403') # 2G Spain Orange.
    test_act_op(modem, modem.ACT_UMTS, '21403') # 3G Spain Orange.
    modem.close_connection()