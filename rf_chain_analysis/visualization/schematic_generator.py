"""
RF Chain Schematic Generator using schemdraw

Task 1: Generates visual schematics of RF chain archetypes from config/rf_chains.yaml.
"""

from pathlib import Path
from typing import Dict, List, Any
import yaml

try:
    import schemdraw
    from schemdraw import elements as elm
    SCHEMDRAW_AVAILABLE = True
except ImportError:
    SCHEMDRAW_AVAILABLE = False
    print("Warning: schemdraw not installed. Install with: pip install schemdraw")


# Component type to schemdraw element mapping
COMPONENT_MAP = {
    'antenna': 'Antenna',
    'amplifier': 'Opamp',
    'attenuator': 'Resistor',
    'filter': 'RBox',
    'switch': 'Switch',
    'cable': 'Line',
    'coax': 'Line',
    'bandpass': 'RBox',
    'lowpass': 'RBox',
    'highpass': 'RBox',
}


def load_chains_config(config_path: Path = None) -> Dict:
    """Load RF chains configuration from YAML."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "rf_chains.yaml"

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_component_details(comp_ref: str, components_library: Dict) -> tuple:
    """Get component name and type from library."""
    if comp_ref in components_library:
        comp_data = components_library[comp_ref]
        return comp_data.get('name', comp_ref), comp_data.get('type', 'unknown')
    return comp_ref, 'unknown'


def create_schematic_element(comp_name: str, comp_type: str):
    """Create appropriate schemdraw element for component type."""
    if not SCHEMDRAW_AVAILABLE:
        return None

    # Map component type to schemdraw element
    if comp_type in ['antenna', 'spiral', 'horn', 'omni']:
        # Use a simple antenna symbol (triangle)
        return elm.Antenna()
    elif comp_type == 'amplifier':
        return elm.Opamp().label(comp_name)
    elif comp_type in ['attenuator', 'atten']:
        return elm.Resistor().label(comp_name)
    elif comp_type in ['filter', 'bandpass', 'lowpass', 'highpass']:
        return elm.RBox(w=1.5, h=1).label(comp_name)
    elif comp_type == 'switch':
        return elm.Switch().label(comp_name)
    elif comp_type in ['cable', 'coax']:
        # Use a line with label
        return elm.Line().label(comp_name, loc='top')
    else:
        # Default: labeled box
        return elm.RBox(w=1.5, h=1).label(comp_name)


def generate_chain_schematic(archetype_name: str, archetype_data: Dict,
                            components_library: Dict, output_dir: Path):
    """
    Generate schematic diagram for a single RF chain archetype.

    Args:
        archetype_name: Name of the archetype (e.g., 'rx_standard')
        archetype_data: Archetype configuration dict
        components_library: Component library dict
        output_dir: Directory to save schematic
    """
    if not SCHEMDRAW_AVAILABLE:
        print(f"  Skipping {archetype_name} - schemdraw not available")
        return

    name = archetype_data.get('name', archetype_name)
    description = archetype_data.get('description', '')
    chain_type = archetype_data.get('type', 'unknown')
    freq_range = archetype_data.get('freq_range_ghz', [0, 0])
    components_list = archetype_data.get('components', [])

    # Sort components by order
    components_list = sorted(components_list, key=lambda x: x.get('order', 999))

    # Create drawing
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=10, font='sans-serif')

        # Add title
        title_text = f"{name}\n{description}\n{freq_range[0]:.1f}-{freq_range[1]:.1f} GHz"

        # Draw components in sequence from left to right
        for i, comp_spec in enumerate(components_list):
            comp_ref = comp_spec.get('ref', f'comp_{i}')
            comp_name, comp_type = get_component_details(comp_ref, components_library)

            # Create and add the element
            try:
                if i == 0:
                    # First element starts the chain
                    elem = create_schematic_element(comp_name, comp_type)
                    if elem:
                        d += elem
                else:
                    # Subsequent elements connect with a line and then the component
                    d += elm.Line().right(0.5)
                    elem = create_schematic_element(comp_name, comp_type)
                    if elem:
                        d += elem
            except Exception as e:
                print(f"    Warning: Could not add {comp_name}: {e}")
                # Add a simple box as fallback
                d += elm.Line().right(0.5)
                d += elm.RBox(w=1.5, h=1).label(comp_name)

        # Add title at top
        # Note: schemdraw doesn't have a built-in title, so we'll add it as text annotation

        # Save schematic
        output_path = output_dir / f"schematic_{archetype_name}.png"
        d.save(str(output_path), dpi=150)
        print(f"  Schematic saved: {output_path}")


def generate_all_schematics(output_dir: Path = None):
    """
    Generate schematics for all chain archetypes in config/rf_chains.yaml.

    Args:
        output_dir: Directory to save schematics. If None, uses rf_chain_analysis/output/
    """
    if not SCHEMDRAW_AVAILABLE:
        print("Cannot generate schematics - schemdraw not installed")
        print("Install with: pip install schemdraw")
        return

    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "output"

    output_dir.mkdir(exist_ok=True, parents=True)

    # Load configuration
    config = load_chains_config()
    components_library = config.get('components', {})
    archetypes = config.get('chain_archetypes', {})

    print(f"\nGenerating RF Chain Schematics...")
    print(f"Found {len(archetypes)} archetypes")

    # Generate schematic for each archetype
    for archetype_name, archetype_data in archetypes.items():
        print(f"\nGenerating {archetype_name}...")
        try:
            generate_chain_schematic(
                archetype_name,
                archetype_data,
                components_library,
                output_dir
            )
        except Exception as e:
            print(f"  Error generating {archetype_name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nSchematic generation complete!")
    print(f"Schematics saved to: {output_dir}")


if __name__ == "__main__":
    generate_all_schematics()
