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

from multiprocessing import Process, Event
from math import floor
from scipy import weave
import numpy as np
import time
import struct
import logging
from RMS.VideoExtraction import Extractor
from RMS.Formats import FFbin

class Compressor(Process):
    """Compress list of numpy arrays (video frames).
    Output is in Flat-field Temporal Pixel (FTP) format like the one used by CAMS project (P. Jenniskens et al., 2011).
    """

    running = False
    
    def __init__(self, array1, startTime1, array2, startTime2, config):
        """
        
        @param array1: first numpy array in shared memory of grayscale video frames
        @param startTime1: float in shared memory that holds time of first frame in array1
        @param array2: second numpy array in shared memory
        @param startTime1: float in shared memory that holds time of first frame in array2
        @param config: configuration class
        """
        
        super(Compressor, self).__init__()
        
        self.array1 = array1
        self.startTime1 = startTime1
        self.array2 = array2
        self.startTime2 = startTime2
        self.config = config
    
    def compress(self, frames):
        """Compress frames to the FTP-compatible array.
        
        @param frames: grayscale frames stored as 3d numpy array
        
        @return: 3d numpy array in format: (N, y, x) where N is [0, 4)
        """
        
        out = np.empty((4, frames.shape[1], frames.shape[2]), np.uint8)
        
        code = """
        unsigned int x, y, n, acc, var, max, max_frame, pixel, num_equal, mean;
        unsigned short rand_count = 0;
        
        unsigned int height = Nframes[1];
        unsigned int width = Nframes[2];
        unsigned int frames_num = Nframes[0];
        unsigned int frames_num_minus_one = frames_num - 1;
        unsigned int frames_num_minus_two = frames_num - 2;
        
        unsigned char randomN[65536] = {};
        unsigned int arand = 1;
        for(n=0; n<65536; n++) {
            arand = (arand * 32719 + 3) % 32749;
            randomN[n] = (unsigned char)(32767.0 / (double)(1 + arand % 32767));
        }
            
        for(y=0; y<height; y++) {
            for(x=0; x<width; x++) {
                acc = 0;
                var = 0;
                max = 0;
                
                // calculate mean, stddev, max, and max frame
                for(n=0; n<frames_num; n++) {
                    pixel = FRAMES3(n, y, x);
                    acc += pixel;
                    var += pixel*pixel;
                    
                    if(pixel > max) {
                        max = pixel;
                        max_frame = n;
                        num_equal = 1;
                    } else if(pixel == max) { // randomize taken frame number for max pixel
                        num_equal++;
                        
                        rand_count++; //rand_count is unsigned short, which means it will overflow back to 0 after 65,535
                        if(num_equal <= randomN[rand_count]) {
                            max_frame = n;
                        }
                    }
                }
                
                //mean
                acc -= max;    // remove max pixel from average
                mean = acc / frames_num_minus_one;
                
                //stddev
                var -= max*max;     // remove max pixel
                var -= acc*mean;    // subtract average squared sum of all values (acc*mean = acc*acc/frames_num_minus_one)
                var = sqrt(var / frames_num_minus_two);
                
                // output results
                OUT3(0, y, x) = max;
                OUT3(1, y, x) = max_frame;
                OUT3(2, y, x) = mean;
                OUT3(3, y, x) = var;
            }
        }
        """
        
        weave.inline(code, ['frames', 'out'], verbose=2, extra_compile_args=self.config.weaveArgs, extra_link_args=self.config.weaveArgs)
        return out
    
    def save(self, arr, startTime, N):
        """Write metadata and data array to FTP .bin file.
        
        @param arr: 3d numpy array in format: (N, y, x) where N is [0, 4)
        @param startTime: seconds and fractions of a second from epoch to first frame
        @param N: frame counter (ie. 0000512)
        """
        
        dateTime = time.strftime("%Y%m%d_%H%M%S", time.localtime(startTime))
        millis = int((startTime - floor(startTime))*1000)
        
        filename = str(self.config.stationID).zfill(3) +  "_" + dateTime + "_" + str(millis).zfill(3) + "_" + str(N).zfill(7)
        
        ff = FFbin.ff_struct()
        ff.array = arr
        ff.nrows = arr.shape[1]
        ff.ncols = arr.shape[2]
        ff.nbits = 8
        ff.first = N+256
        ff.camno = self.config.stationID
        
        FFbin.write(ff, "./", filename)
        
        return filename
    
    def stop(self):
        """Stop the process.
        """
        
        self.exit.set()
        self.join()
        
    def start(self):
        """Start the process.
        """
        
        self.exit = Event()
        super(Compressor, self).start()
        
    def run(self):
        """Retrieve frames from list, convert, compress and save them.
        """
        
        n = 0
        
        while not self.exit.is_set():
            while self.startTime1.value==0 and self.startTime2.value==0: #block until frames are available
                if self.exit.is_set():    #exit function if process was stopped
                    return
                
            t = time.time()
            
            if self.startTime1.value != 0:
                startTime = self.startTime1.value #retrieve time of first frame
                frames = self.array1 #copy frames
                self.startTime1.value = 0
            else:
                startTime = self.startTime2.value #retrieve time of first frame
                frames = self.array2 #copy frames
                self.startTime2.value = 0
            
            logging.debug("memory copy: " + str(time.time() - t) + "s")
            t = time.time()
            
            compressed = self.compress(frames)
            
            logging.debug("compression: " + str(time.time() - t) + "s")
            t = time.time()
            
            filename = self.save(compressed, startTime, n*256)
            n += 1
            
            logging.debug("saving: " + str(time.time() - t) + "s")
            
            ve = Extractor(self.config)
            ve.start(frames, compressed, filename)
    