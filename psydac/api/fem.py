# coding: utf-8

# TODO: - init_fem is called whenever we call discretize. we should check that
#         nderiv has not been changed. shall we add quad_order too?

# TODO: avoid using os.system and use subprocess.call


from sympde.expr     import BasicForm as sym_BasicForm
from sympde.expr     import BilinearForm as sym_BilinearForm
from sympde.expr     import LinearForm as sym_LinearForm
from sympde.expr     import Functional as sym_Functional
from sympde.expr     import Equation as sym_Equation
from sympde.expr     import Boundary as sym_Boundary
from sympde.expr     import Norm as sym_Norm
from sympde.topology import Domain, Boundary
from sympde.topology import Line, Square, Cube
from sympde.topology import BasicFunctionSpace
from sympde.topology import ScalarFunctionSpace, VectorFunctionSpace
from sympde.topology import ProductSpace
from sympde.topology import Mapping

from psydac.api.basic           import BasicDiscrete
from psydac.api.basic           import random_string
from psydac.api.grid            import QuadratureGrid, BoundaryQuadratureGrid
from psydac.api.grid            import BasisValues
from psydac.api.ast.fem         import Kernel
from psydac.api.ast.fem         import Assembly
from psydac.api.ast.fem         import Interface
from psydac.api.ast.glt         import GltKernel
from psydac.api.ast.glt         import GltInterface
from psydac.api.glt             import DiscreteGltExpr
from psydac.api.utilities        import flatten

from psydac.linalg.stencil      import StencilVector, StencilMatrix
from psydac.cad.geometry        import Geometry
from psydac.mapping.discrete    import SplineMapping, NurbsMapping
from psydac.fem.vector          import ProductFemSpace

from collections import OrderedDict
from sympy import Matrix
import inspect
import sys
import numpy as np


#==============================================================================
class DiscreteBilinearForm(BasicDiscrete):

    def __init__(self, expr, kernel_expr, *args, **kwargs):
        if not isinstance(expr, sym_BilinearForm):
            raise TypeError('> Expecting a symbolic BilinearForm')

        if not args:
            raise ValueError('> fem spaces must be given as a list/tuple')

        assert( len(args) == 2 )

        # ...
        domain_h = args[0]
        assert( isinstance(domain_h, Geometry) )

        mapping = list(domain_h.mappings.values())[0]
        self._mapping = mapping

        is_rational_mapping = False
        if not( mapping is None ):
            is_rational_mapping = isinstance( mapping, NurbsMapping )

        self._is_rational_mapping = is_rational_mapping
        # ...
        self._spaces = args[1]
        # ...
        kwargs['discrete_space']      = self.spaces
        kwargs['mapping']             = self.spaces[0].symbolic_mapping
        kwargs['is_rational_mapping'] = is_rational_mapping
        kwargs['comm']                = domain_h.comm

        boundary = kwargs.pop('boundary', [])
        if boundary and isinstance(boundary, list):
            kwargs['boundary'] = boundary[0]
        elif boundary:
            kwargs['boundary'] = boundary

        BasicDiscrete.__init__(self, expr, kernel_expr, **kwargs)

        # ...
        trial_space = self.spaces[0]
        test_space  = self.spaces[1]
        # ...

        # ...
        quad_order = kwargs.pop('quad_order', None)
        boundary   = kwargs.pop('boundary',   None)
        # ...

        # ...
        # TODO must check that spaces lead to the same QuadratureGrid
        if boundary is None:
            self._grid = QuadratureGrid( test_space, quad_order = quad_order )

        else:   
            self._grid = BoundaryQuadratureGrid( test_space,
                                                 boundary.axis,
                                                 boundary.ext,
                                                 quad_order = quad_order )
        # ...
        self._test_basis = BasisValues( test_space, self.grid,
                                        nderiv = self.max_nderiv )
        self._trial_basis = BasisValues( trial_space, self.grid,
                                         nderiv = self.max_nderiv )
        self._args = self.construct_arguments()

    @property
    def spaces(self):
        return self._spaces

    @property
    def grid(self):
        return self._grid

    @property
    def test_basis(self):
        return self._test_basis

    @property
    def trial_basis(self):
        return self._trial_basis

    @property
    def args(self):
        return self._args

    def assemble(self, **kwargs):
        newargs = tuple(self.spaces) + (self.grid, self.test_basis, self.trial_basis)
        if self.mapping:
            newargs = newargs + (self.mapping,)

        kwargs = self._check_arguments(**kwargs)

        return self.func(*newargs, **kwargs)

    def construct_arguments(self):
        tests_basis = flatten(self.test_basis.basis)
        trial_basis = flatten(self.trial_basis.basis)
        spans = flatten(self.test_basis.spans)
        points = self.grid.points
        weights = self.grid.weights
        quads   = flatten(list(zip(points, weights)))
        tests_degrees = flatten(self.spaces[1].degree)
        trials_degrees = flatten(self.spaces[0].degree)
        quads_degree = flatten(self.grid.quad_order)
        global_pads = self.spaces[0].vector_space.pads
        mats = self.allocate_matrices()
        mapping = self.mapping
        args = (*tests_basis, *trial_basis, *spans, *quads, *tests_degrees, *trials_degrees, *quads_degree, *global_pads, *mats, mapping)
        return args

    def allocate_matrices(self):
        spaces = self.spaces
        expr   = self.kernel_expr
        global_mats = OrderedDict()
        local_mats  = OrderedDict()
        test_space  = spaces[1].vector_space
        trial_space = spaces[0].vector_space
        test_degree = np.array(spaces[1].degree)
        trial_degree = np.array(spaces[0].degree)
        pads  = np.block([[*test_degree],[*trial_degree]]).max(axis=0).reshape(test_degree.shape)
        if isinstance(expr, Matrix):
            for i in range(expr.shape[0]):
                for j in range(expr.shape[1]):
                    if expr[i,j].is_zero:
                        continue
                    else:
                        global_mats[i,j] = StencilMatrix(test_space.spaces[i], trial_space.spaces[j])
                        local_mats[i,j]  = np.zeros((*test_degree[i],*(2*pads[j]+1)))
        else:
            global_mats[0,0] = StencilMatrix(test_space, trial_space)
            local_mats[0,0]  = np.zeros((*test_degree,*(2*pads+1)))

        return [*local_mats.values(), *global_mats.values()]
#==============================================================================
class DiscreteLinearForm(BasicDiscrete):

    def __init__(self, expr, kernel_expr, *args, **kwargs):
        if not isinstance(expr, sym_LinearForm):
            raise TypeError('> Expecting a symbolic LinearForm')

        assert( len(args) == 2 )

        domain_h = args[0]
        assert( isinstance(domain_h, Geometry) )

        mapping = list(domain_h.mappings.values())[0]
        self._mapping = mapping

        is_rational_mapping = False
        if not( mapping is None ):
            is_rational_mapping = isinstance( mapping, NurbsMapping )

        self._is_rational_mapping = is_rational_mapping

        self._space = args[1]

        kwargs['discrete_space']      = self.space
        kwargs['mapping']             = self.space.symbolic_mapping
        kwargs['is_rational_mapping'] = is_rational_mapping
        kwargs['comm']                = domain_h.comm

        boundary = kwargs.pop('boundary', [])
        if boundary and isinstance(boundary, list):
            kwargs['boundary'] = boundary[0]
        elif boundary:
            kwargs['boundary'] = boundary

        BasicDiscrete.__init__(self, expr, kernel_expr, **kwargs)

        # ...
        quad_order = kwargs.pop('quad_order', None)
        boundary   = kwargs.pop('boundary',   None)
        # ...

        if boundary is None:
            self._grid = QuadratureGrid( self.space, quad_order = quad_order )

        else:

            self._grid = BoundaryQuadratureGrid( self.space,
                                                 boundary.axis,
                                                 boundary.ext,
                                                 quad_order = quad_order )

        self._test_basis = BasisValues( self.space, self.grid,
                                        nderiv = self.max_nderiv )
    @property
    def space(self):
        return self._space

    @property
    def grid(self):
        return self._grid

    @property
    def test_basis(self):
        return self._test_basis

    def assemble(self, **kwargs):
        newargs = (self.space, self.grid, self.test_basis)
        
        if self.mapping:
            newargs = newargs + (self.mapping,)

        kwargs = self._check_arguments(**kwargs)
        return self.func(*newargs, **kwargs)


#==============================================================================
class DiscreteFunctional(BasicDiscrete):

    def __init__(self, expr, kernel_expr, *args, **kwargs):
        if not isinstance(expr, sym_Functional):
            raise TypeError('> Expecting a symbolic Functional')

        assert( len(args) == 2 )

        # ...
        domain_h = args[0]
        assert( isinstance(domain_h, Geometry) )

        mapping = list(domain_h.mappings.values())[0]
        self._mapping = mapping

        is_rational_mapping = False
        if not( mapping is None ):
            is_rational_mapping = isinstance( mapping, NurbsMapping )

        self._is_rational_mapping = is_rational_mapping

        self._space = args[1]

        kwargs['discrete_space']      = self.space
        kwargs['mapping']             = self.space.symbolic_mapping
        kwargs['is_rational_mapping'] = is_rational_mapping
        kwargs['comm']                = domain_h.comm

        BasicDiscrete.__init__(self, expr, kernel_expr, **kwargs)

        # ...
        quad_order = kwargs.pop('quad_order', None)
        boundary   = kwargs.pop('boundary',   None)
        # ...

        if boundary is None:
            self._grid = QuadratureGrid( self.space, quad_order = quad_order )

        else:
            self._grid = BoundaryQuadratureGrid( self.space,
                                                 boundary.axis,
                                                 boundary.ext,
                                                 quad_order = quad_order )

        # ...
        self._test_basis = BasisValues( self.space, self.grid,
                                        nderiv = self.max_nderiv )

    @property
    def space(self):
        return self._space

    @property
    def grid(self):
        return self._grid

    @property
    def test_basis(self):
        return self._test_basis

    def assemble(self, **kwargs):
        newargs = (self.space, self.grid, self.test_basis)

        if self.mapping:
            newargs = newargs + (self.mapping,)

        kwargs = self._check_arguments(**kwargs)

        v = self.func(*newargs, **kwargs)

#        # ... TODO remove => this is for debug only
#        import sys
#        sys.path.append(self.folder)
#        from interface_pt3xujb5 import  interface_pt3xujb5
#        sys.path.remove(self.folder)
#        return interface_pt3xujb5(*newargs, **kwargs)
#        # ...

        # case of a norm
        
        if isinstance(self.expr, sym_Norm):
            if not( self.comm is None ):
                v = self.comm.allreduce(sendobj=v)

            if self.expr.exponent == 2:
                # add abs because of 0 machine
                v = np.sqrt(np.abs(v))

            else:
                raise NotImplementedError('TODO')

        return v


#==============================================================================
class DiscreteSumForm(BasicDiscrete):

    def __init__(self, a, kernel_expr, *args, **kwargs):
        if not isinstance(a, (sym_BilinearForm, sym_LinearForm, sym_Functional)):
            raise TypeError('> Expecting a symbolic BilinearForm, LinearFormn Functional')

        self._expr = a

        backend = kwargs.get('backend', None)
        self._backend = backend

        folder = kwargs.get('folder', None)
        self._folder = self._initialize_folder(folder)

        # create a module name if not given
        tag = random_string( 8 )

        # ...
        forms = []
        boundaries = kwargs.pop('boundary', [])

        for e in kernel_expr:
            kwargs['target'] = e.target
            if isinstance(e.target, sym_Boundary):
                boundary = [i for i in boundaries if i is e.target]
                if boundary: kwargs['boundary'] = boundary[0]

            if isinstance(a, sym_BilinearForm):
                ah = DiscreteBilinearForm(a, kernel_expr, *args, **kwargs)

            elif isinstance(a, sym_LinearForm):
                ah = DiscreteLinearForm(a, kernel_expr, *args, **kwargs)

            elif isinstance(a, sym_Functional):
                ah = DiscreteFunctional(a, kernel_expr, *args, **kwargs)

            forms.append(ah)
            kwargs['boundary'] = None

        self._forms = forms
        # ...

    @property
    def forms(self):
        return self._forms

    def assemble(self, **kwargs):
        form = self.forms[0]
        M = form.assemble(**kwargs)
        if isinstance(M, (StencilVector, StencilMatrix)):
            M = [M]

        for form in self.forms[1:]:
            n = len(form.interface.inout_arguments)
            # add arguments
            for i in range(0, n):
                key = str(form.interface.inout_arguments[i])
                kwargs[key] = M[i]

            M = form.assemble(**kwargs)
            if isinstance(M, (StencilVector, StencilMatrix)):
                M = [M]

            # remove arguments
            for i in range(0, n):
                key = str(form.interface.inout_arguments[i])
                kwargs.pop(key)

        if len(M) == 1: M = M[0]

        return M
