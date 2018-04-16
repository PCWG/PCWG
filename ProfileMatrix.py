import cProfile
from share_test import test_matrix
import pstats
import os

print "starting profiling"

path = 'ProfilingTest.stats'

cProfile.run('test_matrix()', path)

p = pstats.Stats(path)

p.sort_stats('cumulative').print_stats(10)
p.sort_stats('time').print_stats(10)

os.system("gprof2dot -f pstats {0} | dot -Tsvg -o callgraph.svg".format(path))
os.system("rsvg-convert -h 2000 callgraph.svg > callgraph.png".format(path))
