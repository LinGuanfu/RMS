
from RMS.VideoExtraction import Extractor
import RMS.ConfigReader as cr
import RMS.Formats.FFbin as FFbin
from RMS.Routines.Grouping3D import find3DLines, getAllPoints


import os
import sys
import time
import numpy as np

from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Cython init
import pyximport
pyximport.install(setup_args={'include_dirs':[np.get_include()]})

if __name__ == "__main__":

    # Get bin path and name from the given argument
    bin_name = sys.argv[1]
    if os.sep in bin_name:
        bin_name = bin_name.split(os.sep)
        dirname = (os.sep).join(bin_name[:-2])
        bin_name = bin_name[-1]

    # 3 bina:
    # dirname = '2015110506 bolid' + os.sep
    # bin_name = 'FF454_20151105_190520_767_0043520.bin'

    # 3 bina:
    # dirname = '2015110304 bolid' + os.sep
    # bin_name = 'FF459_20151103_182709_210_0189440.bin'

    # 2 bina
    # dirname = '20151111213 visnjan' + os.sep
    # bin_name =  'FF459_20151112_011549_770_0781312.bin'

    # 1 bin:
    # dirname = 'RIB2015062627 fireball' + os.sep
    # bin_name =  'FF454_20150626_211351_964_0153088.bin'

    # sample bins (2 komada)
    # dirname = 'sample_bins' + os.sep 
    # bin_name = 'FF459_20150704_230501_667_0313856.bin'
    # bin_name = 'FF459_20150705_012154_094_0516096.bin'
    # bin_name = 'FF459_20150705_220250_982_0224768.bin'

    # dirname = ''
    # bin_name = 'FF453_20150421_011431_274_0608512.bin'
    # bin_name = 'FF494_20151121_235145_509_0733184.bin'
    # bin_name = 'FF494_20151122_004543_852_0814080.bin'

    # Load config file
    config = cr.parse(".config")

    # Load compressed file
    compressed = FFbin.read('samples' + os.sep + dirname, bin_name, array=True).array

    # Show maxpixel
    ff = FFbin.read('samples' + os.sep + dirname, bin_name)
    plt.imshow(ff.maxpixel, cmap='gray')
    plt.show()

    plt.clf()
    plt.close()

    # Dummy frames (empty)
    frames = np.zeros(shape=(256, compressed.shape[1], compressed.shape[2]), dtype=np.uint8)

    extract_obj = Extractor(config)
    extract_obj.compressed = compressed
    extract_obj.frames = frames

    event_points = extract_obj.findPoints()

    print event_points

    if event_points:

        # Plot lines in 3D
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        points = np.array(event_points, dtype = np.uint8)

        xs = points[:,1]
        ys = points[:,0]
        zs = points[:,2]

        print len(xs)

        # Plot points in 3D
        ax.scatter(xs, ys, zs)

        # Set limits
        plt.xlim((0, compressed.shape[2]/config.f))
        plt.ylim((0, compressed.shape[1]/config.f))
        ax.set_zlim((0, 255))

        # Set labels
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Frame')

        t1 = time.clock()

        # Run line finding

        line_list = find3DLines(event_points, time.time(), config)

        print line_list

        print 'Elapsed time: ', time.clock() - t1

        # Define line colors to use
        ln_colors = ['r', 'g', 'y', 'k', 'm', 'c']

        # Plot detected lines in 3D
        for i, detected_line in enumerate(line_list):
            # detected_line = detected_line[0]
            xs = [detected_line[0][0], detected_line[1][0]]
            ys = [detected_line[0][1], detected_line[1][1]]
            zs = [detected_line[0][2], detected_line[1][2]]
            ax.plot(ys, xs, zs, c = ln_colors[i%6])


        # Plot grouped points
        for i, detected_line in enumerate(line_list):

            x1, x2 = detected_line[0][0], detected_line[1][0]

            y1, y2 = detected_line[0][1], detected_line[1][1]

            z1, z2 = detected_line[0][2], detected_line[1][2]

            detected_points = getAllPoints(event_points, x1, y1, z1, x2, y2, z2, config)

            if not detected_points.all():
                continue

            detected_points = np.array(detected_points)

            xs = detected_points[:,1]
            ys = detected_points[:,0]
            zs = detected_points[:,2]

            ax.scatter(xs, ys, zs, c = ln_colors[i%6], s = 40)

        plt.show()

        plt.clf()
        plt.close()



