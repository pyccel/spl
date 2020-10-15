# -*- coding: UTF-8 -*-

import numpy as np

from psydac.linalg.stencil  import StencilMatrix, StencilVectorSpace
from psydac.linalg.kron     import KroneckerStencilMatrix
from psydac.linalg.block    import ProductSpace, BlockVector, BlockLinearOperator, BlockMatrix
from psydac.fem.vector      import ProductFemSpace
from psydac.fem.tensor      import TensorFemSpace
from psydac.linalg.identity import IdentityLinearOperator, IdentityStencilMatrix as IdentityMatrix
from psydac.fem.basic       import FemField
from psydac.fem.vector      import VectorFemField

#====================================================================================================
def d_matrix(n, p, periodic):
    """
    Create a 1D incidence matrix of shape (n, n) in the periodic case, and (n, n-1) otherwise.
    The incidence matrix has values -1 on the main diagonal, and +1 on the diagonal above it.

    Parameters
    ----------
    n : int
        Number of degrees of freedom.

    p : int
        Padding size.

    periodic : bool
        True if matrix is periodic, False otherwise.

    Results
    -------
    M : psydac.linalg.stencil.StencilMatrix
        1D incidence matrix of shape (n, n) in the periodic case, and (n, n-1) otherwise.

    """
    m = n if periodic else n - 1

    V1 = StencilVectorSpace([n], [p], [periodic])
    V2 = StencilVectorSpace([m], [p], [periodic])
    M  = StencilMatrix(V1, V2)

    for i in range(m):
        M._data[p+i, p]   = -1.
        M._data[p+i, p+1] =  1.

    return M

#====================================================================================================
class DiffOperator:

    @property
    def matrix(self):
        return self._matrix

    @property
    def domain(self):
        return self._domain

    @property
    def codomain(self):
        return self._codomain

#====================================================================================================
class Grad(DiffOperator):
    """
    Gradient operator in 1D, 2D or 3D.

    Parameters
    ----------
    V0_h : TensorFemSpace
        Domain of gradient operator.

    V1_h : TensorFemSpace | ProductFemSpace
        Codomain of gradient operator; it is a scalar space in 1D, otherwise a vector space.

    """
    def __init__(self, V0_h, V1_h):

        assert isinstance(V0_h, TensorFemSpace)
        dim = V0_h.ldim
        if dim == 1:
            assert isinstance(V1_h, TensorFemSpace)
        else:
            assert isinstance(V1_h, ProductFemSpace)

        self._domain   = V0_h
        self._codomain = V1_h

        self.dim = dim
        d_matrices = [d_matrix(V.nbasis, V.degree, V.periodic) for V in V0_h.spaces]
        identities = [IdentityMatrix(V.vector_space)           for V in V0_h.spaces]

        mats = []
        for i in range(dim):
            args = []
            for j in range(dim):
                if i==j:
                    args.append(d_matrices[j])
                else:
                    args.append(identities[j])

            if dim == 1:
                mats += args
            else:
                mats += [KroneckerStencilMatrix(V0_h.vector_space, V1_h.vector_space.spaces[i], *args)]

        VS0 = ProductSpace(V0_h.vector_space)

        if dim == 1:
            VS1 = ProductSpace(V1_h.vector_space)
        else:
            VS1 = V1_h.vector_space

        self._matrix = BlockMatrix( VS0, VS1, blocks=[[mat] for mat in mats] )

    def __call__(self, x):

        assert isinstance(x, FemField)
        assert x.space == self._domain

        y = BlockVector(ProductSpace(x.coeffs.space), blocks=[x.coeffs])

        coeffs = self._matrix.dot(y)
        coeffs.update_ghost_regions()

        if self.dim == 1:
            out = FemField(self._codomain, coeffs=coeffs[0])
        else:
            out = VectorFemField(self._codomain, coeffs=coeffs)

        return out

#====================================================================================================
class Curl(DiffOperator):
    """
    Curl operator in 2D or 3D.

    Parameters
    ----------
    V1_h : ProductFemSpace
        Domain of curl operator.

    V2_h : ProductFemSpace
        Codomain of curl operator.

    """
    def __init__(self, V1_h, V2_h):

        assert isinstance(V1_h, ProductFemSpace)
        assert isinstance(V2_h, ProductFemSpace)

        self._domain   = V1_h
        self._codomain = V2_h
 
        D_basis = [V.spaces[i] for i,V in enumerate(V1_h.spaces)]
        dim     = len(D_basis)

        if dim == 2:
            N_basis = [V1_h.spaces[1].spaces[0], V1_h.spaces[0].spaces[1]]
        elif dim == 3:
            N_basis = [V1_h.spaces[1].spaces[0], V1_h.spaces[0].spaces[1], V1_h.spaces[0].spaces[2]]

        d_matrices   = [d_matrix(V.nbasis, V.degree, V.periodic)   for V in N_basis]
        identities_0 = [IdentityMatrix(V.vector_space) for V in N_basis]
        identities_1 = [IdentityMatrix(V.vector_space, p=V.vector_space.pads[0]+1) for V in D_basis]
        
        mats = []    
            
        if dim == 3:
            mats = [[None,None,None],
                    [None,None,None],
                    [None,None,None]]
                    
            args       = [-identities_0[0], identities_1[1], d_matrices[2]]
            mats[0][1] = KroneckerStencilMatrix(V1_h.vector_space.spaces[1], V2_h.vector_space.spaces[0], *args)

            args       = [identities_0[0], d_matrices[1], identities_1[2]]
            mats[0][2] = KroneckerStencilMatrix(V1_h.vector_space.spaces[2], V2_h.vector_space.spaces[0], *args)
            # ...
            
            # ...
            args       = [identities_1[0], identities_0[1], d_matrices[2]]
            mats[1][0] = KroneckerStencilMatrix(V1_h.vector_space.spaces[0], V2_h.vector_space.spaces[1], *args)
            
            args       = [-d_matrices[0], identities_0[1], identities_1[2]]
            mats[1][2] = KroneckerStencilMatrix(V1_h.vector_space.spaces[2], V2_h.vector_space.spaces[1], *args)
            # ...
            
            # ...
            args       = [-identities_1[0], d_matrices[1], identities_0[2]]
            mats[2][0] = KroneckerStencilMatrix(V1_h.vector_space.spaces[0], V2_h.vector_space.spaces[2], *args)
            
            args       = [d_matrices[0], identities_1[1], identities_0[2]]
            mats[2][1] = KroneckerStencilMatrix(V1_h.vector_space.spaces[1], V2_h.vector_space.spaces[2], *args)

            self._matrix = BlockMatrix( V1_h.vector_space, V2_h.vector_space, blocks=mats )

        elif dim == 2:
            mats = [[None , None]]
        
            args = [-identities_1[0], d_matrices[1]]
            mats[0][0] = KroneckerStencilMatrix(V1_h.vector_space.spaces[0], V2_h.vector_space, *args)

            args = [d_matrices[0], identities_1[1]]
            mats[0][1] = KroneckerStencilMatrix(V1_h.vector_space.spaces[1], V2_h.vector_space, *args)

            self._matrix = BlockMatrix( V1_h.vector_space, ProductSpace( V2_h.vector_space ), blocks=mats )
        
        else:
            raise NotImplementedError('TODO')

    def __call__(self, x):
        assert isinstance(x, VectorFemField)
        assert x.space == self._domain
        
        coeffs = self._matrix.dot(x.coeffs)
        coeffs.update_ghost_regions()

        return VectorFemField(self._codomain, coeffs=coeffs)

#====================================================================================================
class Div(DiffOperator):
    """
    Divergence operator in 1D, 2D or 3D.

    Parameters
    ----------
    V2_h : ProductFemSpace
        Domain of divergence operator.

    V3_h : TensorFemSpace
        Codomain of divergence operator.

    """
    def __init__(self, V2_h, V3_h):

        assert isinstance(V2_h, ProductFemSpace)
        assert isinstance(V3_h, TensorFemSpace)

        self._domain   = V2_h
        self._codomain = V3_h

        dim        = V2_h.ldim
        N_basis    = [V.spaces[i] for i,V in enumerate(V2_h.spaces)]

        d_matrices = [d_matrix(V.nbasis, V.degree, V.periodic)   for V in N_basis]
        identities = [IdentityMatrix(V.vector_space, p=V.vector_space.pads[0]+1) for V in V3_h.spaces]
            
        mats = []
        for i in range(dim):
            args = []
            for j in range(dim):
                if i==j:
                    args.append(d_matrices[j])
                else:
                    args.append(identities[j])
                    
            mats += [KroneckerStencilMatrix(V2_h.spaces[i].vector_space, V3_h.vector_space, *args)]
        
        Mat = BlockMatrix( V2_h.vector_space, ProductSpace(V3_h.vector_space), blocks=[mats])
        self._matrix = Mat

    def __call__(self, x):
        assert isinstance(x, VectorFemField)
        assert x.space == self._domain

        coeffs = self._matrix.dot(x.coeffs)
        coeffs.update_ghost_regions()

        return FemField(self._codomain, coeffs=coeffs[0])

#====================================================================================================
class Rot(DiffOperator):
    """
    2D Rot operator.

    Parameters
    ----------
    V0_h : TensorFemSpace
        Domain of 2D Rot operator.

    V1_h : ProductFemSpace
        Codomain of 2D Rot operator.

    """
    def __init__(self, V0_h, V1_h):

        assert isinstance(V0_h, TensorFemSpace)
        assert isinstance(V1_h, ProductFemSpace)

        self._domain   = V0_h
        self._codomain = V1_h
      
        if V0_h.ldim != 2:
            raise ValueError('only dimension 2 is available')


        d_matrices = [d_matrix(V.nbasis, V.degree, V.periodic) for V in V0_h.spaces]
        identities = [IdentityMatrix(V.vector_space) for V in V0_h.spaces]
         
        mats = [[None],[None]]
        mats[0][0] = KroneckerStencilMatrix(V0_h.vector_space, V1_h.spaces[0].vector_space, *[identities[0],d_matrices[1]])
        mats[1][0] = KroneckerStencilMatrix(V0_h.vector_space, V1_h.spaces[1].vector_space, *[-d_matrices[0],identities[1]])

        Mat = BlockMatrix( ProductSpace(V0_h.vector_space), V1_h.vector_space, blocks=mats )
        self._matrix = Mat

    def __call__(self, x):
        assert isinstance(x, FemField)
        assert x.space == self._domain

        y      = BlockVector(ProductSpace(x.coeffs.space), blocks=[x.coeffs])
        coeffs = self._matrix.dot(y)
        coeffs.update_ghost_regions()

        return VectorFemField(self._codomain, coeffs=coeffs)

