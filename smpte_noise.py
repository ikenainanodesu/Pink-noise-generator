#!/usr/bin/env python
#
# Copyright (c) 2015, 2021,
# The Society of Motion Picture and Television Engineers
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The name of the author may not be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# SMPTE ST 2095-1 Band-Limited Pink Noise Generator
#
# Produces band limited, pink noise from pseudorandom numbers as a 24-bit
# WAVE file.
#
# r1 2015-02-18 -- Distributed with SMPTE ST 2095-1:2015
# r2 2021-12-01 -- Distributed with SMPTE ST 2095-1:2022 (no substantive changes)
#
VERSION = "1.4"
#

import sys
import math
import struct
from optparse import OptionParser

parser = OptionParser(version='%prog v' + VERSION + \
                      '\nSpecify the -h (help) option for further information about %prog',
                      usage="""%prog [-h | --help] [--version]\n       %prog [options] <outfile>""",
                      description="Create a PCM Wave file containing pink noise per SMPTE ST 2095-1:2015.")

parser.set_defaults(VerboseFlag = True, # Print statistics to stdout
                    Duration_sec = 10,  # Duration of the output stream in seconds
                    SampleRate = 48000, # Output sample rate in samples/sec
                    HpFc = 10.0,        # Highpass filter cutoff frequency in Hz
                    LpFc = 22400.0,     # Lowpass filter cutoff frequency in Hz
                    ChannelCount = 1    # Number of output channels (all identical)
                    )

parser.add_option('-9', '--96k', action='store_const', dest='SampleRate', const=96000,
                  help="Select 96.0 kHz sample rate (default is 48.0 kHz)")

parser.add_option('-c', '--channels', action='store', dest='ChannelCount', type="int", metavar='<n>',
                  help="Set the number of channels in the output file (all contain identical noise)")

parser.add_option('-d', '--duration', action='store', dest='Duration_sec', type="int", metavar='<sec>',
                  help="Set the minimum duration of the output file in seconds (default: %default)")

parser.add_option('-q', '--quiet', action='store_false', dest='VerboseFlag',
                  help="Suppress output of statistics to stdout")

options, args = parser.parse_args()

if not args:
    parser.error("Output filename required.")

if options.Duration_sec == 0:
    options.Duration_sec = 10


# constants
sampleSize = 3     # Number of bytes per sample per channel
maxPeak = -9.5     # Clipping Threshold in dB FS (+/-1.0 = 0 dB)

# Initialize variables for generating a random number

# Perodicity in samples; a power of two, <= 2^31.
# Typical values are 524288, 1048576, 2097152 or 4194304.
samplesPerPeriod = 524288
randStep = 52737		   # Default step size for LCG PRNG

if options.SampleRate > 48000:
    samplesPerPeriod = 1048576
    randStep = 163841      # Special case LCG step for 1024K samples @ 96k

# set up PRNG
randMax = samplesPerPeriod - 1
seed = 0
white = 0.0
scaleFactor = 2.0 / float(randMax)

# Filter setup, see ST 2095-1:2015 for the details
#
maxAmp = pow(10.0, maxPeak / 20.0)

# Calculate omegaT for matched Z transform highpass filters
w0t = 2.0 * math.pi * options.HpFc / float(options.SampleRate)

#  Disaster check: Limit LpFc <= Nyquist
if options.LpFc > options.SampleRate/2.0:
    options.LpFc = options.SampleRate/2.0

# Calculate k for bilinear transform lowpass filters
k = math.tan(( 2.0 * math.pi * options.LpFc / float(options.SampleRate) ) / 2.0)
# precalculate k^2 (makes for a little bit cleaner code)
k2 = k * k

# Calculate biquad coefficients for bandpass filter components
hp1_a1 = -2.0 * math.exp(-0.3826835 * w0t) * math.cos(0.9238795 * w0t)
hp1_a2 = math.exp(2.0 * -0.3826835 * w0t)
hp1_b0 = (1.0 - hp1_a1 + hp1_a2) / 4.0
hp1_b1 = -2.0 * hp1_b0
hp1_b2 = hp1_b0

hp2_a1 = -2.0 * math.exp(-0.9238795 * w0t) * math.cos(0.3826835 * w0t)
hp2_a2 = math.exp(2.0 * -0.9238795 * w0t)
hp2_b0 = (1.0 - hp2_a1 + hp2_a2) / 4.0
hp2_b1 = -2.0 * hp2_b0
hp2_b2 = hp2_b0

lp1_a1 = (2.0 * (k2 - 1.0)) / (k2 + (k / 1.306563) + 1.0)
lp1_a2 = (k2 - (k / 1.306563) + 1.0) / (k2 + (k / 1.306563) + 1.0)
lp1_b0 = k2 / (k2 + (k / 1.306563) + 1.0)
lp1_b1 = 2.0 * lp1_b0
lp1_b2 = lp1_b0

lp2_a1 = (2.0 * (k2 - 1.0)) / (k2 + (k / 0.541196) + 1.0)
lp2_a2 = (k2 - (k / 0.541196) + 1.0) / (k2 + (k / 0.541196) + 1.0)
lp2_b0 = k2 / (k2 + (k / 0.541196) + 1.0)
lp2_b1 = 2.0 * lp2_b0
lp2_b2 = lp2_b0

# Declare delay line variables for bandpass filter and initialize to zero
w = 0.0
hp1w1 = 0.0
hp1w2 = 0.0
hp2w1 = 0.0
hp2w2 = 0.0
lp1w1 = 0.0
lp1w2 = 0.0
lp2w1 = 0.0
lp2w2 = 0.0

# Declare delay lines for pink filter network and initialize to zero
pink = 0.0
lp1 = 0.0
lp2 = 0.0
lp3 = 0.0
lp4 = 0.0
lp5 = 0.0
lp6 = 0.0

#
accum = 0.0
totalSamples = samplesPerPeriod + ( options.SampleRate * options.Duration_sec )
diff = totalSamples % samplesPerPeriod
if diff != 0:
    totalSamples += samplesPerPeriod - diff

# create and write the WAVE header
dataLength = sampleSize * ( totalSamples - samplesPerPeriod ) * options.ChannelCount
if dataLength+32 > 2**31-1:
    raise ValueError("The selected properties exceed the capacity of the header.")

waveHeader = \
    b"RIFF" + \
    struct.pack("<i", dataLength + 38) + \
    b"WAVE" + \
    b"fmt " + \
    struct.pack("<ihhiihhh",
                18,
                1,
                options.ChannelCount,
                options.SampleRate,
                sampleSize * options.ChannelCount * options.SampleRate,
                sampleSize * options.ChannelCount,
                8 * sampleSize,
                0) + \
    b"data" + \
    struct.pack("<i", dataLength)

writer = open(args[0], "wb") #"wb" (b for binary) required for Windows
writer.write(waveHeader)

# Generate a band-limited pink noise signal and write it to the WAV file.
# Before writing samples to the output we cycle the generator one complete
# series to populate the filter bank delay lines.

for i in range(totalSamples):
    # Generate a pseudorandom integer in the range 0 <= seed <= randMax.
    # Bitwise AND with randMax zeroes out any unwanted high order bits.
    seed = (1664525 * seed + randStep) & randMax
    # Scale to a real number in the range -1.0 <= white <= 1.0
    white = float(seed) * scaleFactor - 1.0

    # Run pink filter; a parallel network of first-order LP filters, scaled to
    # produce an output signal with target RMS = -21.5 dB FS (-18.5 dB AES FS)
    # when bandpass filter cutoff frequencies are 10 Hz and 22.4 kHz.
    lp1 = 0.9994551 * lp1 + 0.00198166688621989 * white
    lp2 = 0.9969859 * lp2 + 0.00263702334184061 * white
    lp3 = 0.9844470 * lp3 + 0.00643213710202331 * white
    lp4 = 0.9161757 * lp4 + 0.01438952538362820 * white
    lp5 = 0.6563399 * lp5 + 0.02698408541064610 * white
    pink = lp1 + lp2 + lp3 + lp4 + lp5 + lp6 + white * 0.0342675832159306
    lp6 = white * 0.0088766118009356

    # Run bandpass filter; a series network of 4 biquad filters
    # Biquad filters implemented in Direct Form II
    w = pink - hp1_a1 * hp1w1 - hp1_a2 * hp1w2
    pink = hp1_b0 * w + hp1_b1 * hp1w1 + hp1_b2 * hp1w2
    hp1w2 = hp1w1
    hp1w1 = w

    w = pink - hp2_a1 * hp2w1 - hp2_a2 * hp2w2
    pink = hp2_b0 * w + hp2_b1 * hp2w1 + hp2_b2 * hp2w2
    hp2w2 = hp2w1
    hp2w1 = w

    w = pink - lp1_a1 * lp1w1 - lp1_a2 * lp1w2
    pink = lp1_b0 * w + lp1_b1 * lp1w1 + lp1_b2 * lp1w2
    lp1w2 = lp1w1
    lp1w1 = w

    w = pink - lp2_a1 * lp2w1 - lp2_a2 * lp2w2
    pink = lp2_b0 * w + lp2_b1 * lp2w1 + lp2_b2 * lp2w2
    lp2w2 = lp2w1
    lp2w1 = w

    # Limit peaks to +/-MaxAmp
    if pink > maxAmp:
        pink = maxAmp
    elif pink < -maxAmp:
        pink = -maxAmp

    if i > randMax:
        # accumulate squared amplitude for RMS figure.
        accum += (pink * pink)

        # Write 3 bytes per sample. Scale to a 32-bit signed integer
        # and then encode as a little-endian byte sequence.
        out = struct.pack("<i", int(pink * 2147483647.0))

        # truncate the LSB and write the sample once for each channel
        for n in range(options.ChannelCount):
            writer.write(out[1:])
    #

writer.close()

if options.VerboseFlag:
    accum = 10.0 * math.log10(accum / float(totalSamples - samplesPerPeriod))
    print("{0:0.2f} seconds, RMS (dB) = {1:2.2f}".format(
        ( totalSamples - samplesPerPeriod ) / float(options.SampleRate),
        accum + 3.01))

#
# end ST-2095-1-noise-generator.py
#
