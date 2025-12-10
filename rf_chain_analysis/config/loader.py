"""
RF Chain Configuration Loader

Loads and validates YAML configuration for RF chain analysis.
Matches MATLAB rf_chain_config_example.m structure.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from enum import Enum
import yaml
import math


# =============================================================================
# ENUMS
# =============================================================================

class ComponentType(Enum):
    """Types of RF chain components."""
    CABLE = "cable"
    AMPLIFIER = "amplifier"
    ATTENUATOR = "attenuator"
    ANTENNA = "antenna"


class ChainType(Enum):
    """Type of RF chain."""
    RECEIVE = "receive"
    TRANSMIT = "transmit"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _to_float(value, default: float = 0.0) -> float:
    """Convert value to float, handling strings with scientific notation."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _to_int(value, default: int = 0) -> int:
    """Convert value to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CableComponent:
    """Cable component with frequency-dependent loss."""
    id: str
    name: str
    order: int
    loss_point1_ghz: float  # First calibration point frequency
    loss_point1_db: float   # Loss at first point
    loss_point2_ghz: float  # Second calibration point frequency
    loss_point2_db: float   # Loss at second point
    type: ComponentType = ComponentType.CABLE

    def get_loss_at_freq(self, freq_ghz: float) -> float:
        """
        Calculate cable loss at frequency using sqrt(f) model.

        Loss = k * sqrt(f) where k is derived from two calibration points.
        """
        # Two equations: loss1 = k*sqrt(f1), loss2 = k*sqrt(f2)
        # Average the two k values for robustness
        k1 = self.loss_point1_db / math.sqrt(self.loss_point1_ghz) if self.loss_point1_ghz > 0 else 0
        k2 = self.loss_point2_db / math.sqrt(self.loss_point2_ghz) if self.loss_point2_ghz > 0 else 0
        k = (k1 + k2) / 2
        return k * math.sqrt(freq_ghz)

    def get_gain_at_freq(self, freq_ghz: float) -> float:
        """Get gain (negative loss) at frequency."""
        return -self.get_loss_at_freq(freq_ghz)

    def get_nf_at_freq(self, freq_ghz: float) -> float:
        """For passive devices, NF equals the loss in dB."""
        return self.get_loss_at_freq(freq_ghz)


@dataclass
class AmplifierComponent:
    """Amplifier component with flat gain and optional NF/Psat."""
    id: str
    name: str
    order: int
    gain_db: float
    noise_figure_db: Optional[float] = None  # None if not specified
    psat_dbm: Optional[float] = None         # Saturation power
    type: ComponentType = ComponentType.AMPLIFIER

    def get_gain_at_freq(self, freq_ghz: float) -> float:
        """Amplifiers have flat gain across frequency."""
        return self.gain_db

    def get_nf_at_freq(self, freq_ghz: float) -> Optional[float]:
        """Return noise figure (None if not specified)."""
        return self.noise_figure_db


@dataclass
class AttenuatorComponent:
    """Attenuator with linear frequency-dependent attenuation."""
    id: str
    name: str
    order: int
    atten_min_db: float  # Attenuation at min frequency
    atten_max_db: float  # Attenuation at max frequency
    type: ComponentType = ComponentType.ATTENUATOR

    def get_atten_at_freq(self, freq_ghz: float, freq_min: float, freq_max: float) -> float:
        """
        Calculate attenuation at frequency using linear interpolation.

        Attenuation varies linearly from atten_min_db at freq_min to
        atten_max_db at freq_max.
        """
        if freq_max == freq_min:
            return self.atten_min_db
        return self.atten_min_db + (self.atten_max_db - self.atten_min_db) * \
               (freq_ghz - freq_min) / (freq_max - freq_min)

    def get_gain_at_freq(self, freq_ghz: float, freq_min: float = 0.1, freq_max: float = 36.0) -> float:
        """Get gain (negative attenuation) at frequency."""
        return -self.get_atten_at_freq(freq_ghz, freq_min, freq_max)

    def get_nf_at_freq(self, freq_ghz: float, freq_min: float = 0.1, freq_max: float = 36.0) -> float:
        """For passive devices, NF equals the attenuation in dB."""
        return self.get_atten_at_freq(freq_ghz, freq_min, freq_max)


@dataclass
class AntennaComponent:
    """Antenna component with flat gain."""
    id: str
    name: str
    order: int
    gain_db: float  # Antenna gain in dBi
    type: ComponentType = ComponentType.ANTENNA

    def get_gain_at_freq(self, freq_ghz: float) -> float:
        """Antennas have flat gain across frequency."""
        return self.gain_db

    def get_nf_at_freq(self, freq_ghz: float) -> float:
        """Ideal antenna adds no noise."""
        return 0.0


# Union type for any component
Component = Union[CableComponent, AmplifierComponent, AttenuatorComponent, AntennaComponent]


@dataclass
class ChainConfig:
    """
    Complete RF chain configuration.

    Matches MATLAB rf_chain_config_example.m structure.
    """
    name: str
    description: str
    chain_type: ChainType
    freq_range_ghz: List[float]  # [min, max]
    components: Dict[str, Component]  # Component ID -> Component

    # TX-specific
    source_power_dbm: float = 0.0

    # RX-specific (for damage threshold analysis)
    input_power_range_dbm: Optional[List[float]] = None  # [min, max] sweep range
    damage_level_dbm: Optional[float] = None  # ADC damage threshold

    def get_components_ordered(self) -> List[Component]:
        """Get components sorted by order."""
        return sorted(self.components.values(), key=lambda c: c.order)

    def get_freq_min(self) -> float:
        """Get minimum frequency."""
        return self.freq_range_ghz[0]

    def get_freq_max(self) -> float:
        """Get maximum frequency."""
        return self.freq_range_ghz[1]

    @property
    def is_transmit(self) -> bool:
        """Check if this is a transmit chain."""
        return self.chain_type == ChainType.TRANSMIT

    @property
    def is_receive(self) -> bool:
        """Check if this is a receive chain."""
        return self.chain_type == ChainType.RECEIVE

    @property
    def has_damage_threshold(self) -> bool:
        """Check if RX damage threshold analysis is configured."""
        return (self.input_power_range_dbm is not None and
                self.damage_level_dbm is not None)

    def __str__(self) -> str:
        comp_list = ", ".join([c.name for c in self.get_components_ordered()])
        return (f"{self.name} ({self.chain_type.value})\n"
                f"  {self.description}\n"
                f"  Frequency: {self.freq_range_ghz[0]:.1f} - {self.freq_range_ghz[1]:.1f} GHz\n"
                f"  Components: {comp_list}")


# =============================================================================
# PARSING FUNCTIONS
# =============================================================================

def _parse_component(comp_id: str, data: dict) -> Component:
    """Parse a component from dict based on type."""
    comp_type = data.get('type', 'amplifier')
    name = data.get('name', comp_id)
    order = _to_int(data.get('order'), 0)

    if comp_type == 'cable':
        return CableComponent(
            id=comp_id,
            name=name,
            order=order,
            loss_point1_ghz=_to_float(data.get('loss_point1_ghz'), 1.0),
            loss_point1_db=_to_float(data.get('loss_point1_db'), 0.0),
            loss_point2_ghz=_to_float(data.get('loss_point2_ghz'), 18.0),
            loss_point2_db=_to_float(data.get('loss_point2_db'), 0.0)
        )

    elif comp_type == 'amplifier':
        nf = data.get('noise_figure_db')
        if nf is not None and nf != 'null':
            nf = _to_float(nf)
        else:
            nf = None

        psat = data.get('psat_dbm')
        if psat is not None and psat != 'null':
            psat = _to_float(psat)
        else:
            psat = None

        return AmplifierComponent(
            id=comp_id,
            name=name,
            order=order,
            gain_db=_to_float(data.get('gain_db'), 0.0),
            noise_figure_db=nf,
            psat_dbm=psat
        )

    elif comp_type == 'attenuator':
        return AttenuatorComponent(
            id=comp_id,
            name=name,
            order=order,
            atten_min_db=_to_float(data.get('atten_min_db'), 0.0),
            atten_max_db=_to_float(data.get('atten_max_db'), 0.0)
        )

    elif comp_type == 'antenna':
        return AntennaComponent(
            id=comp_id,
            name=name,
            order=order,
            gain_db=_to_float(data.get('gain_db'), 0.0)
        )

    else:
        raise ValueError(f"Unknown component type: {comp_type}")


def load_chain_config(filepath: Union[str, Path] = None) -> ChainConfig:
    """
    Load RF chain configuration from YAML file.

    Matches MATLAB rf_chain_config_example.m format.

    Args:
        filepath: Path to config YAML. If None, uses default location.

    Returns:
        ChainConfig object with chain definition.
    """
    if filepath is None:
        config_dir = Path(__file__).parent
        filepath = config_dir / "rf_chain_config.yaml"

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(filepath, 'r') as f:
        data = yaml.safe_load(f) or {}

    # Parse chain settings
    chain_data = data.get('chain', {})

    # Chain type
    chain_type_str = chain_data.get('type', 'receive')
    chain_type = ChainType(chain_type_str)

    # Frequency range
    freq_range = chain_data.get('freq_range_ghz', [2.0, 18.0])
    if isinstance(freq_range, list):
        freq_range = [_to_float(f) for f in freq_range]
    else:
        freq_range = [2.0, 18.0]

    # Parse components
    components = {}
    for comp_id, comp_data in data.get('components', {}).items():
        components[comp_id] = _parse_component(comp_id, comp_data)

    # RX damage threshold settings
    input_power_range = chain_data.get('input_power_range_dbm')
    if input_power_range is not None:
        input_power_range = [_to_float(p) for p in input_power_range]

    damage_level = chain_data.get('damage_level_dbm')
    if damage_level is not None:
        damage_level = _to_float(damage_level)

    return ChainConfig(
        name=chain_data.get('name', 'RF Chain'),
        description=chain_data.get('description', ''),
        chain_type=chain_type,
        freq_range_ghz=freq_range,
        components=components,
        source_power_dbm=_to_float(chain_data.get('source_power_dbm'), 0.0),
        input_power_range_dbm=input_power_range,
        damage_level_dbm=damage_level
    )


# Legacy compatibility alias
def load_rf_chain_config(filepath: Union[str, Path] = None) -> ChainConfig:
    """Legacy alias for load_chain_config."""
    return load_chain_config(filepath)


# =============================================================================
# ARCHETYPE & PATH LOADING (Phase 2 Enhancement)
# =============================================================================

@dataclass
class PhysicalPath:
    """Physical RF path instance referencing an archetype."""
    path_id: str
    archetype_id: str
    antenna_position: str
    description: str
    freq_range_ghz: Optional[List[float]] = None  # Override archetype freq range


@dataclass
class RFChainLibrary:
    """
    Complete RF chain library with components, archetypes, and physical paths.

    Implements the "Library & Archetype" pattern:
    - components: Reusable component definitions
    - archetypes: Standard chain configurations referencing components
    - paths: Physical hardware instances referencing archetypes
    """
    components: Dict[str, dict]  # Component ID -> raw component data
    archetypes: Dict[str, dict]  # Archetype ID -> archetype definition
    paths: Dict[str, PhysicalPath]  # Path ID -> PhysicalPath

    def get_archetype_chain(self, archetype_id: str) -> ChainConfig:
        """
        Get a ChainConfig for a specific archetype.

        Args:
            archetype_id: ID of the archetype (e.g., 'rx_standard', 'tx_standard')

        Returns:
            ChainConfig with resolved components
        """
        if archetype_id not in self.archetypes:
            raise ValueError(f"Unknown archetype: {archetype_id}")

        arch_data = self.archetypes[archetype_id]
        return self._build_chain_from_archetype(archetype_id, arch_data)

    def get_path_chain(self, path_id: str) -> ChainConfig:
        """
        Get a ChainConfig for a specific physical path.

        Args:
            path_id: ID of the physical path (e.g., 'rx_path_1')

        Returns:
            ChainConfig with resolved components and path-specific overrides
        """
        if path_id not in self.paths:
            raise ValueError(f"Unknown path: {path_id}")

        path = self.paths[path_id]
        arch_data = self.archetypes[path.archetype_id].copy()

        # Apply path-specific overrides
        if path.freq_range_ghz:
            arch_data['freq_range_ghz'] = path.freq_range_ghz

        # Update name/description with path info
        arch_data['name'] = f"{arch_data.get('name', 'Chain')} - {path.path_id}"
        arch_data['description'] = path.description

        return self._build_chain_from_archetype(path_id, arch_data)

    def _build_chain_from_archetype(self, chain_id: str, arch_data: dict) -> ChainConfig:
        """Build a ChainConfig from archetype data, resolving component references."""
        chain_type_str = arch_data.get('type', 'receive')
        chain_type = ChainType(chain_type_str)

        freq_range = arch_data.get('freq_range_ghz', [2.0, 18.0])
        if isinstance(freq_range, list):
            freq_range = [_to_float(f) for f in freq_range]

        # Resolve component references
        components = {}
        for comp_ref in arch_data.get('components', []):
            ref_id = comp_ref.get('ref')
            order = comp_ref.get('order', 0)

            if ref_id not in self.components:
                raise ValueError(f"Unknown component reference: {ref_id}")

            # Get component data and add order
            comp_data = self.components[ref_id].copy()
            comp_data['order'] = order

            comp = self._parse_library_component(ref_id, comp_data)
            components[f"{ref_id}_{order}"] = comp

        return ChainConfig(
            name=arch_data.get('name', 'RF Chain'),
            description=arch_data.get('description', ''),
            chain_type=chain_type,
            freq_range_ghz=freq_range,
            components=components,
            source_power_dbm=_to_float(arch_data.get('source_power_dbm'), 0.0),
            input_power_range_dbm=None,
            damage_level_dbm=None
        )

    def _parse_library_component(self, comp_id: str, data: dict) -> Component:
        """Parse a component from the library."""
        comp_type = data.get('type', 'amplifier')
        name = data.get('name', comp_id)
        order = _to_int(data.get('order'), 0)

        if comp_type == 'cable':
            # Handle loss_points format from library
            loss_points = data.get('loss_points', [])
            if loss_points and len(loss_points) >= 2:
                point1 = loss_points[0]
                point2 = loss_points[1]
                loss_point1_ghz = _to_float(point1.get('freq_ghz'), 1.0)
                loss_point1_db = _to_float(point1.get('loss_db'), 0.0)
                loss_point2_ghz = _to_float(point2.get('freq_ghz'), 18.0)
                loss_point2_db = _to_float(point2.get('loss_db'), 0.0)
            else:
                loss_point1_ghz = 1.0
                loss_point1_db = 0.0
                loss_point2_ghz = 18.0
                loss_point2_db = 0.0

            return CableComponent(
                id=comp_id,
                name=name,
                order=order,
                loss_point1_ghz=loss_point1_ghz,
                loss_point1_db=loss_point1_db,
                loss_point2_ghz=loss_point2_ghz,
                loss_point2_db=loss_point2_db
            )

        elif comp_type in ('amplifier', 'integrated'):
            return AmplifierComponent(
                id=comp_id,
                name=name,
                order=order,
                gain_db=_to_float(data.get('gain_db'), 0.0),
                noise_figure_db=_to_float(data.get('noise_figure_db')) if data.get('noise_figure_db') else None,
                psat_dbm=_to_float(data.get('psat_dbm')) if data.get('psat_dbm') else None
            )

        elif comp_type == 'attenuator':
            return AttenuatorComponent(
                id=comp_id,
                name=name,
                order=order,
                atten_min_db=_to_float(data.get('attenuation_db', data.get('atten_min_db')), 0.0),
                atten_max_db=_to_float(data.get('attenuation_db', data.get('atten_max_db')), 0.0)
            )

        elif comp_type in ('filter', 'switch'):
            # Treat filters and switches as attenuators (passive loss)
            loss = _to_float(data.get('insertion_loss_db'), 0.0)
            return AttenuatorComponent(
                id=comp_id,
                name=name,
                order=order,
                atten_min_db=loss,
                atten_max_db=loss
            )

        elif comp_type == 'antenna':
            return AntennaComponent(
                id=comp_id,
                name=name,
                order=order,
                gain_db=_to_float(data.get('gain_dbi', data.get('gain_db')), 0.0)
            )

        else:
            # Default to amplifier
            return AmplifierComponent(
                id=comp_id,
                name=name,
                order=order,
                gain_db=_to_float(data.get('gain_db'), 0.0),
                noise_figure_db=None,
                psat_dbm=None
            )

    def list_archetypes(self) -> List[str]:
        """List all available archetype IDs."""
        return list(self.archetypes.keys())

    def list_paths(self) -> List[str]:
        """List all available physical path IDs."""
        return list(self.paths.keys())

    def get_paths_by_type(self, chain_type: str) -> List[str]:
        """Get path IDs filtered by chain type ('receive' or 'transmit')."""
        result = []
        for path_id, path in self.paths.items():
            arch = self.archetypes.get(path.archetype_id, {})
            if arch.get('type') == chain_type:
                result.append(path_id)
        return result


def load_rf_chain_library(filepath: Union[str, Path] = None) -> RFChainLibrary:
    """
    Load complete RF chain library with components, archetypes, and paths.

    This is the preferred method for loading RF chain configurations in Phase 2.

    Args:
        filepath: Path to rf_chains.yaml. If None, uses default location.

    Returns:
        RFChainLibrary with all definitions loaded.
    """
    if filepath is None:
        config_dir = Path(__file__).parent
        filepath = config_dir / "rf_chains.yaml"

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"RF chains library file not found: {filepath}")

    with open(filepath, 'r') as f:
        data = yaml.safe_load(f) or {}

    # Load component library
    components = data.get('components', {})

    # Load archetypes (try both new and legacy names)
    archetypes = data.get('chain_archetypes', data.get('chains', {}))

    # Load physical paths
    paths = {}
    for path_id, path_data in data.get('paths', {}).items():
        paths[path_id] = PhysicalPath(
            path_id=path_id,
            archetype_id=path_data.get('archetype', ''),
            antenna_position=path_data.get('antenna_position', ''),
            description=path_data.get('description', ''),
            freq_range_ghz=path_data.get('freq_range_ghz')
        )

    return RFChainLibrary(
        components=components,
        archetypes=archetypes,
        paths=paths
    )


def load_from_system_config(chain_type: str = 'receive') -> ChainConfig:
    """
    Load RF chain configuration from shared system_config.yaml.

    This ensures consistency with the central system design.
    Creates a simplified ChainConfig from system_config RF chain parameters.

    Args:
        chain_type: 'receive' or 'transmit'

    Returns:
        ChainConfig object with parameters from system_config
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from system_config import load_system_config

    sys_config = load_system_config()
    rf_chain = sys_config.rf_chain

    # Build components from system_config
    components = {}
    for i, comp in enumerate(rf_chain.components):
        comp_id = f"comp_{i}"
        if 'lna' in comp.name.lower() or 'amplifier' in comp.name.lower():
            components[comp_id] = AmplifierComponent(
                id=comp_id,
                name=comp.name,
                order=i,
                gain_db=comp.gain_db,
                noise_figure_db=comp.noise_figure_db
            )
        else:
            # Treat as amplifier with appropriate gain
            components[comp_id] = AmplifierComponent(
                id=comp_id,
                name=comp.name,
                order=i,
                gain_db=comp.gain_db,
                noise_figure_db=comp.noise_figure_db
            )

    return ChainConfig(
        name=f"RF Chain from system_config ({chain_type})",
        description=f"Cascade NF: {rf_chain.cascade_noise_figure_db} dB, "
                    f"Total Gain: {rf_chain.total_gain_db} dB",
        chain_type=ChainType.RECEIVE if chain_type == 'receive' else ChainType.TRANSMIT,
        freq_range_ghz=[sys_config.freq_min_ghz, sys_config.freq_max_ghz],
        components=components,
        source_power_dbm=0.0,
        input_power_range_dbm=[-100, 0],
        damage_level_dbm=rf_chain.damage_threshold_dbm
    )


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("Testing RF Chain configuration loader...")

    config = load_chain_config()

    print(f"\n{config}")
    print(f"\nChain type: {config.chain_type.value}")
    print(f"Is transmit: {config.is_transmit}")

    if config.is_transmit:
        print(f"Source power: {config.source_power_dbm} dBm")

    print(f"\nComponents ({len(config.components)}):")
    for comp in config.get_components_ordered():
        print(f"  {comp.order}. {comp.name} ({comp.type.value})")
        if isinstance(comp, CableComponent):
            print(f"      Loss: {comp.loss_point1_db} dB @ {comp.loss_point1_ghz} GHz, "
                  f"{comp.loss_point2_db} dB @ {comp.loss_point2_ghz} GHz")
        elif isinstance(comp, AmplifierComponent):
            print(f"      Gain: {comp.gain_db} dB, NF: {comp.noise_figure_db} dB, Psat: {comp.psat_dbm} dBm")
        elif isinstance(comp, AttenuatorComponent):
            print(f"      Atten: {comp.atten_min_db} - {comp.atten_max_db} dB")
        elif isinstance(comp, AntennaComponent):
            print(f"      Gain: {comp.gain_db} dBi")

    # Test frequency-dependent calculations
    print(f"\nGain at 10 GHz:")
    freq_min, freq_max = config.get_freq_min(), config.get_freq_max()
    for comp in config.get_components_ordered():
        if isinstance(comp, AttenuatorComponent):
            gain = comp.get_gain_at_freq(10.0, freq_min, freq_max)
        else:
            gain = comp.get_gain_at_freq(10.0)
        print(f"  {comp.name}: {gain:.2f} dB")

    print("\nConfiguration loading successful!")
