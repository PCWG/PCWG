import cProfile
import ProfilingTest
import pstats

print "starting profiling"

cProfile.run('ProfilingTest.run()', 'Profile/ProfilingTest.dat')

p = pstats.Stats('Profile/ProfilingTest.dat')

p.sort_stats('cumulative').print_stats(10)
p.sort_stats('time').print_stats(10)
