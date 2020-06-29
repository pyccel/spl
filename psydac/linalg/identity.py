# coding: utf-8
#
from psydac.linalg.basic   import LinearOperator, Matrix, Vector, VectorSpace
from psydac.linalg.stencil import StencilMatrix

from numpy        import eye as dense_id
from scipy.sparse import eye as sparse_id

__all__ = ['IdentityLinearOperator', 'IdentityMatrix']

class IdentityLinearOperator(LinearOperator):

    def __init__(self, V):
        assert isinstance( V, VectorSpace )
        self._V  = V

    #-------------------------------------
    # Deferred methods
    #-------------------------------------
    @property
    def domain( self ):
        return self._V

    @property
    def codomain( self ):
        return self._V

    def dot( self, v, out=None ):
        assert isinstance( v, Vector )
        assert v.space is self.domain
        # find a way to handle out not None
        return v

class IdentityMatrix( Matrix, IdentityLinearOperator ):

    #-------------------------------------
    # Deferred methods
    #-------------------------------------
    def toarray( self ):
        return dense_id(*self.shape)

    def tosparse( self ):
        return sparse_id(*self.shape)

class IdentityStencilMatrix( StencilMatrix ):
    def __init__(self, V):
        assert V.ndim == 1
        super().__init__(V, V)
        n = V.npts[0]
        p = V.pads[0]
        for i in range(0, n+1):
            self._data[i+p, p] = 1.

    #-------------------------------------
    # Deferred methods
    #-------------------------------------

    def dot( self, v, out=None ):
        assert isinstance( v, Vector )
        assert v.space is self.domain
        # find a way to handle out not None
        return v

