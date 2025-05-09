from __future__ import annotations

from shutil import which

import pytest
from monty.serialization import loadfn
from numpy.testing import assert_allclose
from pytest import approx

from pymatgen.analysis.magnetism import (
    CollinearMagneticStructureAnalyzer,
    MagneticStructureEnumerator,
    Ordering,
    magnetic_deformation,
)
from pymatgen.core import Element, Lattice, Species, Structure
from pymatgen.util.testing import TEST_FILES_DIR

TEST_DIR = f"{TEST_FILES_DIR}/analysis/magnetic_orderings"

ENUM_CMD = which("enum.x") or which("multienum.x")
MAKESTR_CMD = which("makestr.x") or which("makeStr.x") or which("makeStr.py")
ENUMLIB_PRESENT = ENUM_CMD and MAKESTR_CMD


class TestCollinearMagneticStructureAnalyzer:
    def setup_method(self):
        self.Fe = Structure.from_file(f"{TEST_FILES_DIR}/cif/Fe.cif", primitive=True)

        self.LiFePO4 = Structure.from_file(f"{TEST_FILES_DIR}/cif/LiFePO4.cif", primitive=True)

        self.Fe3O4 = Structure.from_file(f"{TEST_FILES_DIR}/cif/Fe3O4.cif", primitive=True)

        self.GdB4 = Structure.from_file(
            f"{TEST_FILES_DIR}/io/cif/mcif/magnetic.ncl.example.GdB4.mcif",
            primitive=True,
        )

        self.NiO_expt = Structure.from_file(f"{TEST_FILES_DIR}/io/cif/mcif/magnetic.example.NiO.mcif", primitive=True)

        # CuO.mcif sourced from https://www.cryst.ehu.es/magndata/index.php?index=1.62
        # doi: 10.1088/0022-3719/21/15/023
        self.CuO_expt = Structure.from_file(
            f"{TEST_FILES_DIR}/io/cif/mcif/magnetic.example.CuO.mcif.gz", primitive=True
        )

        lattice = Lattice.cubic(4.17)
        species = ["Ni", "O"]
        coords = [[0, 0, 0], [0.5, 0.5, 0.5]]
        self.NiO = Structure.from_spacegroup(225, lattice, species, coords)

        lattice = Lattice([[2.085, 2.085, 0.0], [0.0, -2.085, -2.085], [-2.085, 2.085, -4.17]])
        species = ["Ni", "Ni", "O", "O"]
        coords = [[0.5, 0, 0.5], [0, 0, 0], [0.25, 0.5, 0.25], [0.75, 0.5, 0.75]]
        self.NiO_AFM_111 = Structure(lattice, species, coords, site_properties={"magmom": [-5, 5, 0, 0]})

        lattice = Lattice([[2.085, 2.085, 0], [0, 0, -4.17], [-2.085, 2.085, 0]])
        species = ["Ni", "Ni", "O", "O"]
        coords = [[0.5, 0.5, 0.5], [0, 0, 0], [0, 0.5, 0], [0.5, 0, 0.5]]
        self.NiO_AFM_001 = Structure(lattice, species, coords, site_properties={"magmom": [-5, 5, 0, 0]})

        lattice = Lattice([[2.085, 2.085, 0], [0, 0, -4.17], [-2.085, 2.085, 0]])
        species = ["Ni", "Ni", "O", "O"]
        coords = [[0.5, 0.5, 0.5], [0, 0, 0], [0, 0.5, 0], [0.5, 0, 0.5]]
        self.NiO_AFM_001_opposite = Structure(lattice, species, coords, site_properties={"magmom": [5, -5, 0, 0]})

        lattice = Lattice([[2.085, 2.085, 0], [0, 0, -4.17], [-2.085, 2.085, 0]])
        species = ["Ni", "Ni", "O", "O"]
        coords = [[0.5, 0.5, 0.5], [0, 0, 0], [0, 0.5, 0], [0.5, 0, 0.5]]
        self.NiO_unphysical = Structure(lattice, species, coords, site_properties={"magmom": [-3, 0, 0, 0]})

    def test_get_representations(self):
        # tests to convert between storing magnetic moment information
        # on site_properties or on Species 'spin' property

        # test we store magnetic moments on site properties
        self.Fe.add_site_property("magmom", [5])
        msa = CollinearMagneticStructureAnalyzer(self.Fe)
        assert msa.structure.site_properties["magmom"][0] == 5

        # and that we can retrieve a spin representation
        Fe_spin = msa.get_structure_with_spin()
        assert "magmom" not in Fe_spin.site_properties
        assert Fe_spin[0].specie.spin == 5

        # test we can remove magnetic moment information
        msa.get_nonmagnetic_structure()
        assert "magmom" not in Fe_spin.site_properties

        # test with disorder on magnetic site
        self.Fe[0] = {Species("Fe", 0, spin=5): 0.5, "Ni": 0.5}
        with pytest.raises(
            NotImplementedError,
            match="CollinearMagneticStructureAnalyzer not implemented for disordered structures,"
            " make ordered approximation first.",
        ):
            CollinearMagneticStructureAnalyzer(self.Fe)

    def test_matches(self):
        assert self.NiO.matches(self.NiO_AFM_111)
        assert self.NiO.matches(self.NiO_AFM_001)

        # MSA adds magmoms to Structure, so not equal
        msa = CollinearMagneticStructureAnalyzer(self.NiO, overwrite_magmom_mode="replace_all")
        assert not msa.matches_ordering(self.NiO)
        assert not msa.matches_ordering(self.NiO_AFM_111)
        assert not msa.matches_ordering(self.NiO_AFM_001)

        msa = CollinearMagneticStructureAnalyzer(self.NiO_AFM_001, overwrite_magmom_mode="respect_sign")
        assert not msa.matches_ordering(self.NiO)
        assert not msa.matches_ordering(self.NiO_AFM_111)
        assert msa.matches_ordering(self.NiO_AFM_001)
        assert msa.matches_ordering(self.NiO_AFM_001_opposite)

        msa = CollinearMagneticStructureAnalyzer(self.NiO_AFM_111, overwrite_magmom_mode="respect_sign")
        assert not msa.matches_ordering(self.NiO)
        assert msa.matches_ordering(self.NiO_AFM_111)
        assert not msa.matches_ordering(self.NiO_AFM_001)
        assert not msa.matches_ordering(self.NiO_AFM_001_opposite)

    def test_modes(self):
        mode = "none"
        msa = CollinearMagneticStructureAnalyzer(self.NiO, overwrite_magmom_mode=mode)
        magmoms = msa.structure.site_properties["magmom"]
        assert magmoms == [0, 0]

        mode = "respect_sign"
        msa = CollinearMagneticStructureAnalyzer(self.NiO_unphysical, overwrite_magmom_mode=mode)
        magmoms = msa.structure.site_properties["magmom"]
        assert magmoms == [-5, 0, 0, 0]

        mode = "respect_zeros"
        msa = CollinearMagneticStructureAnalyzer(self.NiO_unphysical, overwrite_magmom_mode=mode)
        magmoms = msa.structure.site_properties["magmom"]
        assert magmoms == [5, 0, 0, 0]

        mode = "replace_all"
        msa = CollinearMagneticStructureAnalyzer(self.NiO_unphysical, overwrite_magmom_mode=mode, make_primitive=False)
        magmoms = msa.structure.site_properties["magmom"]
        assert magmoms == [5, 5, 0, 0]

        mode = "replace_all_if_undefined"
        msa = CollinearMagneticStructureAnalyzer(self.NiO, overwrite_magmom_mode=mode)
        magmoms = msa.structure.site_properties["magmom"]
        assert magmoms == [5, 0]

        mode = "normalize"
        msa = CollinearMagneticStructureAnalyzer(msa.structure, overwrite_magmom_mode="normalize")
        magmoms = msa.structure.site_properties["magmom"]
        assert magmoms == [1, 0]

        # test invalid overwrite_magmom_mode
        with pytest.raises(ValueError, match="'invalid_mode' is not a valid OverwriteMagmomMode"):
            CollinearMagneticStructureAnalyzer(self.NiO, overwrite_magmom_mode="invalid_mode")

    def test_net_positive(self):
        msa = CollinearMagneticStructureAnalyzer(self.NiO_unphysical)
        magmoms = msa.structure.site_properties["magmom"]
        assert magmoms == [3, 0, 0, 0]

    def test_get_ferromagnetic_structure(self):
        msa = CollinearMagneticStructureAnalyzer(self.NiO, overwrite_magmom_mode="replace_all_if_undefined")
        s1 = msa.get_ferromagnetic_structure()
        s1_magmoms = [float(m) for m in s1.site_properties["magmom"]]
        s1_magmoms_ref = [5.0, 0.0]
        assert s1_magmoms == s1_magmoms_ref

        _ = CollinearMagneticStructureAnalyzer(self.NiO_AFM_111, overwrite_magmom_mode="replace_all_if_undefined")
        s2 = msa.get_ferromagnetic_structure(make_primitive=False)
        s2_magmoms = [float(m) for m in s2.site_properties["magmom"]]
        s2_magmoms_ref = [5.0, 0.0]
        assert s2_magmoms == s2_magmoms_ref

        s2_prim = msa.get_ferromagnetic_structure(make_primitive=True)
        assert CollinearMagneticStructureAnalyzer(s1).matches_ordering(s2_prim)

    def test_magnetic_properties(self):
        mag_struct_analyzer = CollinearMagneticStructureAnalyzer(self.GdB4)
        assert not mag_struct_analyzer.is_collinear

        mag_struct_analyzer = CollinearMagneticStructureAnalyzer(self.Fe)
        assert not mag_struct_analyzer.is_magnetic

        self.Fe.add_site_property("magmom", [5])

        mag_struct_analyzer = CollinearMagneticStructureAnalyzer(self.Fe)
        assert mag_struct_analyzer.is_magnetic
        assert mag_struct_analyzer.is_collinear
        assert mag_struct_analyzer.ordering == Ordering.FM

        mag_struct_analyzer = CollinearMagneticStructureAnalyzer(
            self.NiO,
            make_primitive=False,
            overwrite_magmom_mode="replace_all_if_undefined",
        )
        assert mag_struct_analyzer.number_of_magnetic_sites == 4
        assert mag_struct_analyzer.number_of_unique_magnetic_sites() == 1
        assert mag_struct_analyzer.types_of_magnetic_species == (Element.Ni,)
        assert mag_struct_analyzer.get_exchange_group_info() == ("Fm-3m", 225)

        # https://github.com/materialsproject/pymatgen/pull/3574
        for threshold, expected in [(1e-8, Ordering.AFM), (1e-20, Ordering.FiM)]:
            mag_struct_analyzer = CollinearMagneticStructureAnalyzer(self.CuO_expt, threshold_ordering=threshold)
            assert mag_struct_analyzer.ordering == expected

    def test_str(self):
        msa = CollinearMagneticStructureAnalyzer(self.NiO_AFM_001)

        ref_msa_str = """Structure Summary
Lattice
    abc : 2.948635277547903 4.17 2.948635277547903
 angles : 90.0 90.0 90.0
 volume : 36.2558565
      A : 2.085 2.085 0.0
      B : 0.0 0.0 -4.17
      C : -2.085 2.085 0.0
Magmoms Sites
+5.00   PeriodicSite: Ni (0.0, 0.0, 0.0) [0.0, 0.0, 0.0]
        PeriodicSite: O (0.0, 0.0, -2.085) [0.0, 0.5, 0.0]
        PeriodicSite: O (0.0, 2.085, 0.0) [0.5, 0.0, 0.5]
-5.00   PeriodicSite: Ni (0.0, 2.085, -2.085) [0.5, 0.5, 0.5]"""

        # just compare lines form 'Magmoms Sites',
        # since lattice param string can vary based on machine precision
        assert "\n".join(str(msa).split("\n")[-5:-1]) == "\n".join(ref_msa_str.split("\n")[-5:-1])

    def test_round_magmoms(self):
        struct = self.NiO_AFM_001.copy()
        struct.add_site_property("magmom", [-5.0143, -5.02, 0.147, 0.146])

        msa = CollinearMagneticStructureAnalyzer(struct, round_magmoms=0.001, make_primitive=False)
        assert_allclose(msa.magmoms, [5.0171, 5.0171, -0.1465, -0.1465])
        assert msa.magnetic_species_and_magmoms["Ni"] == approx(5.0171)
        assert msa.magnetic_species_and_magmoms["O"] == approx(0.1465)

        struct.add_site_property("magmom", [-5.0143, 4.5, 0.147, 0.146])
        msa = CollinearMagneticStructureAnalyzer(struct, round_magmoms=0.001, make_primitive=False)
        assert_allclose(msa.magmoms, [5.0143, -4.5, -0.1465, -0.1465])
        assert msa.magnetic_species_and_magmoms["Ni"][0] == approx(4.5)
        assert msa.magnetic_species_and_magmoms["Ni"][1] == approx(5.0143)
        assert msa.magnetic_species_and_magmoms["O"] == approx(0.1465)

    def test_missing_spin(self):
        # This test catches the case where a structure has some species with
        # Species.spin=None. This previously raised an error upon construction
        # of the analyzer).
        lattice = Lattice([[2.085, 2.085, 0.0], [0.0, -2.085, -2.085], [-2.085, 2.085, -4.17]])
        species = [
            Species("Ni", spin=-5),
            Species("Ni", spin=5),
            Species("O", spin=None),
            Species("O", spin=None),
        ]
        coords = [[0.5, 0, 0.5], [0, 0, 0], [0.25, 0.5, 0.25], [0.75, 0.5, 0.75]]
        struct = Structure(lattice, species, coords)

        msa = CollinearMagneticStructureAnalyzer(struct, round_magmoms=0.001, make_primitive=False)
        assert msa.structure.site_properties["magmom"] == [-5, 5, 0, 0]


@pytest.mark.skipif(not ENUMLIB_PRESENT, reason="enumlib not present")
class TestMagneticStructureEnumerator:
    def test_ordering_enumeration(self):
        # simple AFM
        structure = Structure.from_file(f"{TEST_DIR}/LaMnO3.json")
        enumerator = MagneticStructureEnumerator(structure)
        assert enumerator.input_origin == "afm"

        # ferrimagnetic (Cr produces net spin)
        structure = Structure.from_file(f"{TEST_DIR}/Cr2NiO4.json")
        enumerator = MagneticStructureEnumerator(structure)
        assert enumerator.input_origin == "ferri_by_Cr"

        # antiferromagnetic on single magnetic site
        structure = Structure.from_file(f"{TEST_DIR}/Cr2WO6.json")
        enumerator = MagneticStructureEnumerator(structure)
        assert enumerator.input_origin == "afm_by_Cr"

        # AFM requiring large cell size
        # (enable for further development of workflow, too slow for CI)

        # structure = Structure.from_file(f"{ref_dir}/CuO.json")
        # enumerator = MagneticOrderingsenumerator(
        #     structure, default_magmoms={"Cu": 1.73}, transformation_kwargs={"max_cell_size": 4}
        # )
        # assert enumerator.input_origin == "afm"

        # antiferromagnetic by structural motif
        structure = Structure.from_file(f"{TEST_DIR}/Ca3Co2O6.json")
        enumerator = MagneticStructureEnumerator(
            structure,
            strategies=("antiferromagnetic_by_motif",),
            # this example just misses default cut-off, so do not truncate
            truncate_by_symmetry=False,
            transformation_kwargs={"max_cell_size": 2},
        )
        assert enumerator.input_origin == "afm_by_motif_2a"

    def test_default_transformation_kwargs(self):
        structure = Structure.from_file(f"{TEST_DIR}/LaMnO3.json")

        # Make sure user input would not be overwritten by default values
        transformation_kwargs = {"timeout": 10, "check_ordered_symmetry": True}
        enumerator = MagneticStructureEnumerator(structure, transformation_kwargs=transformation_kwargs)
        assert enumerator.transformation_kwargs["timeout"] == 10
        assert enumerator.transformation_kwargs["check_ordered_symmetry"] is True

        enumerator = MagneticStructureEnumerator(structure, transformation_kwargs=None)
        assert enumerator.transformation_kwargs["timeout"] == 5
        assert enumerator.transformation_kwargs["check_ordered_symmetry"] is False


class TestMagneticDeformation:
    def test_magnetic_deformation(self):
        test_structs = loadfn(f"{TEST_FILES_DIR}/analysis/magnetism/magnetic_deformation.json")
        mag_def = magnetic_deformation(test_structs[0], test_structs[1])

        assert mag_def.type == "NM-FM"
        assert mag_def.deformation == approx(5.0130859485170971)
