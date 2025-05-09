from __future__ import annotations

import itertools

import numpy as np
from numpy.testing import assert_allclose
from pytest import approx

from pymatgen.analysis.chemenv.utils.coordination_geometry_utils import Plane
from pymatgen.util.testing import MatSciTest

__author__ = "David Waroquiers"


class TestPlanesUtils(MatSciTest):
    def setup_method(self):
        # Test of plane 4x + 2y - 4z + 3 = 0 (used in most test cases)
        self.expected_coefficients = np.array([4, 2, -4, 3], float)
        self.p1 = np.array([0, 0, 0.75])
        self.p2 = np.array([-0.75, 0, 0])
        self.p3 = np.array([0, -1.5, 0])
        self.plane = Plane.from_3points(self.p1, self.p2, self.p3)

    def test_factors_abcd_normal_vector(self):
        factors = self.plane.coefficients / self.expected_coefficients
        assert_allclose([factors[0]] * 4, list(factors))
        assert_allclose([2 / 3, 1 / 3, -2 / 3], self.plane.normal_vector)

    def test_from_npoints_plane(self):
        best_fits = ["least_square_distance", "maximum_distance"]
        delta = 0.0001
        for best_fit in best_fits:
            plane = Plane.from_npoints([self.p1, self.p2, self.p3], best_fit=best_fit)
            assert self.plane.is_same_plane_as(plane)
            points = [
                np.array([5.1, 0.3, -2.3]),
                np.array([-2, 4.3, -6.3]),
                np.array([3.1, 2.3, -21.3]),
                np.array([-2, -0.5, 0.05]),
                np.array([11, 12, -13]),
                np.array([10, 8.3, -6.32]),
            ]
            plane = Plane.from_npoints(points, best_fit=best_fit)
            fit_error_plane = plane.fit_error(points, fit=best_fit)
            coeffs = [
                [1 + delta, 1, 1, 1],
                [1, 1 + delta, 1, 1],
                [1, 1, 1 + delta, 1],
                [1, 1, 1, 1 + delta],
                [1 - delta, 1 + delta, 1 - delta, 1 + delta],
            ]
            for coeff in coeffs:
                plane_changed = Plane.from_coefficients(
                    coeff[0] * plane.a,
                    coeff[1] * plane.b,
                    coeff[2] * plane.c,
                    coeff[3] * plane.d,
                )
                fit_error = plane_changed.fit_error(points, fit=best_fit)
                assert fit_error > fit_error_plane
            coeff = [-2.1, -2.1, -2.1, -2.1]
            plane_not_changed = Plane.from_coefficients(
                coeff[0] * plane.a,
                coeff[1] * plane.b,
                coeff[2] * plane.c,
                coeff[3] * plane.d,
            )
            fit_error = plane_not_changed.fit_error(points, fit=best_fit)
            assert fit_error == approx(fit_error_plane)

    def test_is_in_plane(self):
        assert self.plane.is_in_plane(self.p1, 0.001)
        assert self.plane.is_in_plane(self.p2, 0.001)
        assert self.plane.is_in_plane(self.p3, 0.001)
        assert not self.plane.is_in_plane(np.zeros(3), 0.001)
        assert self.plane.is_in_plane(np.array([1, 1, 2.25]), 0.001)
        assert self.plane.is_in_plane(np.array([1, 1, 2.22]), 0.1)
        assert not self.plane.is_in_plane(np.array([1, 1, 2.22]), 0.001)
        assert self.plane.is_in_plane(self.p1 + self.plane.normal_vector * 1, 1.000001)
        assert not self.plane.is_in_plane(self.p1 + self.plane.normal_vector * 1.00001, 1)
        assert not self.plane.is_in_plane(self.p1 + self.plane.normal_vector * 1, 0.999999)
        assert self.plane.is_in_plane(self.plane.p1, 0.00001)
        assert self.plane.is_in_plane(self.plane.p2, 0.00001)
        assert self.plane.is_in_plane(self.plane.p3, 0.00001)

    def test_normal_vector_is_normed(self):
        assert np.isclose(np.linalg.norm(self.plane.normal_vector), 1)

    def test_orthonormal_vectors(self):
        ortho = self.plane.orthonormal_vectors()
        assert np.isclose(np.dot(ortho[0], self.plane.normal_vector), 0)
        assert np.isclose(np.dot(ortho[1], self.plane.normal_vector), 0)
        assert np.isclose(np.dot(ortho[2], self.plane.normal_vector), 1)
        assert np.isclose(np.dot(ortho[0], ortho[1]), 0)
        assert np.isclose(np.dot(ortho[1], ortho[2]), 0)
        assert np.isclose(np.dot(ortho[2], ortho[0]), 0)
        assert_allclose(np.cross(ortho[0], ortho[1]), ortho[2])
        assert_allclose(np.cross(ortho[0], ortho[1]), self.plane.normal_vector)
        assert_allclose(np.cross(ortho[1], ortho[2]), ortho[0])
        assert_allclose(np.cross(ortho[2], ortho[0]), ortho[1])
        assert not np.allclose(np.cross(ortho[1], ortho[0]), ortho[2])
        assert_allclose(np.cross(ortho[0], ortho[1]), self.plane.normal_vector)

    def test_plane_comparison(self):
        plane_test_1 = Plane.from_coefficients(4, 2, -4, 3)
        assert self.plane.is_same_plane_as(plane_test_1)
        plane_test_2 = Plane.from_coefficients(-4, -2, 4, -3)
        assert self.plane.is_same_plane_as(plane_test_2)
        plane_test_3 = Plane.from_coefficients(-12, -6, 12, -9)
        assert self.plane.is_same_plane_as(plane_test_3)
        plane_test_4 = Plane.from_coefficients(3, 0, 2, 4)
        assert not self.plane.is_same_plane_as(plane_test_4)

    def test_plane_is_in_list_of_planes(self):
        plane_test_1 = Plane.from_coefficients(-8.1, 2, -4, 3)
        plane_test_2 = Plane.from_coefficients(0, -2, 4, 0)
        plane_test_3 = Plane.from_coefficients(-12, -6, 12, -9)
        plane_test_4 = Plane.from_coefficients(3, 0, 0, 4)
        plane_list = [plane_test_1, plane_test_2, plane_test_3, plane_test_4]
        assert self.plane.is_in_list(plane_list)
        plane_list = [plane_test_1, plane_test_2, plane_test_4]
        assert not self.plane.is_in_list(plane_list)

    def test_plane_3_coefficients(self):
        plane_1 = Plane.from_coefficients(0, 2, -1, 3)
        assert plane_1.is_in_plane(plane_1.p1, 0.000001)
        assert plane_1.is_in_plane(plane_1.p2, 0.000001)
        assert plane_1.is_in_plane(plane_1.p3, 0.000001)
        plane_2 = Plane.from_coefficients(12, 0, 2, -4)
        assert plane_2.is_in_plane(plane_2.p1, 0.000001)
        assert plane_2.is_in_plane(plane_2.p2, 0.000001)
        assert plane_2.is_in_plane(plane_2.p3, 0.000001)
        plane_3 = Plane.from_coefficients(-8, 8, 0, 0)
        assert plane_3.is_in_plane(plane_3.p1, 0.000001)
        assert plane_3.is_in_plane(plane_3.p2, 0.000001)
        assert plane_3.is_in_plane(plane_3.p3, 0.000001)

    def test_plane_2_coefficients(self):
        plane_1 = Plane.from_coefficients(-21, 0, 0, 3)
        assert plane_1.is_in_plane(plane_1.p1, 0.000001)
        assert plane_1.is_in_plane(plane_1.p2, 0.000001)
        assert plane_1.is_in_plane(plane_1.p3, 0.000001)
        plane_2 = Plane.from_coefficients(0, 4, 0, -4)
        assert plane_2.is_in_plane(plane_2.p1, 0.000001)
        assert plane_2.is_in_plane(plane_2.p2, 0.000001)
        assert plane_2.is_in_plane(plane_2.p3, 0.000001)
        plane_3 = Plane.from_coefficients(0, 0, 3, 1)
        assert plane_3.is_in_plane(plane_3.p1, 0.000001)
        assert plane_3.is_in_plane(plane_3.p2, 0.000001)
        assert plane_3.is_in_plane(plane_3.p3, 0.000001)

    def test_indices_separate(self):
        # Test with the common test plane
        point_1 = np.array([0, 0, 0], float)
        point_2 = np.array([0, 0, 0.75], float)
        point_3 = np.array([-0.75, 0, 0], float)
        point_4 = np.array([1, 0, 0], float)
        point_5 = np.array([0, -1.5, 0], float)
        point_6 = np.array([10, 2, -20], float)
        point_7 = np.array([10, 10, 10], float)
        point_8 = np.array([100, 0, 0], float)
        plist = [point_1, point_2, point_3, point_4, point_5, point_6, point_7, point_8]
        sep = self.plane.indices_separate(plist, 0.000001)
        assert len(sep[0]) == 0
        assert len(sep[1]) == 3
        assert len(sep[2]) == 5
        assert_allclose(sep[1], [1, 2, 4])
        assert_allclose(sep[2], [0, 3, 5, 6, 7])
        sep = self.plane.indices_separate(plist, 10)
        assert len(sep[0]) == 0
        assert len(sep[1]) == 6
        assert len(sep[2]) == 2
        assert_allclose(sep[1], [0, 1, 2, 3, 4, 6])
        assert_allclose(sep[2], [5, 7])
        sep = self.plane.indices_separate(plist, 100000)
        assert len(sep[0]) == 0
        assert len(sep[1]) == 8
        assert len(sep[2]) == 0
        # Test with 2 coeff facets (Normal vector = [1, 0, 0] or [0, 1, 0] or [0, 0, 1])
        # Plane x-2=0 (perpendicular to x)
        plane = Plane.from_coefficients(-4, 0, 0, 8)
        sep = plane.indices_separate(plist, 0.00001)
        assert sep[0] == [0, 1, 2, 3, 4]
        assert sep[1] == []
        assert sep[2] == [5, 6, 7]
        sep = plane.indices_separate(plist, 1)
        assert sep[0] == [0, 1, 2, 4]
        assert sep[1] == [3]
        assert sep[2] == [5, 6, 7]
        # Plane 2y+1=0 (perpendicular to y)
        plane = Plane.from_coefficients(0, 2, 0, 1)
        sep = plane.indices_separate(plist, 0.00001)
        assert sep[0] == [4]
        assert sep[1] == []
        assert sep[2] == [0, 1, 2, 3, 5, 6, 7]
        sep = plane.indices_separate(plist, 1)
        assert sep[0] == []
        assert sep[1] == [0, 1, 2, 3, 4, 7]
        assert sep[2] == [5, 6]
        # Plane 4z-3=0 (perpendicular to z)
        plane = Plane.from_coefficients(0, 0, -4, 3)
        sep = plane.indices_separate(plist, 0.00001)
        assert sep[0] == [0, 2, 3, 4, 5, 7]
        assert sep[1] == [1]
        assert sep[2] == [6]
        sep = plane.indices_separate(plist, 0.75)
        assert sep[0] == [5]
        assert sep[1] == [0, 1, 2, 3, 4, 7]
        assert sep[2] == [6]
        # Test with 3 coeff facets (Normal vector = [0, a, b] or [a, 0, b] or [a, b, 0])
        # Plane 2y-z+4=0
        plane = Plane.from_coefficients(0, 2, -1, 0)
        sep = plane.indices_separate(plist, 0.00001)
        assert sep[0] == [1, 4]
        assert sep[1] == [0, 2, 3, 7]
        assert sep[2] == [5, 6]
        sep = plane.indices_separate(plist, 0.75)
        assert sep[0] == [4]
        assert sep[1] == [0, 1, 2, 3, 7]
        assert sep[2] == [5, 6]
        # Plane 2y-z+4=0
        plane = Plane.from_coefficients(4, 0, -2, -20)
        sep = plane.indices_separate(plist, 0.00001)
        assert sep[0] == [0, 1, 2, 3, 4]
        assert sep[1] == [6]
        assert sep[2] == [5, 7]
        # Plane 2y-z+4=0
        plane = Plane.from_coefficients(-2, 9, 0, 2)
        sep = plane.indices_separate(plist, 0.00001)
        assert sep[0] == [0, 1, 2, 6]
        assert sep[1] == [3, 5]
        assert sep[2] == [4, 7]

    def test_distances(self):
        # Test with the common test plane
        point_1 = np.array([0, 0, 0], float)
        point_2 = np.array([0, 0, 0.75], float)
        point_3 = np.array([-0.75, 0, 0], float)
        point_4 = np.array([1, 0, 0], float)
        point_5 = np.array([0, -1.5, 0], float)
        point_6 = np.array([10, 2, -20], float)
        point_7 = np.array([10, 10, 10], float)
        point_8 = np.array([100, 0, 0], float)
        plist = [point_1, point_2, point_4, point_6, point_7, point_8]
        distances, indices_sorted = self.plane.distances_indices_sorted(plist)
        assert_allclose(
            distances,
            [
                0.5,
                0,
                1.16666666666666,
                21.1666666666666,
                3.8333333333333,
                67.1666666666666,
            ],
            atol=1e-9,
        )
        assert indices_sorted == [1, 0, 2, 4, 3, 5]
        # Plane 2y+1=0 (perpendicular to y)
        plane = Plane.from_coefficients(0, 2, 0, 1)
        plist = [point_1, point_5, point_6, point_7]
        distances, indices_sorted = plane.distances_indices_sorted(plist)
        assert_allclose(distances, [0.5, -1, 2.5, 10.5])
        assert indices_sorted == [0, 1, 2, 3]
        plist = [point_1, point_5, point_6, point_7]
        distances, indices_sorted = plane.distances_indices_sorted(plist)
        assert_allclose(distances, [0.5, -1, 2.5, 10.5])
        assert indices_sorted == [0, 1, 2, 3]
        distances, indices_sorted = plane.distances_indices_sorted(plist, sign=True)
        assert_allclose(distances, [0.5, -1, 2.5, 10.5])
        assert indices_sorted == [(0, 1), (1, -1), (2, 1), (3, 1)]
        plist = [point_5, point_1, point_6, point_7]
        distances, indices_sorted, groups = plane.distances_indices_groups(plist)
        assert_allclose(distances, [-1, 0.5, 2.5, 10.5])
        assert indices_sorted == [1, 0, 2, 3]
        assert groups == [[1, 0], [2], [3]]
        plist = [point_1, point_2, point_3, point_4, point_5, point_6, point_7, point_8]
        distances, indices_sorted = plane.distances_indices_sorted(plist)
        assert_allclose(distances, [0.5, 0.5, 0.5, 0.5, -1, 2.5, 10.5, 0.5])
        assert set(indices_sorted[:5]) == {0, 1, 2, 3, 7}
        # Plane z=0 (plane xy)
        plane = Plane.from_coefficients(0, 0, 1, 0)
        zzs = [0.1, -0.2, 0.7, -2.1, -1.85, 0, -0.71, -0.82, -6.5, 1.8]
        plist = []
        rng = np.random.default_rng()
        for zz in zzs:
            plist.append([rng.uniform(-20, 20), rng.uniform(-20, 20), zz])
        distances, indices_sorted, groups = plane.distances_indices_groups(points=plist, delta=0.25)
        assert indices_sorted == [5, 0, 1, 2, 6, 7, 9, 4, 3, 8]
        assert groups == [[5, 0, 1], [2, 6, 7], [9, 4, 3], [8]]
        assert_allclose(distances, zzs)
        distances, indices_sorted, groups = plane.distances_indices_groups(points=plist, delta_factor=0.1)
        assert indices_sorted == [5, 0, 1, 2, 6, 7, 9, 4, 3, 8]
        assert groups == [[5, 0, 1, 2, 6, 7], [9, 4, 3], [8]]
        assert_allclose(distances, zzs)
        distances, indices_sorted, groups = plane.distances_indices_groups(points=plist, delta_factor=0.1, sign=True)
        assert indices_sorted == [
            (5, 0),
            (0, 1),
            (1, -1),
            (2, 1),
            (6, -1),
            (7, -1),
            (9, 1),
            (4, -1),
            (3, -1),
            (8, -1),
        ]
        assert groups == [
            [(5, 0), (0, 1), (1, -1), (2, 1), (6, -1), (7, -1)],
            [(9, 1), (4, -1), (3, -1)],
            [(8, -1)],
        ]
        assert_allclose(distances, zzs)

    def test_projections(self):
        # Projections of points that are already on the plane
        expected_projected_points = [
            self.p1,
            self.p2,
            self.p3,
            self.plane.p1,
            self.plane.p2,
            self.plane.p3,
        ]
        projected_points = self.plane.projectionpoints(expected_projected_points)
        projected_2d = self.plane.project_and_to2dim(expected_projected_points, "mean")
        for ii, pp in enumerate(expected_projected_points):
            assert_allclose(pp, projected_points[ii], atol=1e-9)
        for i1, i2 in itertools.combinations(list(range(len(expected_projected_points))), 2):
            assert np.isclose(
                np.linalg.norm(expected_projected_points[i1] - expected_projected_points[i2]),
                np.linalg.norm(projected_2d[i1] - projected_2d[i2]),
            )
        # Projections of random points (check on distances between the 3D points and the 2D points)
        points_to_project = [
            np.array([5.1, 0.3, -2.3]),
            np.array([-2, 4.3, -6.3]),
            np.array([3.1, 2.3, -21.3]),
            np.array([-2, -0.5, 0.05]),
            np.array([11, 12, -13]),
            np.array([10, 8.3, -6.32]),
        ]
        projected_points = self.plane.projectionpoints(points_to_project)
        mean_point = np.array([np.mean([pp[ii] for pp in points_to_project]) for ii in range(3)])
        projected_2d = self.plane.project_and_to2dim(points_to_project, "mean")
        projected_2d_bis = self.plane.project_and_to2dim(points_to_project, mean_point)
        for ii, pp in enumerate(projected_2d):
            assert_allclose(pp, projected_2d_bis[ii])
        for i1, i2 in itertools.combinations(list(range(len(projected_points))), 2):
            assert np.isclose(
                np.linalg.norm(projected_points[i1] - projected_points[i2]),
                np.linalg.norm(projected_2d[i1] - projected_2d[i2]),
            )
        for pp in points_to_project:
            projected_2d = self.plane.project_and_to2dim([pp], pp)
            assert_allclose(projected_2d[0], 0)
        # Check some specific projections
        points = [
            np.zeros(3, float),
            np.array([10, 10, 10], float),
            np.array([1.2, 2.3, 3.4], float),
            np.array([-1, -2, -3], float),
            np.array([-1, 1, -1], float),
        ]
        projected_points = self.plane.projectionpoints(points)
        expected_projected_points = [
            np.array([-0.33333333, -0.16666667, 0.33333333]),
            np.array([7.44444444, 8.72222222, 12.55555556]),
            np.array([1.33333333, 2.36666667, 3.26666667]),
            np.array([-1.77777778, -2.38888889, -2.22222222]),
            np.array([-1.55555556, 0.72222222, -0.44444444]),
        ]
        for ii, pp in enumerate(projected_points):
            assert_allclose(pp, expected_projected_points[ii])
            assert self.plane.is_in_plane(pp, 0.0000001)
        projected_2d_points_000 = self.plane.project_and_to2dim(points, [0, 0, 0])
        projected_2d_points_mean = self.plane.project_and_to2dim(points, "mean")
        for i1, i2 in itertools.combinations(list(range(len(projected_2d_points_000))), 2):
            norm_000 = np.linalg.norm(projected_2d_points_000[i1] - projected_2d_points_000[i2])
            norm_mean = np.linalg.norm(projected_2d_points_mean[i1] - projected_2d_points_mean[i2])
            norm_xyz_projected = np.linalg.norm(projected_points[i1] - projected_points[i2])
            assert np.isclose(norm_000, norm_mean)
            assert np.isclose(norm_000, norm_xyz_projected)
