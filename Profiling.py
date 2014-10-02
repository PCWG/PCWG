import cProfile
import ProfilingTest
import pstats

print "starting profiling"

cProfile.run('ProfilingTest.run()', 'ProfilingTest.dat')

p = pstats.Stats('ProfilingTest.dat')

p.sort_stats('cumulative').print_stats(10)
p.sort_stats('time').print_stats(10)
