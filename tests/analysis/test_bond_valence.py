from __future__ import annotations

import pytest
from pytest import approx

from pymatgen.analysis.bond_valence import BVAnalyzer, calculate_bv_sum, calculate_bv_sum_unordered
from pymatgen.core import Composition, Species, Structure
from pymatgen.util.testing import TEST_FILES_DIR, MatSciTest

TEST_DIR = f"{TEST_FILES_DIR}/analysis/bond_valence"


class TestBVAnalyzer(MatSciTest):
    def setup_method(self):
        self.analyzer = BVAnalyzer()

    def test_get_valences(self):
        struct = Structure.from_file(f"{TEST_DIR}/LiMn2O4.json")
        valences = [1, 1, 3, 3, 4, 4, -2, -2, -2, -2, -2, -2, -2, -2]
        assert self.analyzer.get_valences(struct) == valences
        struct = self.get_structure("LiFePO4")
        valences = [1] * 4 + [2] * 4 + [5] * 4 + [-2] * 16
        assert self.analyzer.get_valences(struct) == valences
        struct = self.get_structure("Li3V2(PO4)3")
        valences = [1] * 6 + [3] * 4 + [5] * 6 + [-2] * 24
        assert self.analyzer.get_valences(struct) == valences
        struct = Structure.from_file(f"{TEST_DIR}/Li4Fe3Mn1(PO4)4.json")
        valences = [1] * 4 + [2] * 4 + [5] * 4 + [-2] * 16
        assert self.analyzer.get_valences(struct) == valences
        struct = self.get_structure("NaFePO4")
        assert self.analyzer.get_valences(struct) == valences

        # trigger ValueError Structure contains elements not in set of BV parameters
        with pytest.raises(
            ValueError,
            match="Structure contains elements not in set of BV parameters: {Element Xe}",
        ):
            self.analyzer.get_valences(self.get_structure("Li10GeP2S12").replace_species({"Li": "Xe"}, in_place=False))

    def test_get_oxi_state_structure(self):
        struct = Structure.from_file(f"{TEST_DIR}/LiMn2O4.json")
        oxi_struct = self.analyzer.get_oxi_state_decorated_structure(struct)
        assert Species("Mn3+") in oxi_struct.composition.elements
        assert Species("Mn4+") in oxi_struct.composition.elements


class TestBondValenceSum(MatSciTest):
    def test_calculate_bv_sum(self):
        struct = Structure.from_file(f"{TEST_DIR}/LiMn2O4.json")
        neighbors = struct.get_neighbors(struct[0], 3.0)
        bv_sum = calculate_bv_sum(struct[0], neighbors)
        assert bv_sum == approx(0.7723402182087497)

    def test_calculate_bv_sum_unordered(self):
        struct = Structure.from_file(f"{TEST_DIR}/LiMn2O4.json")
        struct[0].species = Composition("Li0.5Na0.5")
        neighbors = struct.get_neighbors(struct[0], 3.0)
        bv_sum = calculate_bv_sum_unordered(struct[0], neighbors)
        assert bv_sum == approx(1.5494662306918852)
