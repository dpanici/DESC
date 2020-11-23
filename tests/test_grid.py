import unittest
import numpy as np
from desc.grid import LinearGrid, ConcentricGrid


class TestGrid(unittest.TestCase):
    """Tests Grid classes"""

    def test_linear_grid(self):

        L = 3
        M = 1
        N = 1
        NFP = 1

        grid = LinearGrid(L, M, N, NFP, sym=False, endpoint=False)

        nodes = np.stack([np.array([0, 0, 0, 0.5, 0.5, 0.5, 1, 1, 1,
                                    0, 0, 0, 0.5, 0.5, 0.5, 1, 1, 1,
                                    0, 0, 0, 0.5, 0.5, 0.5, 1, 1, 1]),
                          np.array([0, 2*np.pi/3, 4*np.pi/3, 0, 2*np.pi/3, 4*np.pi/3, 0, 2*np.pi/3, 4*np.pi/3,
                                    0, 2*np.pi/3, 4*np.pi/3, 0, 2*np.pi/3, 4*np.pi/3, 0, 2*np.pi/3, 4*np.pi/3,
                                    0, 2*np.pi/3, 4*np.pi/3, 0, 2*np.pi/3, 4*np.pi/3, 0, 2*np.pi/3, 4*np.pi/3]),
                          np.array([0, 0, 0, 0, 0, 0, 0, 0, 0,
                                    2*np.pi/3, 2*np.pi/3, 2*np.pi/3, 2*np.pi/3, 2*np.pi/3, 2*np.pi/3, 2*np.pi/3, 2*np.pi/3, 2*np.pi/3,
                                    4*np.pi/3, 4*np.pi/3, 4*np.pi/3, 4*np.pi/3, 4*np.pi/3, 4*np.pi/3, 4*np.pi/3, 4*np.pi/3, 4*np.pi/3])])

        np.testing.assert_array_almost_equal(grid.nodes, nodes)
        self.assertAlmostEqual(np.sum(grid.volumes[0]*
                                      grid.volumes[1]*
                                      grid.volumes[2]),
                               (2*np.pi)**2/NFP)

    def test_concentric_grid(self):

        M = 2
        N = 0
        NFP = 1

        grid_ansi = ConcentricGrid(M, N, NFP, sym=False, axis=True,
                                   index='ansi', surfs='linear')
        grid_fringe = ConcentricGrid(M, N, NFP, sym=False, axis=True,
                                     index='fringe', surfs='linear')

        ansi_nodes = np.stack([np.array([0, 0.5, 0.5, 1, 1, 1]),
                               np.array([0, 0, np.pi, 0, 2*np.pi/3,
                                         4*np.pi/3]),
                               np.zeros((int((M+1)*(M+2)/2),))])
        fringe_nodes = np.stack([np.array([0, 0.5, 0.5, 0.5, 1, 1, 1, 1, 1]),
                                 np.array([0, 0, 2*np.pi/3, 4*np.pi/3, 0,
                                           2*np.pi/5, 4*np.pi/5, 6*np.pi/5,
                                           8*np.pi/5]),
                                 np.zeros((int((M+1)**2),))])

        np.testing.assert_array_almost_equal(grid_ansi.nodes, ansi_nodes)
        np.testing.assert_array_almost_equal(grid_fringe.nodes, fringe_nodes)
        self.assertAlmostEqual(np.sum(grid_ansi.volumes[0]*
                                      grid_ansi.volumes[1]*
                                      grid_ansi.volumes[2]),
                               (2*np.pi)**2/NFP)
        self.assertAlmostEqual(np.sum(grid_fringe.volumes[0]*
                                      grid_fringe.volumes[1]*
                                      grid_fringe.volumes[2]),
                               (2*np.pi)**2/NFP)