#!/usr/bin/env

# Copied from A Oram - seems to originally be from https://github.com/jhykes/rebin

import numpy as np
from scipy.interpolate import UnivariateSpline, RectBivariateSpline

class BoundedUnivariateSpline(UnivariateSpline):
    """
    1D spline that returns a constant for x outside the specified domain.
    """
    def __init__(self, x, y, fill_value=0.0, **kwargs):
        self.bnds = [x[0], x[-1]]
        self.fill_value = fill_value
        UnivariateSpline.__init__(self, x, y, **kwargs)

    def is_outside_domain(self, x):
        x = np.asarray(x)
        return np.logical_or(x<self.bnds[0], x>self.bnds[1])

    def __call__(self, x):
        outside = self.is_outside_domain(x)

        return np.where(outside, self.fill_value, 
                                 UnivariateSpline.__call__(self, x))
        
    def integral(self, a, b):
        # capturing contributions outside domain of interpolation
        below_dx = np.max([0., self.bnds[0]-a])
        above_dx = np.max([0., b-self.bnds[1]])

        outside_contribution = (below_dx + above_dx) * self.fill_value

        # adjusting interval to spline domain
        a_f = np.max([a, self.bnds[0]])
        b_f = np.min([b, self.bnds[1]])

        if a_f >= b_f:
            return outside_contribution
        else:
            return (outside_contribution +
                      UnivariateSpline.integral(self, a_f, b_f) )


class BoundedRectBivariateSpline(RectBivariateSpline):
    """
    2D spline that returns a constant for x outside the specified domain.

    Input
    -----
      x : array_like, length m+1, bin edges in x direction
      y : array_like, length n+1, bin edges in y direction
      z : array_like, m by n, values of function to fit spline

    """
    def __init__(self, x, y, z, fill_value=0.0, **kwargs):
        self.xbnds = [x[0], x[-1]]
        self.ybnds = [y[0], y[-1]]
        self.fill_value = fill_value
        RectBivariateSpline.__init__(self, x, y, z, **kwargs)

    def is_outside_domain(self, x, y):
        x = np.asarray(x)
        y = np.asarray(y)
        return np.logical_or( np.logical_or(x<self.xbnds[0], x>self.xbnds[1]),
                              np.logical_or(y<self.ybnds[0], y>self.xbnds[1]) )

    def __call__(self, x, y):
        outside = self.is_outside_domain(x, y)

        return np.where(outside, self.fill_value, 
                                 RectBivariateSpline.__call__(self, x, y))
        
    def integral(self, xa, xb, ya, yb):
        assert xa <= xb
        assert ya <= yb

        total_area = (xb - xa) * (yb - ya)

        # adjusting interval to spline domain
        xa_f = np.max([xa, self.xbnds[0]])
        xb_f = np.min([xb, self.xbnds[1]])
        ya_f = np.max([ya, self.ybnds[0]])
        yb_f = np.min([yb, self.ybnds[1]])

        # Rectangle does not overlap with spline domain
        if xa_f >= xb_f or ya_f >= yb_f:
            return total_area * self.fill_value


        # Rectangle overlaps with spline domain
        else:
            spline_area = (xb_f - xa_f) * (yb_f - ya_f)
            outside_contribution = (total_area - spline_area) * self.fill_value
            return (outside_contribution +
                      RectBivariateSpline.integral(self, xa_f, xb_f, ya_f, yb_f) )



