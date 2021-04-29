#coding = utf-8
from functools import reduce

import numpy as np
from scipy.sparse import kron

from psydac.linalg.basic   import LinearOperator, LinearSolver, Matrix
from psydac.linalg.stencil import StencilVectorSpace, StencilVector, StencilMatrix

__all__ = ['KroneckerStencilMatrix',
           'KroneckerLinearSolver',
           'kronecker_solve_2d_par',
           'kronecker_solve_3d_par',
           'kronecker_solve']

##==============================================================================
#def kron_dot(starts, ends, pads, X, X_tmp, Y, A, B):
#    s1 = starts[0]
#    s2 = starts[1]
#    e1 = ends[0]
#    e2 = ends[1]
#    p1 = pads[0]
#    p2 = pads[1]

#    for j1 in range(s1-p1, e1+p1+1):
#        for i2 in range(s2, e2+1):
#             
#             X_tmp[j1+p1-s1, i2-s2+p2] = sum(X[j1+p1-s1, i2-s2+k]*B[i2,k] for k in range(2*p2+1))
#    
#    for i1 in range(s1, e1+1):
#        for i2 in range(s2, e2+1):
#             Y[i1-s1+p1,i2-s2+p2] = sum(A[i1, k]*X_tmp[i1-s1+k, i2-s2+p2] for k in range(2*p1+1))
#    return Y

##==============================================================================
#class KroneckerStencilMatrix_2D( Matrix ):

#    def __init__( self, V, W, A1, A2 ):

#        assert isinstance( V, StencilVectorSpace )
#        assert isinstance( W, StencilVectorSpace )
#        assert V is W
#        assert V.ndim == 2

#        assert isinstance( A1, StencilMatrix )
#        assert A1.domain.ndim == 1
#        assert A1.domain.npts[0] == V.npts[0]

#        assert isinstance( A2, StencilMatrix )
#        assert A2.domain.ndim == 1
#        assert A2.domain.npts[0] == V.npts[1]

#        self._space = V
#        self._A1    = A1
#        self._A2    = A2
#        self._w     = StencilVector( V )

#    #--------------------------------------
#    # Abstract interface
#    #--------------------------------------
#    @property
#    def domain( self ):
#        return self._space

#    # ...
#    @property
#    def codomain( self ):
#        return self._space

#    # ...
#    def dot( self, v, out=None ):

#        dot = np.dot

#        assert isinstance( v, StencilVector )
#        assert v.space is self.domain

#        if out is not None:
#            assert isinstance( out, StencilVector )
#            assert out.space is self.codomain
#        else:
#            out = StencilVector( self.codomain )

#        [s1, s2] = self._space.starts
#        [e1, e2] = self._space.ends
#        [p1, p2] = self._space.pads

#        A1 = self._A1
#        A2 = self._A2
#        w  = self._w

#        for j1 in range(s1-p1, e1+p1+1):
#            for i2 in range(s2, e2+1):
#                 w[j1,i2] = dot( v[j1,i2-p2:i2+p2+1], A2[i2,:])

#        for i1 in range(s1, e1+1):
#            for i2 in range(s2, e2+1):
#                 out[i1,i2] = dot( A1[i1,:], w[i1-p1:i1+p1+1,i2] )

#        out.update_ghost_regions()

#        return out

#    #--------------------------------------
#    # Other properties/methods
#    #--------------------------------------
#    @property
#    def starts( self ):
#        return self._space.starts

#    # ...
#    @property
#    def ends( self ):
#        return self._space.ends

#    # ...
#    @property
#    def pads( self ):
#        return self._space.pads

#    # ...
#    def __getitem__(self, key):
#        raise NotImplementedError('TODO')

#    # ...
#    def tosparse( self ):
#        raise NotImplementedError('TODO')

#    #...
#    def tocsr( self ):
#        return self.tosparse().tocsr()

#    #...
#    def toarray( self ):
#        return self.tosparse().toarray()

#    #...
#    def copy( self ):
#        M = KroneckerStencilMatrix_2D( self.domain, self.codomain, self._A1, self._A2 )
#        return M

#==============================================================================
class KroneckerStencilMatrix( Matrix ):
    """ Kronecker product of 1D stencil matrices.
    """

    def __init__( self,V, W, *args ):

        assert isinstance( V, StencilVectorSpace )
        assert isinstance( W, StencilVectorSpace )

        for i,A in enumerate(args):
            assert isinstance( A, Matrix )
            assert A.domain.ndim == 1
            assert A.domain.npts[0] == V.npts[i]

        self._domain   = V
        self._codomain = W
        self._mats     = args
        self._ndim     = len(args)

    #--------------------------------------
    # Abstract interface
    #--------------------------------------
    @property
    def domain( self ):
        return self._domain

    # ...
    @property
    def codomain( self ):
        return self._codomain

    # ...
    @property
    def ndim( self ):
        return self._ndim
        
    # ...
    @property
    def mats( self ):
        return self._mats

    # ...
    def dot( self, x, out=None ):

        dot = np.dot

        assert isinstance( x, StencilVector )
        assert x.space is self.domain

        # Necessary if vector space is periodic or distributed across processes
        if not x.ghost_regions_in_sync:
            x.update_ghost_regions()

        if out is not None:
            assert isinstance( out, StencilVector )
            assert out.space is self.codomain
        else:
            out = StencilVector( self.codomain )

        starts = self._codomain.starts
        ends   = self._codomain.ends
        pads   = self._codomain.pads

        mats   = self.mats
        
        nrows  = tuple(e-s+1 for s,e in zip(starts, ends))
        pnrows = tuple(2*p+1 for p in pads)
        
        for ii in np.ndindex(*nrows):
            v = 0.
            xx = tuple(i+p for i,p in zip(ii, pads))

            for jj in np.ndindex(*pnrows):
                i_mats = [mat._data[s, j] for s,j,mat in zip(xx, jj, mats)]
                ii_jj = tuple(i+j for i,j in zip(ii, jj))
                v += x._data[ii_jj]*np.product(i_mats)

            out._data[xx] = v

        # IMPORTANT: flag that ghost regions are not up-to-date
        out.ghost_regions_in_sync = False
        return out

    # ...
    def copy(self):
        mats = [m.copy() for m in self.mats]
        return KroneckerStencilMatrix(self.domain, self.codomain, *mats)

    # ...
    def __neg__(self):
        mats = [-self.mats[0], *(m.copy() for m in self.mats[1:])]
        return KroneckerStencilMatrix(self.domain, self.codomain, *mats)

    # ...
    def __mul__(self, a):
        mats = [*(m.copy() for m in self.mats[:-1]), self.mats[-1] * a]
        return KroneckerStencilMatrix(self.domain, self.codomain, *mats)

    # ...
    def __rmul__(self, a):
        mats = [a * self.mats[0], *(m.copy() for m in self.mats[1:])]
        return KroneckerStencilMatrix(self.domain, self.codomain, *mats)

    # ...
    def __imul__(self, a):
        self.mats[-1] *= a
        return self

    # ...
    def __add__(self, m):
        raise NotImplementedError('Cannot sum Kronecker matrices')

    def __sub__(self, m):
        raise NotImplementedError('Cannot subtract Kronecker matrices')

    def __iadd__(self, m):
        raise NotImplementedError('Cannot sum Kronecker matrices')

    def __isub__(self, m):
        raise NotImplementedError('Cannot subtract Kronecker matrices')

    #--------------------------------------
    # Other properties/methods
    #--------------------------------------

    def __getitem__(self, key):
        pads = self._codomain.pads
        rows = key[:self.ndim]
        cols = key[self.ndim:]
        mats = self.mats
        elements = [A[i,j] for A,i,j in zip(mats, rows, cols)]
        return np.product(elements)

    def tostencil(self):

        mats  = self.mats
        ssc   = self.codomain.starts
        eec   = self.codomain.ends
        ssd   = self.domain.starts
        eed   = self.domain.ends
        pads  = [A.pads[0] for A in self.mats]
        xpads = self.domain.pads

        # Number of rows in matrix (along each dimension)
        nrows       = [ed-s+1 for s,ed in zip(ssd, eed)]
        nrows_extra = [0 if ec<=ed else ec-ed for ec,ed in zip(eec,eed)]

        # create the stencil matrix
        M  = StencilMatrix(self.domain, self.codomain, pads=tuple(pads))

        mats = [mat._data for mat in mats]

        self._tostencil(M._data, mats, nrows, nrows_extra, pads, xpads)
        return M

    @staticmethod
    def _tostencil(M, mats, nrows, nrows_extra, pads, xpads):

        ndiags = [2*p + 1 for p in pads]
        diff   = [xp-p for xp,p in zip(xpads, pads)]
        ndim   = len(nrows)

        for xx in np.ndindex( *nrows ):

            ii = tuple(xp + x for xp, x in zip(xpads, xx) )

            for kk in np.ndindex( *ndiags ):

                values        = [mat[i,k] for mat,i,k in zip(mats, ii, kk)]
                M[(*ii, *kk)] = np.product(values)

    def tosparse(self):
        return reduce(kron, (m.tosparse() for m in self.mats))

    def toarray(self):
        return self.tosparse().toarray()

    def transpose(self):
        mats_tr = [Mi.transpose() for Mi in self.mats]
        return KroneckerStencilMatrix(self.codomain, self.domain, *mats_tr)

    @property
    def T(self):
        return self.transpose()

class KroneckerLinearSolver( LinearSolver ):
    """
    A solver for Ax=b, where A is a Kronecker matrix from arbirary dimension d,
    defined by d solvers. We also need information about the space of b.

    Parameters
    ----------
    V : StencilVectorSpace
        The space b will live in; i.e. which gives us information about the distribution of the right-hand sides.
    
    solvers : list of LinearSolver
        The components of A in each dimension.
    
    Attributes
    ----------
    space : StencilVectorSpace
        The space our vectors to solve live in.
    """
    def __init__(self, V, solvers):
        assert isinstance( V, StencilVectorSpace )
        assert hasattr( solvers, '__iter__' )
        for solver in solvers:
            assert isinstance( solver, LinearSolver  )

        assert V.ndim == len( solvers )

        # general arguments
        self._space = V
        self._solvers = solvers
        self._mpi_type = V._mpi_type
        self._parallel = self._space.parallel
        self._ndim = self._space.ndim

        # compute and setup solver arguments
        self._setup_solvers()

        # compute reordering permutations between the steps
        self._setup_permutations()

        # for now: allocate temporary arrays here (can be removed later)
        self._temp1, self._temp2 = self._allocate_temps()
    
    def _setup_solvers( self ):
        """
        Computes the distribution of elements and sets up the solvers (which potentially utilize MPI).
        """
        # slice sizes
        starts = np.array(self._space.starts)
        ends = np.array(self._space.ends) + 1
        self._slice = tuple([slice(s, e) for s,e in zip(starts, ends)])

        # local and global sizes
        nglobals = self._space.npts
        nlocals = ends - starts
        self._localsize = np.product(nlocals)
        mglobals = self._localsize // nlocals
        self._nlocals = nlocals

        # solver passes (and mlocal size)
        solver_passes = [None] * self._ndim

        tempsize = self._localsize
        self._allserial = True
        for i in range(self._ndim):
            # decide for each direction individually, if we should use a serial or a parallel/distributed sovler
            # useful e.g. if we have little data in some directions (and thus no data distributed there)

            if not self._parallel or self._space.cart.subcomm[i].size <= 1:
                # serial solve
                solver_passes[i] = KroneckerSolverSerialPass(self._solvers[i], nglobals[i], mglobals[i])
            else:
                # TODO: also implement a pass using Alltoall (not Alltoallv), in case that the data is regular enough
                # for the parallel case, use Alltoallv
                solver_passes[i] = KroneckerSolverParallelPass(self._solvers[i], self._space._mpi_type, i, self._space.cart, mglobals[i], nglobals[i], nlocals[i], self._localsize)

                # we have a parallel solve pass now, so we are not completely local any more
                self._allserial = False
            
            # update memory requirements
            tempsize = max(tempsize, solver_passes[i].required_memory())
        
        # we want to start with the last dimension
        self._solver_passes = list(reversed(solver_passes))
        self._tempsize = tempsize

    def _setup_permutations(self):
        """
        Creates the permutations and matrix shapes which occur during reordering
        the data for the Kronecker solve operations.
        """

        # we want for the permutations:
        # a) re-order as little as possible
        # b) concatenating all permutations should give us the identity
        #
        # so we can do:
        # if we have (1,...,n) in the beginning, then do:
        # first reorder (1,...,n,n-1) (i.e. swap -1th with -2nd component)
        # second reorder(1,...,n,n-1,n-2) (i.e. swap -1th with -3rd component)
        # third reorder (1,...,n,n-2,n-1,n3)
        # until we get to (n, 2, ..., n-1, 1)
        # combining all these permutations, we have: (2,3,...,n-1,n,1)
        # the inverse of this last permutation is (n,1,2,...,n-1)

        # this way, we avoid too large strides
        self._perm = [None] * self._ndim
        for i in range(self._ndim - 1):
            # permutation which swaps -i-2 with -1
            self._perm[i] = np.arange(self._ndim)
            self._perm[i][-i-2], self._perm[i][-1] = self._perm[i][-1], self._perm[i][-i-2]
        # last permutation
        self._perm[-1] = np.arange(self._ndim)
        self._perm[-1][1:] = self._perm[-1][:-1]
        self._perm[-1][0] = self._ndim - 1

        # re-order the shapes based on the permutations
        self._shapes = [None] * self._ndim
        self._shapes[0] = self._nlocals
        for i in range(1, self._ndim):
            self._shapes[i] = self._shapes[i-1][self._perm[i-1]]
    
    def _allocate_temps( self ):
        """
        Allocates all temporary data needed for the solve operation.
        """
        temp1 = np.empty((self._tempsize,))
        if self._ndim <= 1 and self._allserial:
            # if ndim==1 and we have no parallelism, we can avoid allocating a second temp array
            temp2 = None
        else:
            temp2 = np.empty((self._tempsize,))
        return temp1, temp2
    
    @property
    def space( self ):
        """
        Returns the space associated to this solver (i.e. where the information about the cartesian distribution is taken from).
        """
        return self._space

    def solve( self, rhs, out=None, transposed=False ):
        """
        Solves Ax=b where A is a Kronecker product matrix (and represented as such),
        and b is a suitable vector.
        """

        # type checks
        assert rhs.space is self._space

        if out is not None:
            assert isinstance( out, StencilVector )
            assert out.space is self._space
        else:
            out = StencilVector( rhs.space )
        
        inslice = rhs[self._slice]
        outslice = out[self._slice]

        # call the actual kernel
        self._solve_nd(inslice, outslice, transposed)
        
        out.update_ghost_regions()
        return out
 
    def _solve_nd(self, inslice, outslice, transposed):
        """
        The internal solve loop. Can handle arbitrary dimensions.
        """
        temp1 = self._temp1
        temp2 = self._temp2

        # copy input
        self._inslice_to_temp(inslice, temp1)

        # internal passes
        for i in range(self._ndim - 1):
            # solve direction
            self._solver_passes[i].solve_pass(temp1, temp2, transposed)

            # reorder and swap
            self._reorder_temp_to_temp(temp1, temp2, i)
            temp1, temp2 = temp2, temp1
        
        # last pass
        self._solver_passes[-1].solve_pass(temp1, temp2, transposed)

        # copy to output
        self._reorder_temp_to_outslice(temp1, outslice)

    def _inslice_to_temp(self, inslice, target):
        """
        Copies data to an internal, 1-dimensional temporary array.
        """
        targetview = target[:self._localsize]
        targetview.shape = inslice.shape

        targetview[:] = inslice
    
    def _reorder_temp_to_temp(self, source, target, i):
        """
        Reorders the dimensions of the temporary arrays, and copies data from one to another.
        """
        sourceview = source[:self._localsize]
        sourceview.shape = self._shapes[i]

        targetview = target[:self._localsize]
        targetview.shape = self._shapes[i+1]

        targetview[:] = sourceview.transpose(self._perm[i])
    
    def _reorder_temp_to_outslice(self, source, outslice):
        """
        Reorders the dimensions of the temporary array for a final time, and copies it to the output.
        """
        sourceview = source[:self._localsize]
        sourceview.shape = self._shapes[-1]

        outslice[:] = sourceview.transpose(self._perm[-1])

class KroneckerSolverSerialPass:
    """
    Solves several linear equations at the same time, given that the data is already in memory.

    Not intended for outside use.

    Parameters
    ----------
    solver : DirectSolver
        The internally used solver class.
    
    nglobal : int
        The length of the dimension which we want to solve for.
    
    mglobal : int
        The number of right-hand sizes we want to solve. Equals the product of the
        number of dimensions which we do NOT want to solve for (when squashing all these dimensions into a single one).
        I.e. mglobal*nglobal is the total data size.
    """
    def __init__(self, solver, nglobal, mglobal):
        self._numrhs = mglobal
        self._dimrhs = nglobal
        self._datasize = nglobal*mglobal
        self._solver = solver
        self._view = None
    
    def required_memory(self):
        """
        Returns the required memory for this operation. Minimum size for the workmem and tempmem parameters.
        """
        return self._datasize

    def solve_pass(self, workmem, tempmem, transposed):
        """
        Solves the data available in workmem, assuming that all data is available locally.

        Parameters
        ----------
        workmem : ndarray
            The data which is used for solving. All columns to be solved are ordered contiguously.
        
        tempmem : ndarray
            Ignored, it exists for compatibility with the parallel solver.
        
        transposed : bool
            True, if and only if we want to solve against the transposed matrix instead.
        """
        # reshape necessary memory in column-major
        view = workmem[:self._datasize]
        view.shape = (self._numrhs,self._dimrhs)

        # the solvers want the FORTRAN-contiguous format
        # (TODO: push this into the DirectSolver?)
        view_T = view.transpose()

        # call solver in in-place mode
        self._solver.solve(view_T, out=view_T, transposed=transposed)

class KroneckerSolverParallelPass:
    """
    Solves several linear equations at the same time, using an Alltoallv operation to distribute the data.

    The parameters use the form of n and m; here n denotes the length of the dimension we want to solve for,
    and m is the length of all other dimensions, multiplied with each other. These n and m are then suffixed
    with local and global, denoting how much of them we have (or want to have) locally. I.e.
    nglobal is the dimension of the columns we want to solve, nlocal is the part we have on our local processor.
    mglobal is the number of right-hand sides to solve in the whole communicator, and mlocal is the number of
    right-hand sides we will solve on our local processor.

    Not intended for outside use.

    Parameters
    ----------
    solver : DirectSolver
        The internally used solver class.
    
    mpi_type : MPI type
        The MPI type of the space. Used for the Alltoallv.
    
    i : int
        The index of the dimension.
    
    cart : CartDecomposition
        The cartesian decomposition we use.

    mglobal : int
        The number of right-hand sizes we want to solve. Equals the product of the
        number of dimensions which we do NOT want to solve for (when squashing all these dimensions into a single one).
        I.e. mglobal*nglobal is the total data size in our communicator (not on the whole grid though).
    
    nglobal : int
        The length of the dimension which we want to solve. (the real length, not the one we have on this process)
    
    nlocal : int
        The length of the part of the dimension to solve which is located on this process already.

    localsize : int
        The size of data on our local process. Equals mlocal * nlocal (given that we know the former).
    """

    # To understand the following, here is a short explaination. Consider two processes like this:
    #
    # Pr1 | Pr2
    # 0 1 | 2 3
    # 4 5 | 6 7
    # 8 9 | A B 
    # C D | E F
    #
    # i.e. Pr1 has 0 1 4 5 8 9 C D; Pr2 has 2 3 6 7 A B E F
    #
    # We now would like to get each line on at least one process. So, we do an AlltoAll like this:
    #
    # Pr1 | Pr2
    # 0 1 | 2 3 | to Pr1
    # 4 5 | 6 7 | to Pr1
    # ------------------
    # 8 9 | A B | to Pr2
    # C D | E F | to Pr2
    #
    # But the data is transported per process, i.e. we get in this order:
    # 0 1 4 5 2 3 6 7 on Pr1
    # 8 9 C D A B E F on Pr2
    #
    # so we still need to re-order (i.e. partially transpose) locally to finally get what we want.
    # 0 1 2 3 4 5 6 7 on Pr1
    # 8 9 A B C D E F on Pr2
    #

    # NOTE: in case someone wants to create an Alltoall (not Alltoallv) pass class, this class is a good starting point, though simplifications will be needed
    
    def __init__(self, solver, mpi_type, i, cart, mglobal, nglobal, nlocal, localsize):
        self._nglobal = nglobal

        # cartesian distribution
        comm = cart.subcomm[i]
        cartend = cart.global_ends[i] + 1
        cartstart = cart.global_starts[i]
        cartsize = cartend - cartstart

        # source MPI sizes and disps
        # distribute the data like
        # (N+1, N+1, ..., N+1, N, N, ...)
        # where N = floor(mglobaldata / comm.size)
        mlocal_pre = mglobal // comm.size
        mlocal_add = mglobal % comm.size
        sourcesizes = np.full((comm.size,), mlocal_pre, dtype=int)
        sourcesizes[:mlocal_add] += 1
        mlocal = sourcesizes[comm.rank]
        sourcesizes *= nlocal

        # disps, created from the sizes
        sourcedisps = np.zeros((comm.size+1,), dtype=int)
        np.cumsum(sourcesizes, out=sourcedisps[1:])
        sourcedisps = sourcedisps[:-1]

        # target MPI sizes and disps
        # (mlocal is the same over all processes in the communicator)
        targetsizes = cartsize * mlocal
        targetdisps = cartstart * mlocal

        # setting all arguments to keep
        self._mlocal = mlocal
        self._localsize = localsize
        self._datasize = mlocal * nglobal
        self._source_transfer = (sourcesizes, sourcedisps)
        self._target_transfer = (targetsizes, targetdisps)
        self._mpi_type = mpi_type
        self._cartstart = cartstart
        self._cartend = cartend
        self._comm = comm
        self._serialsolver = KroneckerSolverSerialPass(solver, nglobal, mlocal)

    def required_memory(self):
        """
        Returns the required memory for this operation. Minimum size for the workmem and tempmem parameters.
        """
        return max(self._datasize, self._localsize)

    def _order_blocked(self, source, target):
        blocked_view = source[:self._datasize]
        blocked_view.shape = (self._mlocal,self._nglobal)
        for start, end in zip(self._cartstart, self._cartend):
            targetpart = target[start*self._mlocal:end*self._mlocal]
            targetpart.shape = (self._mlocal,end-start)
            blocked_view[:,start:end] = targetpart
    
    def _unorder_blocked(self, source, target):
        blocked_view = source[:self._datasize]
        blocked_view.shape = (self._mlocal,self._nglobal)
        for start, end in zip(self._cartstart, self._cartend):
            targetpart = target[start*self._mlocal:end*self._mlocal]
            targetpart.shape = (self._mlocal,end-start)
            targetpart[:] = blocked_view[:,start:end]

    def solve_pass(self, workmem, tempmem, transposed):
        """
        Solves the data available in workmem in a distributed manner, using MPI.

        Parameters
        ----------
        workmem : ndarray
            The data which is used for solving. All columns to be solved are ordered contiguously.
        
        tempmem : ndarray
            Temporary array of the same size as workmem.
        
        transposed : bool
            True, if and only if we want to solve against the transposed matrix instead.
        """
        # preparation
        sourceargs = [workmem[:self._localsize], self._source_transfer, self._mpi_type]
        targetargs = [tempmem[:self._datasize], self._target_transfer, self._mpi_type]

        # parts of stripes -> blocked stripes
        self._comm.Alltoallv(sourceargs, targetargs)

        # blocked stripes -> ordered stripes
        self._order_blocked(workmem, tempmem)

        # actual solve (source contains the data)
        self._serialsolver.solve_pass(workmem, tempmem, transposed)

        # ordered stripes -> blocked stripes
        self._unorder_blocked(workmem, tempmem)

        # blocked stripes -> parts of stripes
        self._comm.Alltoallv(targetargs, sourceargs)

#==============================================================================
def kronecker_solve( solvers, rhs, out=None, transposed=False ):
    """
    Solve linear system Ax=b with A=kron( A_n, A_{n-1}, ..., A_2, A_1 ), given
    $n$ separate linear solvers $L_n$ for the 1D problems $A_n x_n = b_n$:

    x_n = L_n.solve( b_n )

    Parameters
    ----------
    solvers : list( LinearSolver )
        List of linear solvers along each direction: [L_1, L_2, ..., L_n].

    rhs : StencilVector
        Right hand side vector of linear system Ax=b.

    """
    # all these feasability checks are again performed in the KroneckerLinearSolver class
    assert hasattr( solvers, '__iter__' )
    for solver in solvers:
        assert isinstance( solver, LinearSolver  )

    assert isinstance( rhs, StencilVector )
    assert rhs.space.ndim == len( solvers )

    if out is not None:
        assert isinstance( out, StencilVector )
        assert out.space is rhs.space
    else:
        out = StencilVector( rhs.space )

    kronsolver = KroneckerLinearSolver(rhs.space, solvers)
    return kronsolver.solve(rhs, transposed=transposed)

