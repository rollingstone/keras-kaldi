#!/usr/bin/python3

##  Copyright (C) 2016 D S Pavan Kumar
##  dspavankumar [at] gmail [dot] com
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program.  If not, see <http://www.gnu.org/licenses/>.


import keras
from keras.optimizers import SGD
import keras.backend as K
from dataGenSequences import dataGenSequences
import sys
import os

if __name__ != '__main__':
    raise ImportError ('This script can only be run, and can\'t be imported')

if len(sys.argv) != 7:
    raise TypeError ('USAGE: train.py data_cv ali_cv data_tr ali_tr gmm_dir dnn_dir')

data_cv = sys.argv[1]
ali_cv  = sys.argv[2]
data_tr = sys.argv[3]
ali_tr  = sys.argv[4]
gmm     = sys.argv[5]
exp     = sys.argv[6]

## Learning parameters
learning = {'rate' : 0.1,
            'batchSize' : 256,
            'spliceSize' : 11,
            'minEpoch' : 5,
            'lrScale' : 0.5,
            'lrScaleCount' : 18,
            'minValError' : 0.002}

os.makedirs (exp, exist_ok=True)

trGen = dataGenSequences (data_tr, ali_tr, gmm, learning['batchSize'], learning['spliceSize'])
cvGen = dataGenSequences (data_cv, ali_cv, gmm, learning['batchSize'], learning['spliceSize'])

## Initialise learning parameters and models
s = SGD(lr=learning['rate'], decay=0, momentum=0.5, nesterov=True)
m = keras.models.Sequential([
                keras.layers.LSTM(256, input_shape=(learning['spliceSize'],trGen.inputFeatDim), activation='tanh', return_sequences=True),
                keras.layers.LSTM(256, activation='tanh', return_sequences=True),
                keras.layers.LSTM(256, activation='tanh'),
                keras.layers.Dense(trGen.outputFeatDim, activation='softmax')])

## Initial training
m.compile(loss='categorical_crossentropy', optimizer=s, metrics=['accuracy'])
print ('Learning rate: %f' % learning['rate'])
h = [m.fit_generator (trGen, steps_per_epoch=trGen.numSteps, 
        validation_data=cvGen, validation_steps=cvGen.numSteps,
        epochs=learning['minEpoch']-1, verbose=2)]
m.save (exp + '/dnn.nnet.h5', overwrite=True)

valErrorDiff = 1 + learning['minValError'] ## Initialise

## Continue training till validation loss stagnates
while valErrorDiff >= learning['minValError']:
    h.append (m.fit_generator (trGen, steps_per_epoch=trGen.numSteps,
            validation_data=cvGen, validation_steps=cvGen.numSteps,
            epochs=1, verbose=2))
    m.save (exp + '/dnn.nnet.h5', overwrite=True)
    valErrorDiff = h[-2].history['val_loss'][-1] - h[-1].history['val_loss'][-1]

## Scale learning rate after each epoch
while learning['lrScaleCount']:
    learning['rate'] *= learning['lrScale']
    print ('Learning rate: %f' % learning['rate'])
    learning['lrScaleCount'] -= 1
    K.set_value(m.optimizer.lr, learning['rate'])
    #m.optimizer.lr.set_value(learning['rate'])
    
    h.append (m.fit_generator (trGen, steps_per_epoch=trGen.numSteps,
            validation_data=cvGen, validation_steps=cvGen.numSteps,
            epochs=1, verbose=2))
    m.save (exp + '/dnn.nnet.h5', overwrite=True)

