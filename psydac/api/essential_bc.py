# coding: utf-8

from sympde.topology import Boundary as sym_Boundary

from psydac.linalg.stencil import StencilVector, StencilMatrix, StencilInterfaceMatrix
from psydac.linalg.block   import BlockVector, BlockMatrix


#==============================================================================
def apply_essential_bc_1d_StencilVector(V, bc, a):
    """ Apply homogeneous dirichlet boundary conditions in 1D """

    # assumes a 1D spline space
    # add asserts on the space if it is periodic

    # get order
    order = bc.order

    if bc.boundary.ext == -1:
        a[0+order] = 0.

    if bc.boundary.ext == 1:
        a[V.nbasis-1-order] = 0.

#==============================================================================
def apply_essential_bc_2d_StencilVector(V, bc, a):
    """ Apply homogeneous dirichlet boundary conditions in 2D """

    # assumes a 2D Tensor space
    # add asserts on the space if it is periodic

    V1,V2 = V.spaces

    s1, s2 = a.space.starts
    e1, e2 = a.space.ends

    # get order
    order = bc.order

    if bc.boundary.axis == 0:
        # left  bc.boundary.at x=0.
        if s1 == 0 and bc.boundary.ext == -1:
            a[0+order,:] = 0.

        # right bc.boundary.at x=1.
        if e1 == V1.nbasis-1 and bc.boundary.ext == 1:
            a [e1-order,:] = 0.

    if bc.boundary.axis == 1:
        # lower bc.boundary.at y=0.
        if s2 == 0 and bc.boundary.ext == -1:
            a [:,0+order] = 0.

        # upper bc.boundary.at y=1.
        if e2 == V2.nbasis-1 and bc.boundary.ext == 1:
            a [:,e2-order] = 0.

#==============================================================================
def apply_essential_bc_3d_StencilVector(V, bc, a):
    """ Apply homogeneous dirichlet boundary conditions in 3D """

    # assumes a 3D Tensor space
    # add asserts on the space if it is periodic

    V1,V2,V3 = V.spaces

    s1, s2, s3 = a.space.starts
    e1, e2, e3 = a.space.ends

    # get order
    order = bc.order

    if bc.boundary.axis == 0:
        # left  bc at x=0.
        if s1 == 0 and bc.boundary.ext == -1:
            a[0+order,:,:] = 0.

        # right bc at x=1.
        if e1 == V1.nbasis-1 and bc.boundary.ext == 1:
            a [e1-order,:,:] = 0.

    if bc.boundary.axis == 1:
        # lower bc at y=0.
        if s2 == 0 and bc.boundary.ext == -1:
            a [:,0+order,:] = 0.

        # upper bc at y=1.
        if e2 == V2.nbasis-1 and bc.boundary.ext == 1:
            a [:,e2-order,:] = 0.

    if bc.boundary.axis == 2:
        # lower bc at z=0.
        if s3 == 0 and bc.boundary.ext == -1:
            a [:,:,0+order] = 0.

        # upper bc at z=1.
        if e3 == V3.nbasis-1 and bc.boundary.ext == 1:
            a [:,:,e3-order] = 0.

#==============================================================================
def apply_essential_bc_1d_StencilMatrix(V, bc, a):
    """ Apply homogeneous dirichlet boundary conditions in 1D """

    # assumes a 1D spline space
    # add asserts on the space if it is periodic

    # get order
    order = bc.order

    if bc.boundary.ext == -1:
        a[ 0+order,:] = 0.

    if bc.boundary.ext == 1:
        a[-1-order,:] = 0.

#==============================================================================
def apply_essential_bc_2d_StencilMatrix(V, bc, a):
    """ Apply homogeneous dirichlet boundary conditions in 2D """

    # assumes a 2D Tensor space
    # add asserts on the space if it is periodic

    V1,V2 = V.spaces

    s1, s2 = a.domain.starts
    e1, e2 = a.domain.ends

    # get order
    order = bc.order

    if bc.boundary.axis == 0:
        # left  bc.boundary.at x=0.
        if s1 == 0 and bc.boundary.ext == -1:
            a[0+order,:,:,:] = 0.

        # right bc.boundary.at x=1.
        if e1 == V1.nbasis-1 and bc.boundary.ext == 1:
            a[e1-order,:,:,:] = 0.

    if bc.boundary.axis == 1:
        # lower bc.boundary.at y=0.
        if s2 == 0 and bc.boundary.ext == -1:
            a[:,0+order,:,:] = 0.

        # upper bc.boundary.at y=1.
        if e2 == V2.nbasis-1 and bc.boundary.ext == 1:
            a[:,e2-order,:,:] = 0.

#==============================================================================
def apply_essential_bc_3d_StencilMatrix(V, bc, a):
    """ Apply homogeneous dirichlet boundary conditions in 3D """

    # assumes a 3D Tensor space
    # add asserts on the space if it is periodic

    V1,V2,V3 = V.spaces

    s1, s2, s3 = a.domain.starts
    e1, e2, e3 = a.domain.ends

    # get order
    order = bc.order

    if bc.boundary.axis == 0:
        # left  bc at x=0.
        if s1 == 0 and bc.boundary.ext == -1:
            a[0+order,:,:,:,:,:] = 0.

        # right bc at x=1.
        if e1 == V1.nbasis-1 and bc.boundary.ext == 1:
            a[e1-order,:,:,:,:,:] = 0.

    if bc.boundary.axis == 1:
        # lower bc at y=0.
        if s2 == 0 and bc.boundary.ext == -1:
            a[:,0+order,:,:,:,:] = 0.

        # upper bc at y=1.
        if e2 == V2.nbasis-1 and bc.boundary.ext == 1:
            a[:,e2-order,:,:,:,:] = 0.

    if bc.boundary.axis == 2:
        # lower bc at z=0.
        if s3 == 0 and bc.boundary.ext == -1:
            a[:,:,0+order,:,:,:] = 0.

        # upper bc at z=1.
        if e3 == V3.nbasis-1 and bc.boundary.ext == 1:
            a[:,:,e3-order,:,:,:] = 0.


#==============================================================================
def apply_essential_bc_1d_StencilInterfaceMatrix(V, bc, a):
    """ Apply homogeneous dirichlet boundary conditions in 1D """

    # assumes a 1D spline space
    # add asserts on the space if it is periodic

    # get order
    order = bc.order
    ext     = bc.boundary.ext
    d_start = a._d_start
    pads    = a._pads

    s1  = a.domain.starts
    e1  = a.domain.ends

    if s1 == 0 and ext == -1 and d_start == 0:
        a._data[ pads[0]+order,:] = 0.

    if e1 == V.nbasis-1 and ext == 1 and d_start == e1:
        a._data[2*pads[0]-order,:] = 0.

#==============================================================================
def apply_essential_bc_2d_StencilInterfaceMatrix(V, bc, a):
    """ Apply homogeneous dirichlet boundary conditions in 2D """

    # assumes a 2D Tensor space
    # add asserts on the space if it is periodic
    V1,V2 = V.spaces

    s1, s2 = a.domain.starts
    e1, e2 = a.domain.ends

    # get order
    order   = bc.order
    axis    = bc.boundary.axis
    ext     = bc.boundary.ext
    d_start = a._d_start
    dim     = a._dim
    pads    = a._pads

    if  axis == 0  and axis != dim:
        # left  bc.boundary.at x=0.
        if s1 == 0 and ext == -1:
            a._data[pads[0]+order,:,:,:] = 0.

        # right bc.boundary.at x=1.
        if e1 == V1.nbasis-1 and ext == 1:
            a._data[pads[0]+e1-order,:,:,:] = 0.
    elif axis == 0:
        # left  bc.boundary.at x=0.
        if s1 == 0 and ext == -1 and d_start == 0:
            a._data[order+pads[0],:,:,:] = 0.

        # right bc.boundary.at x=1.
        if e1 == V1.nbasis-1 and ext == 1 and d_start == e1:
            a._data[2*pads[0]-order,:,:,:] = 0.

    if axis == 1 and axis != dim:
        # lower bc.boundary.at y=0.
        if s2 == 0 and ext == -1:
            a._data[:,pads[1]+order,:,:] = 0.

        # upper bc.boundary.at y=1.
        if e2 == V2.nbasis-1 and ext == 1:
            a._data[:,pads[1]+e2-order,:,:] = 0.
    elif axis == 1:
        # lower bc.boundary.at y=0.
        if s2 == 0 and ext == -1 and d_start == 0:
            a._data[:,pads[1]+order,:,:] = 0.

        # upper bc.boundary.at y=1.
        if e2 == V2.nbasis-1 and ext == 1 and d_start == e2:
            a._data[:,2*pads[1]-order,:,:] = 0.

#==============================================================================
def apply_essential_bc_3d_StencilInterfaceMatrix(V, bc, a):
    """ Apply homogeneous dirichlet boundary conditions in 3D """

    # assumes a 3D Tensor space
    # add asserts on the space if it is periodic

    V1,V2,V3 = V.spaces

    s1, s2, s3 = a.domain.starts
    e1, e2, e3 = a.domain.ends

    # get order
    order = bc.order
    axis    = bc.boundary.axis
    ext     = bc.boundary.ext
    d_start = a._d_start
    dim     = a._dim
    pads    = a._pads

    if axis == 0 and dim != 0:
        # left  bc at x=0.
        if s1 == 0 and ext == -1:
            a._data[pads[0]+order,:,:,:,:,:] = 0.

        # right bc at x=1.
        if e1 == V1.nbasis-1 and ext == 1:
            a._data[pads[0]+e1-order,:,:,:,:,:] = 0.

    elif axis == 0:
        # left  bc at x=0.
        if s1 == 0 and ext == -1 and d_start == 0:
            a._data[pads[0]+order,:,:,:,:,:] = 0.

        # right bc at x=1.
        if e1 == V1.nbasis-1 and ext == 1 and d_start == e1:
            a._data[2*pads[0]-order,:,:,:,:,:] = 0.

    if axis == 1 and dim != 1:
        # lower bc at y=0.
        if s2 == 0 and ext == -1:
            a._data[:,pads[1]+order,:,:,:,:] = 0.

        # upper bc at y=1.
        if e2 == V2.nbasis-1 and ext == 1:
            a._data[:,pads[1]+e2-order,:,:,:,:] = 0.

    elif axis == 1:
            # lower bc at y=0.
        if s2 == 0 and ext == -1 and d_start == 0:
            a._data[:,pads[1]+order,:,:,:,:] = 0.

        # upper bc at y=1.
        if e2 == V2.nbasis-1 and ext == 1 and d_start == e2:
            a._data[:,2*pads[1]-order,:,:,:,:] = 0.

    if axis == 2 and dim != 2:
        # lower bc at z=0.
        if s3 == 0 and ext == -1:
            a._data[:,:,pads[2]+order,:,:,:] = 0.

        # upper bc at z=1.
        if e3 == V3.nbasis-1 and ext == 1:
            a._data[:,:,pads[2]+e3-order,:,:,:] = 0.
            # lower bc at z=0.
    elif axis == 2:
        if s3 == 0 and ext == -1 and d_start == 0:
            a._data[:,:,pads[2]+order,:,:,:] = 0.

        # upper bc at z=1.
        if e3 == V3.nbasis-1 and ext == 1 and d_start == e3:
            a._data[:,:,2*pads[2]-order,:,:,:] = 0.

#==============================================================================
# V is a ProductFemSpace here
def apply_essential_bc_BlockMatrix(V, bc, a):
    """ Apply homogeneous dirichlet boundary conditions in nD """
    keys = list(a._blocks.keys())
    if bc.index_component:
        for i_loc in bc.index_component:
            i = bc.position + i_loc
            js = [ij[1] for ij in keys if ij[0] == i]
            Vi = V.spaces[i]
            for j in js:
                M = a[i,j]
                apply_essential_bc(Vi, bc, M)
    else:
        var = bc.variable
        space = var.space
        if space.is_broken:
            domains = space.domain.interior.args
            bd = bc.boundary.domain
            i  = domains.index(bd)
            js = [ij[1] for ij in keys if ij[0] == i]
            Vi = V.spaces[i]
            for j in js:
                M = a[i,j]
                apply_essential_bc(Vi, bc, M)

#==============================================================================
# V is a ProductFemSpace here
def apply_essential_bc_BlockVector(V, bc, a):
    """ Apply homogeneous dirichlet boundary conditions in nD """

    if bc.index_component:
        for i_loc in bc.index_component:
            i = bc.position + i_loc

            M = a[i]
            Vi = V.spaces[i]
            apply_essential_bc(Vi, bc, M)
    else:
        var = bc.variable
        space = var.space
        if space.is_broken:
            domains = space.domain.interior.args
            bd = bc.boundary.domain
            i  = domains.index(bd)
            Vi = V.spaces[i]
            apply_essential_bc(Vi, bc, a[i])

#==============================================================================
# TODO must pass two spaces for a matrix
def apply_essential_bc(V, bc, *args, **kwargs):

    if not isinstance(bc, (tuple, list)):
        bc = [bc]

    _avail_classes = [StencilVector, StencilMatrix, StencilInterfaceMatrix,
                      BlockVector, BlockMatrix]
    for a in args:
        classes = type(a).__mro__
        classes = set(classes) & set(_avail_classes)
        classes = list(classes)
        if not classes:
            raise TypeError('> wrong argument type {}'.format(type(a)))

        cls = classes[0]

        if not isinstance(a, (BlockMatrix, BlockVector)):
            pattern = 'apply_essential_bc_{dim}d_{name}'
            apply_bc = pattern.format( dim = V.ldim, name = cls.__name__ )

        else:
            pattern = 'apply_essential_bc_{name}'
            apply_bc = pattern.format( name = cls.__name__ )
        apply_bc = eval(apply_bc)
        for b in bc:
            apply_bc(V, b, a, **kwargs)
