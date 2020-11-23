import numpy as np
from desc.backend import TextColors
from abc import ABC


class Grid(ABC):
    """Grid is an abstract class that defines an API for collocation grids. 
    """

    def __init__(self) -> None:
        pass

    @abstract
    def create_nodes(self):
        pass

    def change_resolution(self) -> None:
        pass

    def sort_nodes(self) -> None:
        """Sorts nodes for use with FFT

            Returns
            -------
            None

        """

        sort_idx = np.lexsort((self.__nodes[1], self.__nodes[0], self.__nodes[2]))
        self.__nodes = self.__nodes[:, sort_idx]
        self.__volumes = self.__volumes[:, sort_idx]

    @property
    def nodes(self):
        return self.__nodes

    @nodes.setter
    def nodes(self, nodes):
        self.__nodes = nodes

    @property
    def volumes(self):
        return self.__volumes

    @volumes.setter
    def volumes(self, volumes):
        self.__volumes = volumes


class LinearGrid(Grid):
    """LinearGrid is a collocation grid in which the nodes are linearly 
       spaced in each coordinate. 
    """

    def __init__(self, L:int=1, M:int=0, N:int=0, NFP:int=1, sym:bool=False,
                 endpoint:bool=False, surfs=np.array([1.0])) -> None:
        """Initializes a LinearGrid

        Parameters
        ----------
        L : int
            radial grid resolution (L radial nodes, Defualt = 1)
        M : int
            poloidal grid resolution (2*M+1 poloidal nodes, Default = 0)
        N : int
            toroidal grid resolution (2*N+1 toroidal nodes, Default = 0)
        NFP : int
            number of field periods (Default = 1)
        sym : bool
            True for stellarator symmetry, False otherwise (Default = False)
        endpoint : bool
            if True, theta=0 and zeta=0 are duplicated after a full period. 
            Should be False for use with FFT (Default = False)
        surfs : ndarray of float
            radial coordinates

        Returns
        -------
        None

        """
        self.__L = L
        self.__M = M
        self.__N = N
        self.__NFP = NFP
        self.__sym = sym
        self.__endpoint = endpoint
        self.__surfs = surfs

        self._Grid__nodes, self._Grid__volumes = self.create_nodes(L=self.__L,
                                     M=self.__M, N=self.__N, NFP=self.__NFP,
                                     sym=self.__sym, surfs=self.__surfs)
        self.sort_nodes()

    def create_nodes(self, L:int=1, M:int=0, N:int=0, NFP:int=1,
                     sym:bool=False, endpoint:bool=False,
                     surfs=np.array([1.0])):
        """

        Parameters
        ----------
        L : int
            radial grid resolution (L radial nodes, Defualt = 1)
        M : int
            poloidal grid resolution (2*M+1 poloidal nodes, Default = 0)
        N : int
            toroidal grid resolution (2*N+1 toroidal nodes, Default = 0)
        NFP : int
            number of field periods (Default = 1)
        sym : bool
            True for stellarator symmetry, False otherwise (Default = False)
        endpoint : bool
            if True, theta=0 and zeta=0 are duplicated after a full period. 
            Should be False for use with FFT (Default = False)
        surfs : ndarray of float
            radial coordinates

        Returns
        -------
        nodes : ndarray, size(3,Nnodes)
            node coordinates, in (rho,theta,zeta)
        volumes : ndarray, size(3,Nnodes)
            node spacing (drho,dtheta,dzeta) at each node coordinate

        """
        # rho
        nr = L
        if surfs.size == nr:
            r = surfs
        else:
            r = np.linspace(0, 1, nr)
        dr = 1/nr

        # theta/vartheta
        nt = 2*M+1
        t = np.linspace(0, 2*np.pi, nt, endpoint=endpoint)
        dt = 2*np.pi/nt

        # zeta/phi
        nz = 2*N+1
        z = np.linspace(0, 2*np.pi/NFP, nz, endpoint=endpoint)
        dz = 2*np.pi/NFP/nz

        r, t, z = np.meshgrid(r, t, z, indexing='ij')
        r = r.flatten()
        t = t.flatten()
        z = z.flatten()

        dr = dr*np.ones_like(r)
        dt = dt*np.ones_like(t)
        dz = dz*np.ones_like(z)

        nodes = np.stack([r, t, z])
        volumes = np.stack([dr, dt, dz])

        if sym:
            non_sym_idx = np.where(t > np.pi)
            nodes = np.delete(nodes, non_sym_idx, axis=1)
            volumes = np.delete(volumes, non_sym_idx, axis=1)

        return nodes, volumes

    def change_resolution(self, L:int, M:int, N:int) -> None:
        """

        Parameters
        ----------
        L : int
            new radial grid resolution (L radial nodes)
        M : int
            new poloidal grid resolution (2*M+1 poloidal nodes)
        N : int
            new toroidal grid resolution (2*N+1 toroidal nodes)

        Returns
        -------
        None

        """
        if L != self.__L and M != self.__M and N != self.__N:
            self.__nodes, self.__volumes = self.create_nodes(L=L, M=M, N=N,
                                 NFP=self.__NFP, sym=self.__sym, 
                                 endpoint=self.__endpoint, surfs=self.__surfs)
            self.sort_nodes()


class ConcentricGrid(Grid):
    """ConcentricGrid is a collocation grid in which the nodes are arranged 
       in concentric circles within each toroidal cross-section. 
    """

    def __init__(self, M:int, N:int, NFP:int=1, sym:bool=False, axis:bool=True,
                 index='ansi', surfs='cheb1') -> None:
        """Initializes a ConcentricGrid

        Parameters
        ----------
        M : int
            poloidal grid resolution
        N : int
            toroidal grid resolution
        NFP : int
            number of field periods (Default = 1)
        sym : bool
            True for stellarator symmetry, False otherwise (Default = False)
        axis : bool
            True to include the magnetic axis, False otherwise (Default = True)
        index : string
            Zernike indexing scheme
                ansi (Default), chevron, fringe, house
        surfs : string
            pattern for radial coordinates
                cheb1 = Chebyshev-Gauss-Lobatto nodes scaled to r=[0,1]
                cheb2 = Chebyshev-Gauss-Lobatto nodes scaled to r=[-1,1]
                anything else defaults to linear spacing in r=[0,1]

        Returns
        -------
        None

        """
        self.__M = M
        self.__N = N
        self.__NFP = NFP
        self.__sym = sym
        self.__axis = axis
        self.__index = index
        self.__surfs = surfs

        self._Grid__nodes, self._Grid__volumes = self.create_nodes(M=self.__M,
                         N=self.__N, NFP=self.__NFP, sym=self.__sym,
                         axis=self.__axis, index=self.__index, surfs=self.__surfs)
        self.sort_nodes()

    def create_nodes(self, M:int, N:int, NFP:int=1, sym:bool=False,
                       axis:bool=True, index='ansi', surfs='cheb1'):
        """

        Parameters
        ----------
        M : int
            poloidal grid resolution
        N : int
            toroidal grid resolution
        NFP : int
            number of field periods (Default = 1)
        sym : bool
            True for stellarator symmetry, False otherwise (Default = False)
        axis : bool
            True to include the magnetic axis, False otherwise (Default = True)
        index : string
            Zernike indexing scheme
                ansi (Default), chevron, fringe, house
        surfs : string
            pattern for radial coordinates
                cheb1 = Chebyshev-Gauss-Lobatto nodes scaled to r=[0,1]
                cheb2 = Chebyshev-Gauss-Lobatto nodes scaled to r=[-1,1]
                anything else defaults to linear spacing in r=[0,1]

        Returns
        -------
        nodes : ndarray, size(3,Nnodes)
            node coordinates, in (rho,theta,zeta)
        volumes : ndarray, size(3,Nnodes)
            node spacing (drho,dtheta,dzeta) at each node coordinate

        """
        dim_fourier = 2*N+1
        if index in ['ansi', 'chevron']:
            dim_zernike = int((M+1)*(M+2)/2)
            a = 1
        elif index in ['fringe', 'house']:
            dim_zernike = int((M+1)**2)
            a = 2
        else:
            raise ValueError(
                TextColors.FAIL + "Invalid index input." + TextColors.ENDC)

        pattern = {
            'cheb1': (np.cos(np.arange(M, -1, -1)*np.pi/M)+1)/2,
            'cheb2': -np.cos(np.arange(M, 2*M+1, 1)*np.pi/(2*M))
        }
        rho = pattern.get(surfs, np.linspace(0, 1, num=M+1))
        rho = np.sort(rho, axis=None)
        if axis:
            rho[0] = 0
        else:
            rho[0] = rho[1]/4

        drho = np.zeros_like(rho)
        for i in range(rho.size):
            if i == 0:
                drho[i] = (rho[0]+rho[1])/2
            elif i == rho.size-1:
                drho[i] = 1-(rho[-2]+rho[-1])/2
            else:
                drho[i] = (rho[i+1]-rho[i-1])/2

        r = np.zeros(dim_zernike)
        t = np.zeros(dim_zernike)
        dr = np.zeros(dim_zernike)
        dt = np.zeros(dim_zernike)

        i = 0
        for m in range(M+1):
            dtheta = 2*np.pi/(a*m+1)
            theta = np.arange(0, 2*np.pi, dtheta)
            for j in range(a*m+1):
                r[i] = rho[m]
                t[i] = theta[j]
                dr[i] = drho[m]
                dt[i] = dtheta
                i += 1

        dz = 2*np.pi/(NFP*dim_fourier)
        z = np.arange(0, 2*np.pi/NFP, dz)

        r = np.tile(r, dim_fourier)
        t = np.tile(t, dim_fourier)
        z = np.tile(z[np.newaxis], (dim_zernike, 1)).flatten(order='F')
        dr = np.tile(dr, dim_fourier)
        dt = np.tile(dt, dim_fourier)
        dz = np.ones_like(z)*dz

        nodes = np.stack([r, t, z])
        volumes = np.stack([dr, dt, dz])

        if sym:
            non_sym_idx = np.where(t > np.pi)
            nodes = np.delete(nodes, non_sym_idx, axis=1)
            volumes = np.delete(volumes, non_sym_idx, axis=1)

        return nodes, volumes

    def change_resolution(self, M:int, N:int) -> None:
        """

        Parameters
        ----------
        M : int
            new poloidal grid resolution
        N : int
            new toroidal grid resolution

        Returns
        -------
        None

        """
        if M != self.__M and N != self.__N:
            self.__nodes, self.volumes = self.create_nodes(M=M, N=N,
                         NFP=self.__NFP, sym=self.__sym, surfs=self.__surfs)
            self.sort_nodes()


# these functions are currently unused ---------------------------------------

# TODO: finish option for placing nodes at irrational surfaces

def dec_to_cf(x, dmax=6):
    """Compute continued fraction form of a number.

    Parameters
    ----------
    x : float
        floating point form of number
    dmax : int
        maximum iterations (ie, number of coefficients of continued fraction). (Default value = 6)

    Returns
    -------
    cf : ndarray of int
        coefficients of continued fraction form of x.

    """
    cf = []
    q = np.floor(x)
    cf.append(q)
    x = x - q
    i = 0
    while x != 0 and i < dmax:
        q = np.floor(1 / x)
        cf.append(q)
        x = 1 / x - q
        i = i + 1
    return np.array(cf)


def cf_to_dec(cf):
    """Compute decimal form of a continued fraction.

    Parameters
    ----------
    cf : array-like
        coefficients of continued fraction.

    Returns
    -------
    x : float
        floating point representation of cf

    """
    if len(cf) == 1:
        return cf[0]
    else:
        return cf[0] + 1/cf_to_dec(cf[1:])


def most_rational(a, b):
    """Compute the most rational number in the range [a,b]

    Parameters
    ----------
    a,b : float
        lower and upper bounds

    Returns
    -------
    x : float
        most rational number between [a,b]

    """
    # handle empty range
    if a == b:
        return a
    # ensure a < b
    elif a > b:
        c = a
        a = b
        b = c
    # return 0 if in range
    if np.sign(a*b) <= 0:
        return 0
    # handle negative ranges
    elif np.sign(a) < 0:
        s = -1
        a *= -1
        b *= -1
    else:
        s = 1

    a_cf = dec_to_cf(a)
    b_cf = dec_to_cf(b)
    idx = 0  # first idex of dissimilar digits
    for i in range(min(a_cf.size, b_cf.size)):
        if a_cf[i] != b_cf[i]:
            idx = i
            break
    f = 1
    while True:
        dec = cf_to_dec(np.append(a_cf[0:idx], f))
        if dec >= a and dec <= b:
            return dec*s
        f += 1