"""
RF Chain Configuration Loader

Loads and validates YAML configuration for RF chain analysis.
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
    FILTER = "filter"
    SWITCH = "switch"
    ANTENNA = "antenna"
    INTEGRATED = "integrated"  # Integrated assemblies like RFP PCB


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
class LossPoint:
    """Frequency-dependent loss point for cables."""
    freq_ghz: float
    loss_db: float


@dataclass
class Component:
    """Generic RF component."""
    id: str
    type: ComponentType
    name: str

    # Common parameters
    gain_db: float = 0.0           # Positive for amplifiers, negative for losses
    noise_figure_db: float = 0.0   # NF in dB
    p1db_dbm: float = 100.0        # 1dB compression point
    psat_dbm: float = 100.0        # Saturation power

    # Cable-specific
    loss_points: List[LossPoint] = field(default_factory=list)

    # Attenuator-specific
    attenuation_db: float = 0.0
    min_atten_db: float = 0.0
    max_atten_db: float = 0.0

    # Filter-specific
    insertion_loss_db: float = 0.0
    freq_min_ghz: float = 0.0
    freq_max_ghz: float = 100.0

    # Switch-specific
    isolation_db: float = 0.0

    # Antenna-specific
    gain_dbi: float = 0.0

    def get_gain_at_freq(self, freq_ghz: float) -> float:
        """
        Get component gain/loss at specific frequency.

        Returns:
            Gain in dB (negative for losses).
        """
        if self.type == ComponentType.CABLE:
            return -self._calculate_cable_loss(freq_ghz)
        elif self.type == ComponentType.ATTENUATOR:
            return -self.attenuation_db
        elif self.type == ComponentType.FILTER:
            # Check if in passband
            if self.freq_min_ghz <= freq_ghz <= self.freq_max_ghz:
                return -self.insertion_loss_db
            else:
                return -60.0  # Out of band rejection
        elif self.type == ComponentType.SWITCH:
            return -self.insertion_loss_db
        elif self.type == ComponentType.ANTENNA:
            return self.gain_dbi
        else:  # AMPLIFIER, INTEGRATED
            return self.gain_db

    def get_nf_at_freq(self, freq_ghz: float) -> float:
        """
        Get component noise figure at specific frequency.

        For passive devices, NF equals the loss.
        """
        if self.type in [ComponentType.CABLE, ComponentType.ATTENUATOR,
                         ComponentType.FILTER, ComponentType.SWITCH]:
            # Passive device: NF = Loss
            return abs(self.get_gain_at_freq(freq_ghz))
        elif self.type == ComponentType.ANTENNA:
            return 0.0  # Ideal antenna adds no noise
        else:
            return self.noise_figure_db

    def _calculate_cable_loss(self, freq_ghz: float) -> float:
        """Calculate cable loss using sqrt(f) model."""
        if not self.loss_points or len(self.loss_points) < 2:
            return 0.0

        # Use first two points to calculate k coefficient
        p1 = self.loss_points[0]
        p2 = self.loss_points[1]

        # Loss = k * sqrt(f)
        # Solve for k using both points and average
        k1 = p1.loss_db / math.sqrt(p1.freq_ghz) if p1.freq_ghz > 0 else 0
        k2 = p2.loss_db / math.sqrt(p2.freq_ghz) if p2.freq_ghz > 0 else 0
        k = (k1 + k2) / 2

        return k * math.sqrt(freq_ghz)

    def __str__(self) -> str:
        if self.type == ComponentType.AMPLIFIER:
            return f"{self.name}: G={self.gain_db:.1f}dB, NF={self.noise_figure_db:.1f}dB"
        elif self.type == ComponentType.CABLE:
            return f"{self.name}: Cable (freq-dependent loss)"
        elif self.type == ComponentType.ATTENUATOR:
            return f"{self.name}: {self.attenuation_db:.1f}dB atten"
        else:
            return f"{self.name} ({self.type.value})"


@dataclass
class ChainComponent:
    """Component instance in a chain with order."""
    component: Component
    order: int


@dataclass
class RFChain:
    """Complete RF chain definition."""
    id: str
    name: str
    description: str
    chain_type: ChainType
    freq_range_ghz: List[float]
    components: List[ChainComponent]

    # TX-specific
    source_power_dbm: float = 0.0

    def get_components_ordered(self) -> List[Component]:
        """Get components in signal path order."""
        sorted_chain = sorted(self.components, key=lambda c: c.order)
        return [c.component for c in sorted_chain]

    def __str__(self) -> str:
        comp_list = ", ".join([c.component.name for c in
                               sorted(self.components, key=lambda x: x.order)])
        return (f"{self.name} ({self.chain_type.value})\n"
                f"  {self.description}\n"
                f"  Components: {comp_list}")


@dataclass
class AnalysisSettings:
    """Analysis configuration settings."""
    frequency_points: int = 200
    temperature_k: float = 290.0
    snr_required_db: float = 10.0
    bandwidth_hz: float = 20.0e6
    input_power_sweep_dbm: List[float] = field(default_factory=lambda: [-80, 0])
    adc_damage_level_dbm: float = 10.0


@dataclass
class ComponentLibrary:
    """Library of reusable components."""
    components: Dict[str, Component] = field(default_factory=dict)

    def get(self, component_id: str) -> Optional[Component]:
        return self.components.get(component_id)

    def list_components(self) -> List[str]:
        return list(self.components.keys())

    def __len__(self) -> int:
        return len(self.components)


@dataclass
class RFChainConfig:
    """Complete RF chain configuration."""
    component_library: ComponentLibrary
    chains: Dict[str, RFChain]
    analysis: AnalysisSettings
    defaults: Dict[str, Any]

    def get_chain(self, chain_id: str) -> Optional[RFChain]:
        return self.chains.get(chain_id)

    def list_chains(self) -> List[str]:
        return list(self.chains.keys())

    def get_receive_chains(self) -> List[RFChain]:
        return [c for c in self.chains.values() if c.chain_type == ChainType.RECEIVE]

    def get_transmit_chains(self) -> List[RFChain]:
        return [c for c in self.chains.values() if c.chain_type == ChainType.TRANSMIT]


# =============================================================================
# PARSING FUNCTIONS
# =============================================================================

def _parse_component(comp_id: str, data: dict) -> Component:
    """Parse a component from dict."""
    comp_type = ComponentType(data.get('type', 'amplifier'))

    # Parse loss points for cables
    loss_points = []
    if 'loss_points' in data:
        for lp in data['loss_points']:
            loss_points.append(LossPoint(
                freq_ghz=_to_float(lp.get('freq_ghz'), 1.0),
                loss_db=_to_float(lp.get('loss_db'), 0.0)
            ))

    return Component(
        id=comp_id,
        type=comp_type,
        name=data.get('name', comp_id),
        gain_db=_to_float(data.get('gain_db'), 0.0),
        noise_figure_db=_to_float(data.get('noise_figure_db'), 0.0),
        p1db_dbm=_to_float(data.get('p1db_dbm'), 100.0),
        psat_dbm=_to_float(data.get('psat_dbm'), 100.0),
        loss_points=loss_points,
        attenuation_db=_to_float(data.get('attenuation_db'), 0.0),
        min_atten_db=_to_float(data.get('min_atten_db'), 0.0),
        max_atten_db=_to_float(data.get('max_atten_db'), 0.0),
        insertion_loss_db=_to_float(data.get('insertion_loss_db'), 0.0),
        freq_min_ghz=_to_float(data.get('freq_min_ghz'), 0.0),
        freq_max_ghz=_to_float(data.get('freq_max_ghz'), 100.0),
        isolation_db=_to_float(data.get('isolation_db'), 0.0),
        gain_dbi=_to_float(data.get('gain_dbi'), 0.0)
    )


def _parse_component_library(data: dict) -> ComponentLibrary:
    """Parse component library from dict."""
    components = {}
    for comp_id, comp_data in data.items():
        components[comp_id] = _parse_component(comp_id, comp_data)
    return ComponentLibrary(components=components)


def _parse_chain(chain_id: str, data: dict, library: ComponentLibrary) -> RFChain:
    """Parse an RF chain from dict."""
    # Parse chain type
    chain_type_str = data.get('type', 'receive')
    chain_type = ChainType(chain_type_str)

    # Parse frequency range
    freq_range = data.get('freq_range_ghz', [2.0, 18.0])
    if isinstance(freq_range, list):
        freq_range = [_to_float(f) for f in freq_range]
    else:
        freq_range = [2.0, 18.0]

    # Parse components
    chain_components = []
    for comp_entry in data.get('components', []):
        comp_ref = comp_entry.get('ref')
        order = _to_int(comp_entry.get('order'), 0)

        if comp_ref and comp_ref in library.components:
            chain_components.append(ChainComponent(
                component=library.components[comp_ref],
                order=order
            ))

    return RFChain(
        id=chain_id,
        name=data.get('name', chain_id),
        description=data.get('description', ''),
        chain_type=chain_type,
        freq_range_ghz=freq_range,
        components=chain_components,
        source_power_dbm=_to_float(data.get('source_power_dbm'), 0.0)
    )


def _parse_analysis_settings(data: dict) -> AnalysisSettings:
    """Parse analysis settings from dict."""
    power_sweep = data.get('input_power_sweep_dbm', [-80, 0])
    if isinstance(power_sweep, list):
        power_sweep = [_to_float(p) for p in power_sweep]
    else:
        power_sweep = [-80, 0]

    return AnalysisSettings(
        frequency_points=_to_int(data.get('frequency_points'), 200),
        temperature_k=_to_float(data.get('temperature_k'), 290.0),
        snr_required_db=_to_float(data.get('snr_required_db'), 10.0),
        bandwidth_hz=_to_float(data.get('bandwidth_hz'), 20.0e6),
        input_power_sweep_dbm=power_sweep,
        adc_damage_level_dbm=_to_float(data.get('adc_damage_level_dbm'), 10.0)
    )


# =============================================================================
# MAIN LOADING FUNCTION
# =============================================================================

def load_rf_chain_config(filepath: Union[str, Path] = None) -> RFChainConfig:
    """
    Load RF chain configuration from YAML file.

    Args:
        filepath: Path to rf_chains.yaml. If None, uses default location.

    Returns:
        RFChainConfig object with all chain definitions.
    """
    if filepath is None:
        config_dir = Path(__file__).parent
        filepath = config_dir / "rf_chains.yaml"

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(filepath, 'r') as f:
        data = yaml.safe_load(f) or {}

    # Parse defaults
    defaults = data.get('defaults', {})

    # Parse component library
    library = _parse_component_library(data.get('components', {}))

    # Parse chains
    chains = {}
    for chain_id, chain_data in data.get('chains', {}).items():
        chains[chain_id] = _parse_chain(chain_id, chain_data, library)

    # Parse analysis settings
    analysis = _parse_analysis_settings(data.get('analysis', {}))

    return RFChainConfig(
        component_library=library,
        chains=chains,
        analysis=analysis,
        defaults=defaults
    )


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("Testing RF Chain configuration loader...")

    config = load_rf_chain_config()

    print(f"\nComponent Library: {len(config.component_library)} components")
    for comp_id in config.component_library.list_components():
        print(f"  - {comp_id}")

    print(f"\nChains: {len(config.chains)}")
    for chain_id, chain in config.chains.items():
        print(f"\n{chain}")

    print("\nConfiguration loading successful!")
