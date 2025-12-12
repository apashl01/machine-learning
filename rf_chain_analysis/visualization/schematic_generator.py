"""
RF Chain System Architecture Generator using schemdraw

Generates a single comprehensive diagram showing the complete RF system
architecture with all RX and TX paths connected to a central transceiver unit.
"""

from pathlib import Path
from typing import Dict, List, Any
import yaml
import subprocess
import os

try:
    import schemdraw
    from schemdraw import elements as elm
    SCHEMDRAW_AVAILABLE = True
except ImportError:
    SCHEMDRAW_AVAILABLE = False
    print("Warning: schemdraw not installed. Install with: pip install schemdraw")

# Check for SVG to PNG conversion tools
SVG_CONVERTER = None
try:
    import cairosvg
    SVG_CONVERTER = 'cairosvg'
except (ImportError, OSError):
    # cairosvg not available or Cairo library not installed
    # Try svglib + reportlab (pure Python, works on Windows)
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        SVG_CONVERTER = 'svglib'
    except ImportError:
        # Check if Inkscape is available in PATH
        if os.system('inkscape --version > /dev/null 2>&1') == 0:
            SVG_CONVERTER = 'inkscape'
        # Check if rsvg-convert is available
        elif os.system('rsvg-convert --version > /dev/null 2>&1') == 0:
            SVG_CONVERTER = 'rsvg-convert'


def convert_svg_to_png(svg_path: Path, png_path: Path, dpi: int = 150) -> bool:
    """
    Convert SVG to PNG using available converter.

    Returns True if successful, False otherwise.
    """
    if SVG_CONVERTER == 'cairosvg':
        try:
            cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), dpi=dpi)
            return True
        except Exception as e:
            print(f"  cairosvg conversion failed: {e}")
            return False

    elif SVG_CONVERTER == 'svglib':
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPM

            # Load SVG
            drawing = svg2rlg(str(svg_path))
            if drawing is None:
                print(f"  svglib: Failed to load SVG")
                return False

            # Scale based on DPI (default is 72 DPI for reportlab)
            scale = dpi / 72.0
            drawing.width *= scale
            drawing.height *= scale
            drawing.scale(scale, scale)

            # Render to PNG
            renderPM.drawToFile(drawing, str(png_path), fmt='PNG', dpi=dpi)
            return True
        except Exception as e:
            print(f"  svglib conversion failed: {e}")
            return False

    elif SVG_CONVERTER == 'inkscape':
        try:
            result = subprocess.run(
                ['inkscape', '--export-type=png', f'--export-dpi={dpi}',
                 f'--export-filename={png_path}', str(svg_path)],
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            print(f"  Inkscape conversion failed: {e}")
            return False

    elif SVG_CONVERTER == 'rsvg-convert':
        try:
            result = subprocess.run(
                ['rsvg-convert', f'--dpi-x={dpi}', f'--dpi-y={dpi}',
                 '-o', str(png_path), str(svg_path)],
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            print(f"  rsvg-convert conversion failed: {e}")
            return False

    else:
        print("  No SVG to PNG converter available")
        print("  Install one of:")
        print("    - svglib + reportlab (recommended for Windows): pip install svglib reportlab pillow")
        print("    - cairosvg (requires Cairo C library): pip install cairosvg")
        print("    - inkscape or librsvg (system tools)")
        return False


def load_system_config(config_path: Path = None) -> Dict:
    """Load system configuration containing rx_paths and tx_paths with num_paths."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "system_config.yaml"

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def create_component_element(comp_name: str, comp_type: str, scale: float = 1.0):
    """Create a compact schemdraw element for a component."""
    if not SCHEMDRAW_AVAILABLE:
        return None

    # Map component type to schemdraw element with compact sizing
    if comp_type in ['antenna', 'spiral', 'horn', 'omni', 'dipole']:
        return elm.Antenna().scale(scale * 0.4)
    elif comp_type == 'amplifier':
        return elm.Opamp().scale(scale * 0.3).label(comp_name, fontsize=6)
    elif comp_type in ['attenuator', 'atten']:
        return elm.Resistor().scale(scale * 0.3).label(comp_name, fontsize=6)
    elif comp_type in ['filter', 'bandpass', 'lowpass', 'highpass']:
        return elm.RBox(w=0.6, h=0.4).label(comp_name, fontsize=6)
    elif comp_type == 'switch':
        return elm.Switch().scale(scale * 0.3)
    elif comp_type in ['cable', 'coax']:
        return elm.Line().length(0.3)
    else:
        # Default: compact labeled box
        return elm.RBox(w=0.6, h=0.4).label(comp_name, fontsize=6)


def draw_rx_path(d, components: List[Dict], y_offset: float, freq_label: str, start_x: float = 0, scale: float = 1.0):
    """
    Draw a single RX path horizontally from antenna (left) to transceiver (right).

    Returns the ending X position for connection to transceiver.
    """
    # Draw frequency label near antenna
    d += elm.Label().at((start_x - 0.5, y_offset)).label(freq_label, fontsize=7)

    # Start the path at the specified position
    current_pos = (start_x, y_offset)

    # Draw components left to right using natural chaining
    for i, comp in enumerate(components):
        comp_name = comp.get('name', 'Unknown')
        comp_type = comp.get('type', 'component')

        try:
            if i == 0:  # Antenna - first element
                d += elm.Antenna().scale(scale * 0.5).at(current_pos)
            else:
                # Add connecting line, then component
                d += elm.Line().right(0.4)

                # Add component element
                if comp_type in ['antenna', 'spiral', 'horn', 'omni', 'dipole']:
                    d += elm.Antenna().scale(scale * 0.4)
                elif comp_type == 'amplifier':
                    d += elm.Opamp().scale(scale * 0.3).label(comp_name, fontsize=6)
                elif comp_type in ['attenuator', 'atten']:
                    d += elm.Resistor().scale(scale * 0.3).label(comp_name, fontsize=6)
                elif comp_type in ['filter', 'bandpass', 'lowpass', 'highpass']:
                    d += elm.RBox(w=0.6, h=0.4).label(comp_name, fontsize=6)
                elif comp_type == 'switch':
                    d += elm.Switch().scale(scale * 0.3)
                elif comp_type in ['cable', 'coax']:
                    d += elm.Line().length(0.3)
                else:
                    d += elm.RBox(w=0.6, h=0.4).label(comp_name, fontsize=6)
        except Exception as e:
            # Fallback: simple box
            if i == 0:
                d += elm.RBox(w=0.4, h=0.3).at(current_pos).label(comp_name[:8], fontsize=5)
            else:
                d += elm.Line().right(0.2)
                d += elm.RBox(w=0.4, h=0.3).label(comp_name[:8], fontsize=5)

    # Return the current drawing position (endpoint)
    # Schemdraw tracks this internally, but we need to calculate it for connections
    # Estimate: antenna (0.8) + (n-1) components * (0.4 line + 0.6 component avg)
    estimated_end_x = start_x + 0.8 + (len(components) - 1) * 1.0
    return estimated_end_x


def draw_tx_path(d, components: List[Dict], y_offset: float, freq_label: str, start_x: float, scale: float = 1.0):
    """
    Draw a single TX path horizontally from transceiver (left) to antenna (right).
    """
    # Start the TX path from the transceiver edge
    current_pos = (start_x, y_offset)

    # Draw components left to right using natural chaining
    for i, comp in enumerate(components):
        comp_name = comp.get('name', 'Unknown')
        comp_type = comp.get('type', 'component')

        try:
            if i == 0:  # First component after transceiver
                # Check if it's an antenna (last in chain)
                if comp_type in ['antenna', 'spiral', 'horn', 'omni']:
                    d += elm.Antenna().scale(scale * 0.5).at(current_pos)
                    # Add frequency label
                    d += elm.Label().at((start_x + 0.8, y_offset)).label(freq_label, fontsize=7)
                else:
                    # Regular component
                    if comp_type == 'amplifier':
                        d += elm.Opamp().scale(scale * 0.3).label(comp_name, fontsize=6).at(current_pos)
                    elif comp_type in ['attenuator', 'atten']:
                        d += elm.Resistor().scale(scale * 0.3).label(comp_name, fontsize=6).at(current_pos)
                    elif comp_type in ['filter', 'bandpass', 'lowpass', 'highpass']:
                        d += elm.RBox(w=0.6, h=0.4).label(comp_name, fontsize=6).at(current_pos)
                    elif comp_type == 'switch':
                        d += elm.Switch().scale(scale * 0.3).at(current_pos)
                    elif comp_type in ['cable', 'coax']:
                        d += elm.Line().length(0.3).at(current_pos)
                    else:
                        d += elm.RBox(w=0.6, h=0.4).label(comp_name, fontsize=6).at(current_pos)
            else:
                # Subsequent components - use chaining
                d += elm.Line().right(0.4)

                if comp_type in ['antenna', 'spiral', 'horn', 'omni']:
                    d += elm.Antenna().scale(scale * 0.5)
                    # Add frequency label near antenna (estimate position)
                    label_x = start_x + (i + 1) * 1.0 + 0.8
                    d += elm.Label().at((label_x, y_offset)).label(freq_label, fontsize=7)
                elif comp_type == 'amplifier':
                    d += elm.Opamp().scale(scale * 0.3).label(comp_name, fontsize=6)
                elif comp_type in ['attenuator', 'atten']:
                    d += elm.Resistor().scale(scale * 0.3).label(comp_name, fontsize=6)
                elif comp_type in ['filter', 'bandpass', 'lowpass', 'highpass']:
                    d += elm.RBox(w=0.6, h=0.4).label(comp_name, fontsize=6)
                elif comp_type == 'switch':
                    d += elm.Switch().scale(scale * 0.3)
                elif comp_type in ['cable', 'coax']:
                    d += elm.Line().length(0.3)
                else:
                    d += elm.RBox(w=0.6, h=0.4).label(comp_name, fontsize=6)
        except Exception as e:
            # Fallback: simple box
            if i == 0:
                d += elm.RBox(w=0.4, h=0.3).at(current_pos).label(comp_name[:8], fontsize=5)
            else:
                d += elm.Line().right(0.2)
                d += elm.RBox(w=0.4, h=0.3).label(comp_name[:8], fontsize=5)


def generate_system_architecture(output_dir: Path = None):
    """
    Generate a single comprehensive system architecture diagram showing all
    RX and TX paths connected to a central transceiver unit.
    """
    if not SCHEMDRAW_AVAILABLE:
        print("schemdraw not available - skipping system architecture generation")
        return

    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "output"

    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nGenerating System RF Architecture Diagram...")

    # Load system configuration
    config = load_system_config()
    rf_chains = config.get('rf_chains', {})
    rx_paths = rf_chains.get('rx_paths', {})
    tx_paths = rf_chains.get('tx_paths', {})

    # Create drawing with compact scaling
    d = schemdraw.Drawing(unit=0.8, fontsize=8)

    # =========================================================================
    # Calculate layout dimensions
    # =========================================================================

    # Count total physical paths
    total_rx_paths = sum(path.get('num_paths', 1) for path in rx_paths.values())
    total_tx_paths = sum(path.get('num_paths', 1) for path in tx_paths.values())

    print(f"  Total RX paths: {total_rx_paths}")
    print(f"  Total TX paths: {total_tx_paths}")

    # Vertical spacing between paths
    path_spacing = 1.2

    # Calculate total height needed and track path positions
    rx_height = total_rx_paths * path_spacing
    tx_height = total_tx_paths * path_spacing
    total_height = max(rx_height, tx_height)
    max_paths = max(total_rx_paths, total_tx_paths)

    # Calculate actual Y positions for paths
    start_y = total_height - 0.5  # Top position
    end_y = start_y - (max_paths - 1) * path_spacing  # Bottom position

    # Transceiver box dimensions and position (dynamically sized)
    transceiver_width = 3.0
    transceiver_height = (start_y - end_y) + 1.5  # Height spans all paths + margin
    transceiver_x = 6.0  # Center position
    transceiver_y_center = (start_y + end_y) / 2  # Center vertically between paths

    # =========================================================================
    # Draw Central Transceiver/Processor
    # =========================================================================

    d += elm.RBox(w=transceiver_width, h=transceiver_height).at(
        (transceiver_x - transceiver_width/2, transceiver_y_center - transceiver_height/2)
    ).fill('#e0e0e0').label('Transceiver /\nProcessor', fontsize=10)

    # =========================================================================
    # Draw RX Paths (Left side -> Transceiver)
    # =========================================================================

    current_y = start_y  # Start from top
    rx_connection_points = []

    for path_name, path_config in rx_paths.items():
        num_paths = path_config.get('num_paths', 1)
        freq_range = path_config.get('freq_range_ghz', [0, 0])
        freq_label = f"{freq_range[0]:.1f}-{freq_range[1]:.1f} GHz"
        components = path_config.get('components', [])

        print(f"  Drawing {num_paths}x {path_name} ({freq_label})")

        # Draw each physical instance of this path type
        for i in range(num_paths):
            endpoint_x = draw_rx_path(d, components, current_y, freq_label, scale=1.0)
            rx_connection_points.append((endpoint_x, current_y))

            # Connect endpoint to transceiver
            transceiver_left = transceiver_x - transceiver_width/2
            d += elm.Line().at((endpoint_x, current_y)).to((transceiver_left, current_y))

            current_y -= path_spacing

    # =========================================================================
    # Draw TX Paths (Transceiver -> Right side)
    # =========================================================================

    current_y = start_y  # Start from top (same as RX paths)

    for path_name, path_config in tx_paths.items():
        num_paths = path_config.get('num_paths', 1)
        freq_range = path_config.get('freq_range_ghz', [0, 0])
        freq_label = f"{freq_range[0]:.1f}-{freq_range[1]:.1f} GHz"
        components = path_config.get('components', [])

        print(f"  Drawing {num_paths}x {path_name} ({freq_label})")

        # Draw each physical instance of this path type
        for i in range(num_paths):
            transceiver_right = transceiver_x + transceiver_width/2

            # Connection from transceiver
            tx_start_x = transceiver_right + 0.5
            d += elm.Line().at((transceiver_right, current_y)).to((tx_start_x, current_y))

            # Draw TX path components
            draw_tx_path(d, components, current_y, freq_label, tx_start_x, scale=1.0)

            current_y -= path_spacing

    # =========================================================================
    # Add Title
    # =========================================================================

    title_y = total_height + 1.0
    d += elm.Label().at((transceiver_x, title_y)).label(
        'RF System Architecture', fontsize=14
    )

    # =========================================================================
    # Save diagram
    # =========================================================================

    # Save as SVG first
    svg_path = output_dir / "system_architecture.svg"
    d.save(str(svg_path))
    print(f"  System architecture diagram (SVG) saved to: {svg_path}")

    # Convert to PNG for PowerPoint compatibility
    png_path = output_dir / "system_architecture.png"
    print(f"  Converting to PNG for PowerPoint...")

    if convert_svg_to_png(svg_path, png_path, dpi=150):
        print(f"  System architecture diagram (PNG) saved to: {png_path}")
        return png_path
    else:
        print(f"  Warning: PNG conversion failed, PowerPoint may not be able to use SVG")
        return svg_path


def generate_all_schematics(output_dir: Path = None):
    """
    Main entry point: Generate system architecture diagram.

    This replaces the previous approach of generating individual chain schematics.
    """
    print("\n" + "=" * 70)
    print(" RF SYSTEM ARCHITECTURE GENERATION")
    print("=" * 70)

    try:
        generate_system_architecture(output_dir)
        print("\nSystem architecture generation complete!")
    except Exception as e:
        print(f"\nError generating system architecture: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    generate_all_schematics()
