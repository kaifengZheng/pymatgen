from __future__ import annotations

import numpy as np
import pytest
from pytest import approx

from pymatgen.core.structure import Molecule, Structure
from pymatgen.io.cp2k.sets import SETTINGS, Cp2kValidationError, DftSet, GaussianTypeOrbitalBasisSet, GthPotential
from pymatgen.util.testing import TEST_FILES_DIR, MatSciTest

CP2K_TEST_DIR = f"{TEST_FILES_DIR}/io/cp2k"

Si_structure = Structure(
    lattice=[[0, 2.734364, 2.734364], [2.734364, 0, 2.734364], [2.734364, 2.734364, 0]],
    species=["Si", "Si"],
    coords=[[0, 0, 0], [0.25, 0.25, 0.25]],
)
molecule = Molecule(species=["Si"], coords=[[0, 0, 0]])

# Basis set / potential with objects
Si_gto_basis = """
Si SZV-MOLOPT-GTH SZV-MOLOPT-GTH-q4
1
2 0 1 6 1 1
    2.693604434572  0.015333179500 -0.005800105400
    1.359613855428 -0.283798205000 -0.059172026000
    0.513245176029 -0.228939692700  0.121487149900
    0.326563011394  0.728834000900  0.423382421100
    0.139986977410  0.446205299300  0.474592116300
    0.068212286977  0.122025292800  0.250129397700
"""
Si_gth_pot = """Si GTH-BLYP-q4 GTH-BLYP
2    2
0.44000000    1    -6.25958674
2
0.44465247    2     8.31460936    -2.33277947
                                    3.01160535
0.50279207    1     2.33241791"""

BASIS_AND_POTENTIAL: dict[str, dict[str, GaussianTypeOrbitalBasisSet | GthPotential]] = {
    "Si": {"basis": GaussianTypeOrbitalBasisSet.from_str(Si_gto_basis), "potential": GthPotential.from_str(Si_gth_pot)},
    "Fe": {
        "basis": GaussianTypeOrbitalBasisSet.from_str(Si_gto_basis.replace("Si", "Fe")),
        "potential": GthPotential.from_str(Si_gth_pot.replace("Si", "Fe")),
    },
}


class TestDftSet(MatSciTest):
    def test_dft_set(self) -> None:
        """Test various DFT set configurations."""
        SETTINGS["PMG_CP2K_DATA_DIR"] = CP2K_TEST_DIR

        # Basis sets / potentials searching
        basis_and_potential: dict[str, str | None | dict[str, str | None]] = {
            "basis_type": "SZV",
            "potential_type": "Pseudopotential",
            "functional": None,
        }
        dft_set = DftSet(Si_structure, basis_and_potential=basis_and_potential, xc_functionals="PBE")

        # Basis sets / potentials by name
        basis_and_potential = {"Si": {"basis": "SZV-GTH-q4", "potential": "GTH-PBE-q4"}}
        dft_set = DftSet(Si_structure, basis_and_potential=basis_and_potential, xc_functionals="PBE")

        # Basis sets / potentials by name with ADMM
        basis_and_potential = {
            "Si": {
                "basis": "SZV-GTH-q4",
                "potential": "GTH-PBE-q4",
                "aux_basis": "cFIT3",
            }
        }
        dft_set = DftSet(Si_structure, basis_and_potential=basis_and_potential, xc_functionals="PBE")
        basis_sets = dft_set["force_eval"]["subsys"]["Si_1"].get("basis_set")
        assert any("AUX_FIT" in b.values for b in basis_sets)
        assert any("cFIT3" in b.values for b in basis_sets)

        # Basis sets / potentials by hash value
        basis_and_potential = {
            "Si": {
                "basis": "30767c18f6e7e46c1b56c1d34ff6007d",
                "potential": "21e2f468a18404ff6119fe801da81e43",
            }
        }
        dft_set = DftSet(Si_structure, basis_and_potential=basis_and_potential, xc_functionals="PBE")

        set_kwargs = dict.fromkeys(("print_pdos", "print_dos", "print_v_hartree", "print_e_density"), False)
        dft_set = DftSet(
            Si_structure,
            basis_and_potential=BASIS_AND_POTENTIAL,
            xc_functionals="PBE",
            **set_kwargs,
        )
        assert dft_set.cutoff == approx(150)

        # Test that printing will activate sections
        assert not dft_set.check("motion")
        dft_set.activate_motion()
        assert dft_set.check("motion")
        assert not dft_set.check("force_eval/dft/print/pdos")
        dft_set.print_pdos()
        assert dft_set.check("force_eval/dft/print/pdos")
        assert not dft_set.check("force_eval/dft/print/v_hartree_cube")
        dft_set.print_v_hartree()
        assert dft_set.check("force_eval/dft/print/v_hartree_cube")

        # Test property activators
        assert not dft_set.check("force_eval/properties")
        dft_set.activate_nmr()
        dft_set.activate_epr()
        dft_set.activate_hyperfine()
        dft_set.activate_polar()
        dft_set.activate_tddfpt()
        assert dft_set.check("force_eval/properties/linres/localize")
        assert dft_set.check("force_eval/properties/linres/nmr/print/chi_tensor")
        assert dft_set.check("force_eval/properties/linres/epr/print/g_tensor")
        assert dft_set.check("force_eval/properties/tddfpt")
        assert dft_set.check("force_eval/dft/print/hyperfine_coupling_tensor")

        # For at least up to v2022.1, DOS doesn't work without kpoints
        assert not dft_set.check("force_eval/dft/print/dos")
        dft_set.print_dos()
        assert not dft_set.check("force_eval/dft/print/dos")

        assert not dft_set.check("force_eval/dft/xc/hf")
        dft_set.activate_hybrid()
        assert dft_set.check("force_eval/dft/xc/hf")
        assert dft_set.check("force_eval/dft/auxiliary_density_matrix_method")

        # Validator will trip for kpoints + hfx
        dft_set |= {"force_eval": {"dft": {"kpoints": {}}}}
        with pytest.raises(
            Cp2kValidationError,
            match="CP2K v2022.1: Does not support hartree fock with kpoints",
        ):
            dft_set.validate()

        # Test non-periodic settings
        dft_set = DftSet(molecule, basis_and_potential=basis_and_potential, xc_functionals="PBE")
        assert dft_set.check("force_eval/dft/poisson")
        assert dft_set["force_eval"]["dft"]["poisson"].get("periodic").values[0].upper() == "NONE"

    def test_kind_magnetization(self) -> None:
        """Test different ways of setting kind (i.e. element-specific) initial magnetization."""
        fe_structure = Structure(
            lattice=np.eye(3) * 3,
            species=["Fe", "Fe"],
            coords=[[0, 0, 0], [0.5, 0.5, 0.5]],
        )

        # Test 1: Setting via site properties
        dft_set = DftSet(
            fe_structure.copy().add_site_property("magmom", [2.0, -2.0]),
            basis_and_potential=BASIS_AND_POTENTIAL,
            xc_functionals="PBE",
        )
        fe1_kind = dft_set["force_eval"]["subsys"]["Fe_1"]
        fe2_kind = dft_set["force_eval"]["subsys"]["Fe_2"]
        assert {fe1_kind["magnetization"].values[0], fe2_kind["magnetization"].values[0]} == {2.0, -2.0}

        # Test 2: Setting via element defaults
        element_defaults = {"Fe": {"magnetization": 4.0}}
        dft_set = DftSet(
            fe_structure,
            basis_and_potential=BASIS_AND_POTENTIAL,
            xc_functionals="PBE",
            element_defaults=element_defaults,
        )
        fe_kind = dft_set["force_eval"]["subsys"]["Fe_1"]
        assert fe_kind["magnetization"].values[0] == 4.0

        # Test 3: Site properties take precedence over element defaults
        fe_structure.add_site_property("magmom", [2.0, -2.0])
        dft_set = DftSet(
            fe_structure,
            basis_and_potential=BASIS_AND_POTENTIAL,
            xc_functionals="PBE",
            element_defaults=element_defaults,
        )
        fe1_kind = dft_set["force_eval"]["subsys"]["Fe_1"]
        fe2_kind = dft_set["force_eval"]["subsys"]["Fe_2"]
        assert {fe1_kind["magnetization"].values[0], fe2_kind["magnetization"].values[0]} == {2.0, -2.0}

    def test_cell_parameters(self) -> None:
        """Test that cell parameters are properly set when provided."""
        # Test with cell parameters
        cell_params = {
            "SYMMETRY": "CUBIC",
            "MULTIPLE_UNIT_CELL": [2, 2, 2],
        }

        dft_set = DftSet(Si_structure, basis_and_potential=BASIS_AND_POTENTIAL, xc_functionals="PBE", cell=cell_params)

        # Check that cell parameters were properly set
        subsys = dft_set["force_eval"]["subsys"]
        assert subsys.check("cell")
        cell_section = subsys["cell"]
        assert cell_section["symmetry"].values[0] == "CUBIC"
        assert cell_section["multiple_unit_cell"].values == ([2, 2, 2],)

        # Test without cell parameters (default behavior)
        dft_set = DftSet(Si_structure, basis_and_potential=BASIS_AND_POTENTIAL, xc_functionals="PBE")

        # Check that only default cell parameters exist
        subsys = dft_set["force_eval"]["subsys"]
        assert subsys.check("cell")
        cell_section = subsys["cell"]
        assert not cell_section.check("symmetry")
        assert not cell_section.check("multiple_unit_cell")
