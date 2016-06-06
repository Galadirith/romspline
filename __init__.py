"""romSpline
   =========

romSpline is an easy-to-use code for generating a reduced-order spline 
interpolant of 1d data.

romSpline uses a greedy algorithm on 1d data to find a nearly minimal subset of 
samples for recovering the original data, to the requested tolerance, with 
a univariate spline interpolant. This code should be useful for downsampling 
or compressing large data arrays to their essential components needed for 
reconstructing the original information. The degree of downsampling is 
often significant (e.g., orders of magnitude) for relatively smooth data.

Future versions of romSpline will include support for multi-dimensional data 
and for quantifying the uncertainty of the output spline interpolant on
data not used for training the underlying greedy algorithm.

See the accompanying IPython notebook (romSpline_example.ipynb) for a 
tutorial on using the code.

If you find this code useful for your publication work then please
cite the code repository (www.bitbucket.org/chadgalley/romSpline)
and the corresponding paper that discusses and characterizes the
reduced-order spline method (to be available soon).

"""

__copyright__ = "Copyright (C) 2015 Chad Galley"
__author__ = "Chad Galley"
__email__ = "crgalley@tapir.caltech.edu, crgalley@gmail.com"
__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

from greedySpline import *
from uncQuant import *


################################
#   Class for generating some  #
#   test data for showing how  #
#    to use the code in the    #
# associated IPython notebooks #
################################

class _TestData(object):
  """
  Generate the test data used as in example IPython notebooks 
  for demonstrating the construction, properties, and errors 
  of a reduced-order spline interpolant.  
  """
  
  def __init__(self, samples=4001, noise=None, uv=None):
    # Generate test data
    self.x = np.linspace(-1, 1, samples)
    self.y = self.f(self.x, noise=noise, uv=uv)
  
  def f(self, x, noise=None, uv=None):
    """Function to sample for reduced-order spline example"""
    
    # Validate inputs
    assert None in [noise, uv], "One or both of `noise` and `uv` must be None."
    x = np.asarray(x)
    
    # Return smooth function values
    smooth = 100.*( (x+1.)*np.sin(5.*(x-0.2)**2) + np.exp(-(x-0.5)**2/2./0.01)*np.sin(100*x) )
    if noise is None and uv is None:
      ans = smooth
    
    # Return smooth function values with high-frequency (UV) features
    elif uv is not None:
      assert type(uv) in [float, int], "Expecting integer or float type."
      ans = smooth + uv*self.uv(x)
    
    # Return smooth function values with stochastic noise
    elif noise is not None:
      assert type(noise) in [float, int], "Expecting integer or float type."
      ans = smooth + noise*np.random.randn(len(x))
    
    return ans
  
  def dfdx(self, x):
      """Analytic derivative of f"""
      x = np.asarray(x)
      
      a = 10.*(-0.2+x)*(1.+x)*np.cos(5.*(-0.2 + x)**2)
      b = 100.*np.exp(-50.*(-0.5+x)**2)*np.cos(100.*x)
      c = np.sin(5.*(-0.2+x)**2)
      d = -100.*np.exp(-50.*(-0.5+x)**2)*(-0.5+x)*np.sin(100.*x)
      
      return 100.*(a+b+c+d)
  
  def uv(self, x, width=20):
      X = x[width] - x[0]
      return np.sin(len(x)/X * x)



###################################
# Functions for finite difference #
#        differentiation          #
###################################

def _get_arg(a, x):
  """Get index of array a that has the closest value to x"""
  return abs(a-x).argmin()

def _make_patch(x, x_grid, dim):
  """Make patch with dim elements centered around x"""
  
  # Find grid points closest to x
  ix = _get_arg(x_grid, x)
  
  # Find how many elements to take on either side of x
  if dim % 2:    # Check if dim is odd...
    a = int((dim+1)/2.)
    b = a
  else:          #...or even
    a = int(dim/2.)
    b = a+1
  
  # Ensure patch doesn't cross the training grid boundary
  ix = _check_patch(ix, a, b, x_grid.size)
  
  # Indices of the patch 
  ipatch = np.arange(ix-a, ix+b)
  return ipatch, ix, _get_arg(ipatch, ix)

def _check_patch(i, dileft, diright, dim):
  """Check if i is too close to interval endpoints and adjust if so."""
  if i <= dileft: 
    ans = dileft
  elif dim-i <= diright: 
    ans = dim-diright
  else:
    ans = i
  return ans

def D(y, x, dx=1, order=4):
  """Deriviative(s) of y with respect to x using finite differencing"""
  # Look up finite differencing weights
  h = x[1]-x[0]
  weights = _FD_weights(dx, order, order/2., h)
  
  # Compute finite difference derivatives
  ans = np.zeros(y.size, dtype=y.dtype)
  for ii, xx in enumerate(x):
    ix_patch, _, ix = _make_patch(xx, x, order)
    if float(ix) != order/2.:
      weights = _FD_weights(dx, order, ix, h)
    ans[ii] = np.dot(y[ix_patch], weights)
  
  return ans

def _FD_weights(nd, order, s, h):
  nd, order, s = int(nd), int(order), int(s)
  params = str((nd,order,s))
  return np.array(_weights[params])/h**nd

_weights = {}

# Weights are computed from the Fornberg formula
# as coefficients in the seres expansion in 
# powers of (1-x) up to x^nd of the function:
#
#    x^s * log(x)^order / h^order
#
# Here, nd is the number of derivatives requested.
# The coefficients can be generated in Mathematica
# using:
#
# CoefficientList[Normal[Series[
#     x^nd Log[x]^order,{x,1,nd}]/h^order],x]


# ----------------------#
# First derivatives     #
# ----------------------#

# First derivative, first order
_weights['(1, 1, 0)'] = [-1., 1.]
_weights['(1, 1, 1)'] = [-1., 1.]

# First derivative, second order
_weights['(1, 2, 0)'] = [-3./2., 2., -1./2.]
_weights['(1, 2, 1)'] = [-1./2., 0., 1./2.]
_weights['(1, 2, 2)'] = [1./2., -2., 3./2.]

# First derivative, third order
_weights['(1, 3, 0)'] = [-11./6., 3., -3./2., 1./3.]
_weights['(1, 3, 1)'] = [-1./3., -1./2., 1., -1./6.]
_weights['(1, 3, 2)'] = [1./6., -1., 1./2., 1./3.]
_weights['(1, 3, 3)'] = [-1./3., 3./2., -3., 11./6.]

# First derivative, fourth order
_weights['(1, 4, 0)'] = [-25./12., 4., -3., 4./3., -1./4.]
_weights['(1, 4, 1)'] = [-1./4., -5./6., 3./2., -1./2., 1./12.]
_weights['(1, 4, 2)'] = [1./12., -2./3., 0., 2./3., -1./12.]
_weights['(1, 4, 3)'] = [-1./12., 1./2., -3./2., 5./6., 1./4.]
_weights['(1, 4, 4)'] = [1./4., -4./3., 3., -4., 25./12.]

# First derivative, fifth order
_weights['(1, 5, 0)'] = [-137./60., 5., -5., 10./3., -5./4., 1./5.]
_weights['(1, 5, 1)'] = [-1./5., -13./12., 2., -1., 1./3., -1./20.]
_weights['(1, 5, 2)'] = [1./20., -1./2., -1./3., 1., -1./4., 1./30.]
_weights['(1, 5, 3)'] = [-1./30., 1./4., -1., 1./3., 1./2., -1./20.]
_weights['(1, 5, 4)'] = [1./20., -1./3., 1., -2., 13./12., 1./5.]
_weights['(1, 5, 5)'] = [-1./5., 5./4., -10./3., 5., -5., 137./60.]

# First derivative, sixth order
_weights['(1, 6, 0)'] = [-49./20., 6., -15./2., 20./3., -15./4., 6./5., -1./6.]
_weights['(1, 6, 1)'] = [-1./6., -77./60., 5./2., -5./3., 5./6., -1./4., 1./30.]
_weights['(1, 6, 2)'] = [1./30., -2./5., -7./12., 4./3., -1./2., 2./15., -1./60.]
_weights['(1, 6, 3)'] = [-1./60., 3./20., -3./4., 0., 3./4., -3./20., 1./60.]
_weights['(1, 6, 4)'] = [1./60., -2./15., 1./2., -4./3., 7./12., 2./5., -1./30.]
_weights['(1, 6, 5)'] = [-1./30., 1./4., -5./6., 5./3., -5./2., 77./60., 1./6.]
_weights['(1, 6, 6)'] = [1./6., -6./5., 15./4., -20./3., 15./2., -6., 49./20.]

# First derivative, seventh order
_weights['(1, 7, 0)'] = [-363./140., 7., -21./2., 35./3., -35./4., 21./5., -7./6., 1./7.]
_weights['(1, 7, 1)'] = [-1./7., -29./20., 3., -5./2., 5./3., -3./4., 1./5., -1./42.]
_weights['(1, 7, 2)'] = [1./42., -1./3., -47./60., 5./3., -5./6., 1./3., -1./12., 1./105.]
_weights['(1, 7, 3)'] = [-1./105., 1./10., -3./5., -1./4., 1., -3./10., 1./15., -1./140.]
_weights['(1, 7, 4)'] = [1./140., -1./15., 3./10., -1., 1./4., 3./5., -1./10., 1./105.]
_weights['(1, 7, 5)'] = [-1./105., 1./12., -1./3., 5./6., -5./3., 47./60., 1./3., -1./42.]
_weights['(1, 7, 6)'] = [1./42., -1./5., 3./4., -5./3., 5./2., -3., 29./20., 1./7.]
_weights['(1, 7, 7)'] = [-1./7., 7./6., -21./5., 35./4., -35./3., 21./2., -7., 363./140.]

# First derivative, eight order
_weights['(1, 8, 0)'] = [-761./280., 8., -14., 56./3., -35./2., 56./5., -14./3., 8./7., -1./8.]
_weights['(1, 8, 1)'] = [-1./8., -223./140., 7./2., -7./2., 35./12., -7./4., 7./10., -1./6., 1./56.]
_weights['(1, 8, 2)'] = [1./56., -2./7., -19./20., 2., -5./4., 2./3., -1./4., 2./35., -1./168.]
_weights['(1, 8, 3)'] = [-1./168., 1./14., -1./2., -9./20., 5./4., -1./2., 1./6., -1./28., 1./280.]
_weights['(1, 8, 4)'] = [1./280., -4./105., 1./5., -4./5., 0., 4./5., -1./5., 4./105., -1./280.]
_weights['(1, 8, 5)'] = [-1./280., 1./28., -1./6., 1./2., -5./4., 9./20., 1./2., -1./14., 1./168.]
_weights['(1, 8, 6)'] = [1./168., -2./35., 1./4., -2./3., 5./4., -2., 19./20., 2./7., -1./56.]
_weights['(1, 8, 7)'] = [-1./56., 1./6., -7./10., 7./4., -35./12., 7./2., -7./2., 223./140., 1./8.]
_weights['(1, 8, 8)'] = [1./8., -8./7., 14./3., -56./5., 35./2., -56./3., 14., -8., 761./280.]


# -----------------------#
# Second derivatives     #
# -----------------------#

# Second derivative, second order
_weights['(2, 2, 0)'] = [1., -2., 1.]
_weights['(2, 2, 1)'] = [1., -2., 1.]
_weights['(2, 2, 2)'] = [1., -2., 1.]

# Second derivative, third order
_weights['(2, 3, 0)'] = [2., -5., 4., -1.]
_weights['(2, 3, 1)'] = [1., -2., 1., 0.]
_weights['(2, 3, 2)'] = [0., 1., -2., 1.]
_weights['(2, 3, 3)'] = [-1., 4., -5., 2.]

# Second derivative, fourth order
_weights['(2, 4, 0)'] = [35./12., -26./3., 19./2., -14./3., 11./12.]
_weights['(2, 4, 1)'] = [11./12., -5./3., 1./2., 1./3., -1./12.]
_weights['(2, 4, 2)'] = [-1./12., 4./3., -5./2., 4./3., -1./12]
_weights['(2, 4, 3)'] = [-1./12., 1./3., 1./2., -5./3., 11./12.]
_weights['(2, 4, 4)'] = [11./12, -14./3., 19./2., -26./3., 35./12]

# Second derivative, fifth order
_weights['(2, 5, 0)'] = [15./4., -77./6., 107./6., -13., 61./12., -5./6.]
_weights['(2, 5, 1)'] = [5./6., -5./4., -1./3., 7./6., -1./2., 1./12.]
_weights['(2, 5, 2)'] = [-1./12., 4./3., -5./2., 4./3., -1./12., 0.]
_weights['(2, 5, 3)'] = [0., -1./12., 4./3., -5./2., 4./3., -1./12.]
_weights['(2, 5, 4)'] = [1./12., -1./2., 7./6., -1./3., -5./4., 5./6.]
_weights['(2, 5, 5)'] = [-5./6., 61./12., -13., 107./6., -77./6., 15./4.]

# Second derivative, sixth order
_weights['(2, 6, 0)'] = [203./45., -87./5., 117./4., -254./9., 33./2., -27./5., 137./180.]
_weights['(2, 6, 1)'] = [137./180., -49./60., -17./12., 47./18., -19./12., 31./60., -13./180.]
_weights['(2, 6, 2)'] = [-13./180., 19./15., -7./3., 10./9., 1./12., -1./15., 1./90.]
_weights['(2, 6, 3)'] = [1./90., -3./20., 3./2., -49./18., 3./2., -3./20., 1./90.]
_weights['(2, 6, 4)'] = [1./90., -1./15., 1./12., 10./9., -7./3., 19./15., -13./180.]
_weights['(2, 6, 5)'] = [-13./180., 31./60., -19./12., 47./18., -17./12., -49./60., 137./180.]
_weights['(2, 6, 6)'] = [137./180., -27./5., 33./2., -254./9., 117./4., -87./5., 203./45.]

# Second derivative, seventh order
_weights['(2, 7, 0)'] = [469./90., -223./10., 879./20., -949./18., 41., -201./10., 1019./180., -7./10.]
_weights['(2, 7, 1)'] = [7./10., -7./18., -27./10., 19./4., -67./18., 9./5., -1./2., 11./180.]
_weights['(2, 7, 2)'] = [-11./180., 107./90., -21./10., 13./18., 17./36., -3./10., 4./45., -1./90.]
_weights['(2, 7, 3)'] = [1./90., -3./20., 3./2., -49./18., 3./2., -3./20., 1./90., 0.]
_weights['(2, 7, 4)'] = [0., 1./90., -3./20., 3./2., -49./18., 3./2., -3./20., 1./90.]
_weights['(2, 7, 5)'] = [-1./90., 4./45., -3./10., 17./36., 13./18., -21./10., 107./90., -11./180.]
_weights['(2, 7, 6)'] = [11./180., -1./2., 9./5., -67./18., 19./4., -27./10., -7./18., 7./10.]
_weights['(2, 7, 7)'] = [-7./10., 1019./180., -201./10., 41., -949./18., 879./20., -223./10., 469./90.]

# Second derivative, eighth order
_weights['(2, 8, 0)'] = [29531./5040., -962./35., 621./10., -4006./45., 691./8., -282./5., 2143./90., -206./35., 363./560.]
_weights['(2, 8, 1)'] = [363./560., 8./315., -83./20., 153./20., -529./72., 47./10., -39./20., 599./1260., -29./560.]
_weights['(2, 8, 2)'] = [-29./560., 39./35., -331./180., 1./5., 9./8., -37./45., 7./20., -3./35., 47./5040.]
_weights['(2, 8, 3)'] = [47./5040., -19./140., 29./20., -118./45., 11./8., -1./20., -7./180., 1./70., -1./560.]
_weights['(2, 8, 4)'] = [-1./560., 8./315., -1./5., 8./5., -205./72., 8./5., -1./5., 8./315., -1./560.]
_weights['(2, 8, 5)'] = [-1./560., 1./70., -7./180., -1./20., 11./8., -118./45., 29./20., -19./140., 47./5040.]
_weights['(2, 8, 6)'] = [47./5040., -3./35., 7./20., -37./45., 9./8., 1./5., -331./180., 39./35., -29./560.]
_weights['(2, 8, 7)'] = [-29./560., 599./1260., -39./20., 47./10., -529./72., 153./20., -83./20., 8./315., 363./560.]
_weights['(2, 8, 8)'] = [363./560., -206./35., 2143./90., -282./5., 691./8., -4006./45., 621./10., -962./35., 29531./5040.]


# ----------------------#
# Third derivatives     #
# ----------------------#

# Third derivative, third order
_weights['(3, 3, 0)'] = [-1., 3., -3., 1.]
_weights['(3, 3, 1)'] = [-1., 3., -3., 1.]
_weights['(3, 3, 2)'] = [-1., 3., -3., 1.]
_weights['(3, 3, 3)'] = [-1., 3., -3., 1.]

# Third derivative, fourth order
_weights['(3, 4, 0)'] = [-5./2., 9., -12., 7., -3./2.]
_weights['(3, 4, 1)'] = [-3./2., 5., -6., 3., -1./2.]
_weights['(3, 4, 2)'] = [-1./2., 1., 0., -1., 1./2.]
_weights['(3, 4, 3)'] = [1./2., -3., 6., -5., 3./2.]
_weights['(3, 4, 4)'] = [3./2., -7., 12., -9., 5./2.]

# Third derivative, fifth order
_weights['(3, 5, 0)'] = [-17./4., 71./4., -59./2., 49./2., -41./4., 7./4.]
_weights['(3, 5, 1)'] = [-7./4., 25./4., -17./2., 11./2., -7./4., 1./4.]
_weights['(3, 5, 2)'] = [-1./4., -1./4., 5./2., -7./2., 7./4., -1./4.]
_weights['(3, 5, 3)'] = [1./4., -7./4., 7./2., -5./2., 1./4., 1./4.]
_weights['(3, 5, 4)'] = [-1./4., 7./4., -11./2., 17./2., -25./4., 7./4.]
_weights['(3, 5, 5)'] = [-7./4., 41./4., -49./2., 59./2., -71./4., 17./4.]

# Third derivative, sixth order
_weights['(3, 6, 0)'] = [-49./8., 29., -461./8., 62., -307./8., 13., -15./8.]
_weights['(3, 6, 1)'] = [-15./8., 7., -83./8., 8., -29./8., 1., -1./8.]
_weights['(3, 6, 2)'] = [-1./8., -1., 35./8., -6., 29./8., -1., 1./8.]
_weights['(3, 6, 3)'] = [1./8., -1., 13./8., 0., -13./8., 1., -1./8.]
_weights['(3, 6, 4)'] = [-1./8., 1., -29./8., 6., -35./8., 1., 1./8.]
_weights['(3, 6, 5)'] = [1./8., -1., 29./8., -8., 83./8., -7., 15./8.]
_weights['(3, 6, 6)'] = [15./8., -13., 307./8., -62., 461./8., -29., 49./8.]

# Third derivative, seventh order
_weights['(3, 7, 0)'] = [-967./120., 638./15., -3929./40., 389./3., -2545./24., 268./5., -1849./120., 29./15.]
_weights['(3, 7, 1)'] = [-29./15., 889./120., -58./5., 241./24., -17./3., 89./40., -8./15., 7./120.]
_weights['(3, 7, 2)'] = [-7./120., -22./15., 231./40., -25./3., 143./24., -12./5., 71./120., -1./15.]
_weights['(3, 7, 3)'] = [1./15., -71./120., 2./5., 49./24., -11./3., 89./40., -8./15., 7./120.]
_weights['(3, 7, 4)'] = [-7./120., 8./15., -89./40., 11./3., -49./24., -2./5., 71./120., -1/15.]
_weights['(3, 7, 5)'] = [1./15., -71./120., 12./5., -143./24., 25./3., -231./40., 22./15., 7./120.]
_weights['(3, 7, 6)'] = [-7./120., 8./15., -89./40., 17./3., -241./24., 58./5., -889./120., 29./15.]
_weights['(3, 7, 7)'] = [-29./15., 1849./120., -268./5., 2545./24., -389./3., 3929./40., -638./15., 967./120.]

# Third derivative, eighth order
_weights['(3, 8, 0)'] = [-801./80., 349./6., -18353./120., 2391./10., -1457./6., 4891./30., -561./8., 527./30., -469./240.]
_weights['(3, 8, 1)'] = [-469./240., 303./40., -731./60., 269./24., -57./8., 407./120., -67./60., 9./40., -1./48.]
_weights['(3, 8, 2)'] = [-1./48., -53./30., 273./40., -313./30., 103./12., -9./2., 197./120., -11./30., 3./80.]
_weights['(3, 8, 3)'] = [3./80., -43./120., -5./12., 147./40., -137./24., 463./120., -27./20., 7./24., -7./240.]
_weights['(3, 8, 4)'] = [-7./240., 3./10., -169./120., 61./30., 0., -61./30., 169./120., -3./10., 7./240.]
_weights['(3, 8, 5)'] = [7./240., -7./24., 27./20., -463./120., 137./24., -147./40., 5./12., 43./120., -3./80.]
_weights['(3, 8, 6)'] = [-3./80., 11./30., -197./120., 9./2., -103./12., 313./30., -273./40., 53./30., 1./48.]
_weights['(3, 8, 7)'] = [1./48., -9./40., 67./60., -407./120., 57./8., -269./24., 731./60., -303./40., 469./240.]
_weights['(3, 8, 8)'] = [469./240., -527./30., 561./8., -4891./30., 1457./6., -2391./10., 18353./120., -349./6., 801./80.]


# -----------------------#
# Fourth derivatives     #
# -----------------------#

# Fourth derivative, fourth order
_weights['(4, 4, 0)'] = [1., -4., 6., -4., 1.]
_weights['(4, 4, 1)'] = [1., -4., 6., -4., 1.]
_weights['(4, 4, 2)'] = [1., -4., 6., -4., 1.]
_weights['(4, 4, 3)'] = [1., -4., 6., -4., 1.]
_weights['(4, 4, 4)'] = [1., -4., 6., -4., 1.]

# Fourth derivative, fifth order
_weights['(4, 5, 0)'] = [3., -14., 26., -24., 11., -2.]
_weights['(4, 5, 1)'] = [2., -9., 16., -14., 6., -1.]
_weights['(4, 5, 2)'] = [1., -4., 6., -4., 1., 0.]
_weights['(4, 5, 3)'] = [0., 1., -4., 6., -4., 1.]
_weights['(4, 5, 4)'] = [-1., 6., -14., 16., -9., 2.]
_weights['(4, 5, 5)'] = [-2., 11., -24., 26., -14., 3.]

# Fourth derivative, sixth order
_weights['(4, 6, 0)'] = [35./6., -31., 137./2., -242./3., 107./2., -19., 17./6.]
_weights['(4, 6, 1)'] = [17./6., -14., 57./2., -92./3., 37./2., -6., 5./6.]
_weights['(4, 6, 2)'] = [5./6., -3., 7./2., -2./3., -3./2., 1., -1./6.]
_weights['(4, 6, 3)'] = [-1./6., 2., -13./2., 28./3., -13./2., 2., -1./6.]
_weights['(4, 6, 4)'] = [-1./6., 1., -3./2., -2./3., 7./2., -3., 5./6.]
_weights['(4, 6, 5)'] = [5./6., -6., 37./2., -92./3., 57./2., -14., 17./6.]
_weights['(4, 6, 6)'] = [17./6., -19., 107./2., -242./3., 137./2., -31., 35./6.]

# Fourth derivative, seventh order
_weights['(4, 7, 0)'] = [28./3., -111./2., 142., -1219./6., 176., -185./2., 82./3., -7./2.]
_weights['(4, 7, 1)'] = [7./2., -56./3., 85./2., -54., 251./6., -20., 11./2., -2./3.]
_weights['(4, 7, 2)'] = [2./3., -11./6., 0., 31./6., -22./3., 9./2., -4./3., 1./6.]
_weights['(4, 7, 3)'] = [-1./6., 2., -13./2., 28./3., -13./2., 2., -1./6., 0.]
_weights['(4, 7, 4)'] = [0., -1./6., 2., -13./2., 28./3., -13./2., 2., -1./6.]
_weights['(4, 7, 5)'] = [1./6., -4./3., 9./2., -22./3., 31./6., 0., -11./6., 2./3.]
_weights['(4, 7, 6)'] = [-2./3., 11./2., -20., 251./6., -54., 85./2., -56./3., 7./2.]
_weights['(4, 7, 7)'] = [-7./2., 82./3., -185./2., 176., -1219./6., 142., -111./2., 28./3.]

# Fourth derivative, eighth order
_weights['(4, 8, 0)'] = [1069./80., -1316./15., 15289./60., -2144./5., 10993./24., -4772./15., 2803./20., -536./15., 967./240.]
_weights['(4, 8, 1)'] = [967./240., -229./10., 3439./60., -2509./30., 631./8., -1489./30., 1219./60., -49./10., 127./240.]
_weights['(4, 8, 2)'] = [127./240., -11./15., -77./20., 193./15., -407./24., 61./5., -311./60., 19./15., -11./80.]
_weights['(4, 8, 3)'] = [-11./80., 53./30., -341./60., 77./10., -107./24., 11./30., 13./20., -7./30., 7./240.]
_weights['(4, 8, 4)'] = [7./240., -2./5., 169./60., -122./15., 91./8., -122./15., 169./60., -2./5., 7./240.]
_weights['(4, 8, 5)'] = [7./240., -7./30., 13./20., 11./30., -107./24., 77./10., -341./60., 53./30., -11./80.]
_weights['(4, 8, 6)'] = [-11./80., 19./15., -311./60., 61./5., -407./24., 193./15., -77./20., -11./15., 127./240.]
_weights['(4, 8, 7)'] = [127./240., -49./10., 1219./60., -1489./30., 631./8., -2509./30., 3439./60., -229./10., 967./240.]
_weights['(4, 8, 8)'] = [967./240., -536./15., 2803./20., -4772./15., 10993./24., -2144./5., 15289./60., -1316./15., 1069./80.]