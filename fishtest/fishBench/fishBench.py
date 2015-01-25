import sys
import re
import os
import os.path
import threading
import math
import subprocess

'''Python script to bench two stockfish against each other.
Called by python fishBench <SF1> <SF2> <samples>
Example: python fishBench stockfish stockfish 3.
It starts two threads running <samples> benches of <SF1> and <SF2>, collect the results, make some stats and display it nicely on
the screen.
<SF1> and <SF2> are supposed to be stockfish executables in the same directory as fishBench.py.
Test on Ubuntu/Linux, no clue whether it works on Windows.
'''

def benchEngine(name, samples):
    command  = ['./'+name, 'bench']
    fileCounter = 0
    filename = 'bench'+name+str(fileCounter)+'.log'
    while os.path.exists(filename):
        fileCounter += 1
        filename = 'bench'+name+str(fileCounter)+'.log'
    benchLog = open(filename,'w')
    for n in range(samples):
        subprocess.call(command, stderr=benchLog, stdout=benchLog)
    benchLog.close()
    with open(filename) as f:
        content = f.readlines()
    benchLog = []
    for line in content:
        mo = re.search('Nodes/second' , line, flags=0)
        if mo != None:
            numString = re.sub('[^0-9]','' , mo.string)
            benchLog.append(int(numString))
    os.remove(filename)
    return benchLog


class benchStats():
    def __init__(self, name, results):
        self.name = name
        self.results = results
        self.make_stats()
        
    def make_stats(self):
        self.median = quantile(self.results, 0.5)
        self.high_limit = quantile(self.results, 0.95)
        self.low_limit = quantile(self.results,0.95)
        self.std = (quantile(self.results, 0.84) - quantile(self.results, 0.16))/2.0



class benchThread (threading.Thread):
    def __init__(self, threadID, name, samples):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.samples = samples
        self.results = []
        
        
    def run(self):
        self.results = benchEngine(self.name, self.samples)


def quantile(values, quantile):
    tmpvalues = values
    tmpvalues.sort()
    quantile *= len(values)-1
    p = math.fmod(quantile, 1)
    return (1-p)*tmpvalues[int(quantile)] + (p)*tmpvalues[int(quantile)+1]

def std(values):
    return  0.5*quantile(values,0.84) - 0.5*quantile(values,0.16)
 

threaded_flag = True

# How many samples?
samples = int(sys.argv[-1])
sys.argv.pop()

# Engines commands? 
names = sys.argv[1:]

benchLogs  = []
if threaded_flag:
    threads = []
    for n,name in enumerate(names):
    # Create new threads
        threads.append(benchThread(n+1, name, samples))
    for thread in threads:
    # Start new Threads
        thread.start()
    for thread in threads:
    # Wait threads to finish
        thread.join()
    for thread in threads:
        benchLogs.append(benchStats(thread.name , thread.results))

print ''
print 'Engine',             ' '*(30-len('Engine')),           '| Nodes/second'

for n in range(len(benchLogs)):
    print benchLogs[n].name,    ' '*(30-len(benchLogs[n].name)),  '|' , benchLogs[n].median, '+-', benchLogs[n].std

if len(benchLogs) == 2:
    print ''
    deltas = [benchLogs[0].results[n] - benchLogs[1].results[n] for n in range(samples)]
    deltasMed  = round(quantile(deltas,0.5))
    deltasStd  = round(std(deltas))
    print 'Differences',           ' '*(30-len('Differences')),      '|' , deltasMed, '+-', deltasStd
    if deltasMed == 0:
        meanVariance = float('Inf')
        relativeStd  = float('Inf')
    else:
        meanVariance = deltasStd/math.sqrt(samples)
        relativeStd  = round(100*meanVariance/deltasMed,2)
    print 'Variance of the mean',  ' '*(30-len('Variance of the mean')), '|'  , round(meanVariance,2), '(', relativeStd , '%)'
    print 'Speed up',              ' '*(30-len('Speed up'))            , '|'  , round((deltasMed/benchLogs[1].median)*100,2), '%'
    print ''
