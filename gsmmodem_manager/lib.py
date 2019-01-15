#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4
###
#
# Copyright (c) 2016-2018 Pod Group Ltd
# Authors : J. Félix Ontañón <felix.ontanon@podgroup.com>

import serial
import time
import logging

# Inspired in http://m2msupport.net/m2msupport/atcsq-signal-quality/
def signal_quality(rssi_dBm):
    if rssi_dBm <= -113: return 'No Signal'
    elif rssi_dBm == -111: return 'Marginal, No Signal'
    elif -109 <= rssi_dBm < -93: return 'Marginal'
    elif -93 <= rssi_dBm < -83: return 'OK'
    elif -83 <= rssi_dBm < -73: return 'Good'
    elif rssi_dBm >= -73: return 'Excellent'
    else: return "Not valid rssi_dBm"

class GSMModem(object):
    """Super class for GSM modems. Only Standard Hayes AT commands supported."""

    __conf = {'devicefile':'', 'baudrate': ''}

    VENDOR_ID, PRODUCT_ID = 0x0000, 0x0000,
    VENDOR, PRODUCT = 'GSM Modem', 'Generic'

    # As per ETSI TS 127 007 v10.3.0 AT Commands set for User Equipment
    # Format of dictionary
    #    {
    #        "0": [             -- RSSI, from 0 to 32
    #            -113,          -- Power from -113dBm to -51dBm
    #            "No Signal",   -- Description of signal strength
    #            0              -- Signal percentaje from 0 (bad) to 100 (good)
    #        ], 
    #        ... 
    #    }
    RSSI_DBM = dict(zip(
        range(0, 32), # 0 to 31
        [(x, signal_quality(x),n*100/32) for n,x in enumerate(range(-113, -49, 2))]
    )); del x
    RSSI_DBM[99] = (-114, 'Not known or not detectable', 0)

    def __init__(self, devicefile, baudrate, timeout=25):
        self.__conf['devicefile'], self.__conf['baudrate'] = devicefile, baudrate
        self.__ser = serial.Serial(devicefile, baudrate, timeout=25)
        self._logger = logging.getLogger('carrierwatchdog.modem')
        if not self._logger.handlers: logging.basicConfig() # In the case there's no parent logger, lets log anyway in basic mode

    def __str__(self):
        return self.VENDOR + ' ' + self.PRODUCT + ' (' + hex(self.VENDOR_ID) + ',' + hex(self.PRODUCT_ID) + ')'

    # By default 2 seconds of sleep before reading command response. Randomly choosed :D
    def _send_command(self, command, sleeptime=2):
        self.__ser.write(command+"\r\n")
        time.sleep(sleeptime)

        ret = []
        while self.__ser.inWaiting() > 0:
            msg = self.__ser.readline().strip().replace("\r","").replace("\n","")
            if msg != "":
                ret.append(msg)

        return ret

    def set_operator(self, plmn, sleeptime=2):
        command = 'AT+COPS=1,2,"' + plmn + '"'
        response = self._send_command(command, sleeptime)
        
        if len(response) and response[0] == 'OK': 
            return True, command, None
        elif response is None or response == []:
            return True, command, None
        else:
            self._logger.error('Set operator failed with: ' + str(response))
            return False, command, response

    def get_operator(self, sleeptime=2):
        command = 'AT+COPS?'
        response = self._send_command(command, sleeptime)

        # This case mode, format, oper and optionally AcT is returned.
        if len(response) == 2:
            # Split response in chunks: mode, [format, oper, [AcT]]
            resp_split = response[0].split(':')[1].split(',') 
            if len(resp_split) >= 3: # Theres an oper in the response.
                oper = resp_split[2].replace('"', '')
                return True, command, oper
            else: # Most likely to be ['+COPS: 1', 'OK'], no operator selected
                self._logger.error('No operator selected: ' + str(response))
                return False, command, response
        # CME Error !!
        else:
            self._logger.error('Get operator failed with: ' + str(response))
            return False, command, response

    def register(self, lac=2, sleeptime=2):
        command = 'AT+CREG=' + str(lac) # 1 = enable | 2 = enable with lac/cellid info
        response = self._send_command(command, sleeptime)

        if len(response) and response[0] == 'OK':
            return True, command, response[0]
        if response is None or response is []:
            # It seems that if already registered
            # nothing will show but it is already
            # authenticated
            return True, command, response
        else:
            self._logger.error('Registration failed with: ' + str(response))
            return False, command, response

    # First attach to PS domain. Let's give it 10 secs at least.
    def activate_pdp_context(self, sleeptime=10):
        command_pdp_attachment = 'AT+CGATT=1'
        command_pdp_activate = 'AT+CGACT=1,1'

        response = self._send_command(command_pdp_attachment, sleeptime/2)

        if len(response) and response[0] == 'OK':
            response = self._send_command(command_pdp_activate, sleeptime/2)
            if len(response) and response[0] == 'OK':
                return True, command_pdp_activate, None
            else:
                return False, command_pdp_activate, response
        else:
            return False, command_pdp_attachment, response

    def deactivate_pdp_context(self, sleeptime=2):
        command = 'AT+CGATT=0'
        response = self._send_command(command, sleeptime)

        if len(response) and response[0] == 'OK':
            return True, command, None
        else:
            return False, command, response

    def get_pdp_context(self, sleeptime=2):
        command = 'AT+CGATT?'
        response = self._send_command(command, sleeptime)

        if len(response) == 2 and response[-1] == 'OK':
            response = {"pdp_attached" : (response[0].split(" ")[-1] == 1)}
            return True, command, response
        else:
            return False, command, response

    def get_signal_quality(self, sleeptime=2):
        """Returns Signal Quality as RSSI,BER string. Use GSMModem.sq_to_rssi to convert to RSSI dBm"""

        command = 'AT+CSQ'
        response = self._send_command(command, sleeptime)

        if len(response) >= 2 and response[1] == 'OK':
            sq = response[0].split(':')[1].replace(' ','')
            return True, command, sq
        else:
            return False, command, response

    def sq_to_rssidBm(self, sq):
        sq = int(sq) # Just in case it is not a integer
        return self.RSSI_DBM[sq]

    def get_imsi(self, sleeptime=2):
        command = "AT+CIMI"
        response = self._send_command(command, sleeptime)

        if len(response) == 2 and response[1] == 'OK': 
            return True, command, response[0]
        else: 
            return False, command, response

    def get_imei(self, sleeptime=2):
        command = "AT+GSN"
        response = self._send_command(command, sleeptime)

        if len(response) == 2 and response[1] == 'OK': 
            return True, command, response[0]
        else: 
            return False, command, response

    def get_apn(self):
        command = 'AT+CGDCONT?'
        response = self._send_command(command, sleeptime=1)

        # Sometimes modem send trash characters before the OK
        # but if OK is the last line then everything went well
        # this might be caused by the noise in serial connection
        if len(response) > 0 and response[-1] == 'OK': 
            return True, command, response[:-1]
        else:
            return False, command, response

    def set_apn(self, context_number, apn_name, sleeptime=2):
        assert isinstance(context_number, int), "PDP context # must be int"
        command = 'AT+CGDCONT='+ str(context_number) +',"IP","'+ apn_name + '",""'
        response = self._send_command(command, sleeptime)

        if len(response) == 1 and response[0] == 'OK': 
            return True, command, response[0]
        else:
            return False, command, response

    def reset_modem(self):
        command = 'ATZ'
        response = self._send_command(command, sleeptime=1)

        # Sometimes modem send trash characters before the OK
        # but if OK is the last line then everything went well
        # this might be caused by the noise in serial connection
        if len(response) > 0 and response[-1] == 'OK': 
            return True, command, response
        else:
            return False, command, response

    def get_serial_conf(self):
        return self.__conf

    def close_connection(self):
        self.__ser.close()


# Further details HUAWEI_MS2131_AT_Command_Interface_Specification
class HuaweiModem(GSMModem):
    """Super class for Huawei GSM USB dongles, supporting Huawei extended AT commands and specific definitions."""

    VENDOR_ID = 0x12d1
    VENDOR = 'Huawei'

    STAT_NOTREG, STAT_REGHOME, STAT_SEARCH, STAT_DENIED, STAT_UNK, STAT_REGROAM = '0', '1', '2', '3', '4', '5'

    def __init__(self, devicefile, baudrate, timeout=25):
        super(HuaweiModem, self).__init__(devicefile, baudrate, timeout)

    # Surprisingly CGREG returns LAC/CellID. CREG doesn't. Is this Huawei specific behaviour?
    def get_registration_info(self):
        command = 'AT+CGREG?'
        response = self._send_command(command) 

        if len(response) == 2 and response[1] == 'OK': 
            params = ['n', 'stat', 'lac', 'cid']
            reg = map(lambda item: item.replace('"', '').strip(), response[0].split(':')[1].split(','))
            return True, command, dict(zip(params,reg))
        else:
            self._logger.error('Get registration info failed with: ' + str(response))
            return False, command, response

    def set_operator(self, plmn):
        return super(HuaweiModem, self).set_operator(plmn, 10) # 10 secs for this specific device worked

    def get_operator(self):
        return super(HuaweiModem, self).get_operator(5) # 5 secs for this specific device worked

    def get_iccid(self, sleeptime=2):
        command = "AT^ICCID?"
        response = self._send_command(command, sleeptime)

        if len(response) == 2 and response[1] == 'OK':
            return True, command, response[0].split(': ')[1]
        else:
            return False, command, response


# Further details HUAWEI_MS2131_AT_Command_Interface_Specification
class HuaweiMS2131(HuaweiModem):

    PRODUCT_ID = 0x1506
    PRODUCT = 'MS2131'

    MODE_AUTO, MODE_GSM, MODE_WCDMA, MODE_NOTCHANGED = '2', '13', '14', '16'
    ACT_AUTO, ACT_GSM, ACT_UMTS, ACT_NOTCHANGED = '0', '1', '2', '3'
    ROAM_NO, ROAM_YES, ROAM_NA = '0', '1', '2'

    def __init__(self, devicefile, baudrate, timeout=25):
        super(HuaweiMS2131, self).__init__(devicefile, baudrate, timeout)

    def get_access_technology(self):
        # As per HUAWEI_MS2131_AT_Command_Interface_Specification Section 9.6: Command of Setting System Configurations
        command = 'AT^SYSCFG?'
        response = self._send_command(command)

        if len(response) == 2 and response[1] == 'OK': 
            mode, acqorder, band, roam, srvdomain = response[0].split(':')[1].split(',')
            return True, command, {'acqorder': acqorder.replace('"',''), 'roam': roam}
        else: 
            return False, command, response

    # Further details Section 9.6: Command of Setting System Configurations
    def set_access_technology(self, act):
        assert act in [self.ACT_AUTO, self.ACT_GSM, self.ACT_UMTS]
        if act == self.ACT_GSM: mode = self.MODE_GSM
        elif act == self.ACT_UMTS: mode = self.MODE_WCDMA
        else: mode = self.ACT_NOTCHANGED

        command = "AT^SYSCFG=" + mode + ',0' + act + ',3FFFFFFF,1,2' # Mode / ACT / Any Band / Roam enabled / CS+PS used
        response = self._send_command(command, 1) # TODO: Sleep time of 1 worked for me! Why? Who knows!

        if len(response) and response[0] == 'OK':
            return True, command, None
        else:
            return False, command, response

    def set_echo(self, on=False):
        """Turn echo mode ON or OFF
        - on: True (activate) / False (deactivate) echo
        This lib expects the echo to be OFF"""
        if on:
            command = 'ATE1'
        elif not on:
            command = 'ATE0'
        
        response = self._send_command(command) 

        if len(response) and response[0] == 'OK':
            return True, command, None
            
        else:
            return False, command, response


# TODO: Look for HUAWEI_MS2372_AT_Command_Interface_Specification
class HuaweiMS2372h(HuaweiModem):

    PRODUCT_ID = 0x1506
    PRODUCT = 'MS2372h'

    ACT_AUTO, ACT_GSM, ACT_UMTS, ACT_LTE, ACT_NOTCHANGED = '00', '01', '02', '03', '99'
    ROAM_NO, ROAM_YES, ROAM_NA = '0', '1', '2'

    def __init__(self, devicefile, baudrate, timeout=25):
        super(HuaweiMS2372h, self).__init__(devicefile, baudrate, timeout)

    def get_access_technology(self):
        command = 'AT^SYSCFGEX?'
        response = self._send_command(command, sleeptime=10)

        if len(response) == 2 and response[1] == 'OK': 
            acqorder, band, roam, srvdomain, lteband = response[0].split(':')[1].split(',')
            return True, command, {'acqorder': acqorder.replace('"',''), 'roam': roam}
        elif len(response) >= 2 and response[-1] == 'OK': 
            acqorder, band, roam, srvdomain, lteband = response[-2].split(':')[1].split(',')
            return True, command, {'acqorder': acqorder.replace('"',''), 'roam': roam}
        else:
            self._logger.error('Get access technology failed with: ' + str(response))
            return False, command, response

    def set_access_technology(self, act):
        assert act in [self.ACT_AUTO, self.ACT_GSM, self.ACT_UMTS, self.ACT_LTE]
        # ACT / Any Band / Roam enabled / CS+PS used / LTE Any Band
        command = 'AT^SYSCFGEX="' + act + '",3FFFFFFF,1,2,7FFFFFFFFFFFFFFF,,' 
        response = self._send_command(command, sleeptime=10)

        if len(response) and response[0] == 'OK':
            return True, command, None
        elif len(response) > 1 and response[-1] == 'OK':
            return True, command, None
        elif response == []:
            return True, command, None
        else:
            self._logger.error('Set access technology failed with: ' + str(response))
            return False, command, response
    

class HuaweiE3372(HuaweiModem):
    """Tested specifically for Huawei E3372H-510.
    This modem returns more information on setting
    technolgy, this info is returned as a list in
    response"""

    PRODUCT_ID = 0x155e
    PRODUCT = 'E3372'

    ACT_AUTO, ACT_GSM, ACT_UMTS, ACT_LTE, ACT_NOTCHANGED = '00', '01', '02', '03', '99'
    ROAM_NO, ROAM_YES, ROAM_NA = '0', '1', '2'

    def __init__(self, devicefile, baudrate, timeout=25):
        super(HuaweiE3372, self).__init__(devicefile, baudrate, timeout)
        echo_off = False
        counter = 0
        while not echo_off:
            if counter == 3:
                raise Exception('Cannot set echo off')
            echo_off,_,_ = self.set_echo(on=False)
            counter += 1
    
    def stop_periodic_messages(self):
        command = 'AT^CURC=0'
        response = self._send_command(command)

        if len(response) >= 1 and response[-1] == 'OK':
            return True, command, response[-1]
        else:
            return False, command, response

    def get_access_technology(self):
        command = 'AT^SYSCFGEX?'
        response = self._send_command(command)

        if len(response) == 2 and response[1] == 'OK':
            acqorder, band, roam, srvdomain, lteband = response[0].split(':')[1].split(',')
            return True, command, {'acqorder': acqorder.replace('"',''), 'roam': roam}
        else:
            return False, command, response

    def set_access_technology(self, act):
        assert act in [self.ACT_AUTO, self.ACT_GSM, self.ACT_UMTS, self.ACT_LTE]
        # ACT / Any Band / Roam enabled / CS+PS used / LTE Any Band
        command = 'AT^SYSCFGEX="' + act + '",3FFFFFFF,1,2,7FFFFFFFFFFFFFFF,,' 
        
        # Lesser waiting time translates to error 
        response = self._send_command(command, 2)
        
        # It can happen that switching bewteen ACT some
        # trash characteres are generated
        if len(response) > 0 and response[-1] == 'OK':
            return True, command, response
        else:
            return False, command, response

    def set_echo(self, on=False):
        """Turn echo mode ON or OFF
        - on: True (activate) / False (deactivate) echo
        This lib expects the echo to be OFF"""
        if on:
            command = 'ATE1'
        elif not on:
            command = 'ATE0'
        
        response = self._send_command(command, sleeptime=5) 

        if len(response) and response[0] == 'OK':
            return True, command, None
            
        else:
            return False, command, response

    def get_registration_info(self):
        # On other Huawei modems AT+CGREG works with LAC and CID
        # but this one outputs LAC & CID with CREG insead of CGREG
        command = 'AT+CREG?'
        response = self._send_command(command) 

        if len(response) == 2 and response[1] == 'OK': 
            params = ['n', 'stat', 'lac', 'cid']
            reg = map(lambda item: item.replace('"', '').strip(), response[0].split(':')[1].split(','))
            response = dict(zip(params,reg))
            return True, command, response
        else:
            return False, command, response
