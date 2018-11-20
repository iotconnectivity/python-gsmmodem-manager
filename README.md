# python-gsmmodem-manager

Framework for communicating and interacting with 2G/3G/4G usb modems

## Table of Contents

- [Description](#description)
- [Hardware supported](#hardware)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [To Do](#todo)
- [Standards](#standards)


## Description

Modems usually offer an interface via AT commands. A serial protocol originally developed by [Dennis Hayes](https://en.wikipedia.org/wiki/Hayes_command_set). There's a basic set of AT commands almost all modems support, and an extended set only some support. Every single manufacturer adds their extended set of commands to provide with vendor specific functionallity.

This python library is aimed to encapsulate all complicated vendor specific logic of USB modems and serving a common library to perform typical operations like:

- Selecting a network operator.
- Choosing an access technology (2G/3G/4G).
- Registering in the network.
- Activating/deactivating a PDP context.
- Get IMEI from device. Get IMSI from SIM card.
- etc.

## Hardware

So far, the list of supported modems are:

- Huawei MS2131
- Huawei MS2372h
- Huawei E3372

Plese have a look the [Contributing](#contributing) section to extend support for other modems.
Let's join efforts!

## Installation

You can install via pip from our Github repository directly (pending to submit to [pypi](https://pypi.org))

```shell
pip install git+https://github.com/PodgroupConnectivity/python-gsmmodem-manager.git@9a9ccfb7f0e7de4124c7c6f7791a721e20383e73
```

As per the lack of dependencies, It has been succesfully tested on the following platforms:

- Linux (Intel/AMD Ubuntu 18.04)
- Raspberry-Pi 3 (ARM Raspbian GNU/Linux 8)
- Rasbberry-Pi Zero (ARM Raspbian GNU/Linux 8)

## Usage

```python
# Lets use a generic modem and test some basic AT commands
from gsmmodem_manager import GSMModem, signal_quality

# The USB modem is attached to /dev/ttyUSB0. Let's communicate with 9600 baud.
modem = GSMModem("/dev/ttyUSB0", "9600")

modem.get_imei() # (True, 'AT+GSN', '{IMEI CODE GOES HERE}')
modem.get_imsi() # (True, 'AT+CIMI', '{IMSI CODE GOES HERE}')
modem.set_operator('21401') # (True, 'AT+COPS=1,2,"21401"', None)
sq = modem.get_signal_quality() # (True, 'AT+CSQ', '11,99')
signal_quality(sq[2]) # 'Excellent'

# Let's use a specific Huawei MS2131 modem now
from gsmmodem_manager import HuaweiMS2131
modem = GSMModem("/dev/ttyUSB0", "9600")

# The following snipped selects Spain Vodafone 4G, registers and acquire data.
# Please note this does not generate a PPP interface, but establish the session.
modem.set_operator('21401') # Selects Spain Vodafone
modem.set_access_technology(HuaweiMS2131.ACT_UMTS) # Choses 4G. Each modem has its own codes.
modem.register() # Registers in the network
modem.activate_pdp_context() # Acquires PDP Context (data session)
modem.deactivate_pdp_context() # Closes PDP Context (data session)
```

## Contributing

Please contribute using [Github Flow](https://guides.github.com/introduction/flow/). Create a branch, add commits, and [open a pull request](https://github.com/fraction/readme-boilerplate/compare/).

Please note this source code has been released under the GPLv3 terms and all contributions will be considered under the same license. Have a look at the LICENSE file distributed with this code.

## TODO

The following is a non-comprehensive list of pending developments to add. 
We're happy to accept any contribution :)

- Hot-detecting the USB modem and determine whether it is compatible or not. Via UDEV.
- Listen to udev events when USB modem is available or not to pause/resume any activity.
- Finish compatibility with K3765 HSPA

## Standards

[AT command set for User Equipment](https://www.etsi.org/deliver/etsi_ts/127000_127099/127007/10.03.00_60/ts_127007v100300p.pdf)
