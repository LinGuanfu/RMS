# RPi Meteor Station
# Copyright (C) 2015  Dario Zubovic
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from RMS.BufferedCapture import BufferedCapture
from RMS.Compression import Compressor
from multiprocessing import Array, Value
import RMS.ConfigReader as cr
import numpy as np
import ctypes
import logging
from time import time

def wait():
    try:
        raw_input("Press Enter to stop...")
    except EOFError:
        pass

if __name__ == "__main__":
    logging.basicConfig(filename="log.log", level=logging.DEBUG)
    logging.debug("########## START #########")
    logging.debug(time())
    
    config = cr.parse(".config")
    
    sharedArrayBase = Array(ctypes.c_uint8, 256*config.width*config.height)
    sharedArray = np.ctypeslib.as_array(sharedArrayBase.get_obj())
    sharedArray = sharedArray.reshape(256, config.height, config.width)
    startTime = Value('d', 0.0)
    
    sharedArrayBase2 = Array(ctypes.c_uint8, 256*config.width*config.height)
    sharedArray2 = np.ctypeslib.as_array(sharedArrayBase2.get_obj())
    sharedArray2 = sharedArray2.reshape(256, config.height, config.width)
    startTime2 = Value('d', 0.0)
    
    bc = BufferedCapture(sharedArray, startTime, sharedArray2, startTime2, config)
    
    c = Compressor(sharedArray, startTime, sharedArray2, startTime2, config)
    
    bc.startCapture()
    c.start()
    
    wait()
    
    bc.stopCapture()
    c.stop()