"""
Scan Position Dwell Scheduler for ESM Systems

This module implements dwell scheduling algorithms for wideband ESM receivers
that must scan across frequency to intercept radar emitters. The scheduler
optimizes dwell time at each scan position to maximize probability of
intercept (POI) while managing scan revisit rates.

Key concepts:
- Scan position: A frequency channel being monitored
- Dwell time: How long the receiver stays at each scan position
- POI: Probability that an emitter will be detected during a scan
- Time-on-target: Integration of emitter beams, pulses, and receiver dwells
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable
from enum import Enum
from esm_detection import (
    RadarParameters, ReceiverParameters, ESMDetector, DetectionResult
)


class ScanStrategy(Enum):
    """Scan strategy enumeration."""
    UNIFORM = "uniform"           # Equal dwell time at all positions
    THREAT_WEIGHTED = "threat"    # Longer dwell at threat frequencies
    ADAPTIVE = "adaptive"         # Adjust based on detection history
    OPTIMIZED = "optimized"       # Mathematically optimized for POI


@dataclass
class ScanPosition:
    """A single scan position (frequency channel)."""

    center_freq_GHz: float          # Center frequency of channel
    bandwidth_MHz: float            # Channel bandwidth
    dwell_time_ms: float = 10.0     # Dwell time at this position
    priority: float = 1.0           # Priority weight (for weighted scanning)
    last_detection_time: float = -np.inf  # Time of last detection (s)
    n_detections: int = 0           # Number of detections at this position

    @property
    def freq_min_GHz(self) -> float:
        return self.center_freq_GHz - self.bandwidth_MHz / 2000

    @property
    def freq_max_GHz(self) -> float:
        return self.center_freq_GHz + self.bandwidth_MHz / 2000


@dataclass
class EmitterModel:
    """
    Model of an emitter for POI calculations.

    Represents an expected/threat emitter with its scan and emission patterns.
    """

    radar: RadarParameters
    antenna_scan_type: str = "rotating"  # "rotating", "phased_array", "fixed"
    antenna_beamwidth_deg: float = 3.0   # 3-dB beamwidth
    main_beam_illumination_fraction: float = 0.1  # Fraction of time in main beam

    @property
    def pulses_per_dwell(self) -> Callable[[float], float]:
        """Return function that calculates pulses received during dwell."""
        def calc(dwell_time_ms: float) -> float:
            dwell_time_s = dwell_time_ms / 1000
            # Account for duty cycle and beam illumination
            effective_time = dwell_time_s * self.main_beam_illumination_fraction
            return effective_time * self.radar.prf_Hz
        return calc


@dataclass
class DwellSchedule:
    """Complete dwell schedule for ESM scan."""

    positions: List[ScanPosition]
    total_scan_time_ms: float
    strategy: ScanStrategy
    poi_estimates: Dict[str, float] = field(default_factory=dict)

    @property
    def n_positions(self) -> int:
        return len(self.positions)

    @property
    def scan_revisit_time_s(self) -> float:
        """Time to complete one full scan cycle."""
        return self.total_scan_time_ms / 1000

    def get_position_at_time(self, time_ms: float) -> ScanPosition:
        """Get the scan position at a given time within the scan cycle."""
        cumulative_time = 0.0
        cycle_time = time_ms % self.total_scan_time_ms

        for pos in self.positions:
            cumulative_time += pos.dwell_time_ms
            if cycle_time < cumulative_time:
                return pos

        return self.positions[-1]


class DwellScheduler:
    """
    Dwell Scheduler for ESM Systems

    Calculates optimal dwell times at each scan position to maximize
    probability of intercept while balancing scan revisit rate.
    """

    def __init__(self, receiver: ReceiverParameters,
                 freq_min_GHz: float = 2.0,
                 freq_max_GHz: float = 18.0,
                 channel_bandwidth_MHz: float = 20.0):
        """
        Initialize dwell scheduler.

        Args:
            receiver: ReceiverParameters for the ESM receiver
            freq_min_GHz: Minimum frequency to scan
            freq_max_GHz: Maximum frequency to scan
            channel_bandwidth_MHz: Bandwidth of each scan channel
        """
        self.receiver = receiver
        self.freq_min_GHz = freq_min_GHz
        self.freq_max_GHz = freq_max_GHz
        self.channel_bandwidth_MHz = channel_bandwidth_MHz

        # Create detector instance
        self.detector = ESMDetector(receiver)

        # Calculate number of scan positions
        total_bandwidth_MHz = (freq_max_GHz - freq_min_GHz) * 1000
        self.n_positions = int(np.ceil(total_bandwidth_MHz / channel_bandwidth_MHz))

        # Initialize scan positions
        self.positions = self._initialize_positions()

    def _initialize_positions(self) -> List[ScanPosition]:
        """Create initial list of scan positions."""
        positions = []
        freq_step_GHz = self.channel_bandwidth_MHz / 1000

        for i in range(self.n_positions):
            center_freq = self.freq_min_GHz + (i + 0.5) * freq_step_GHz
            if center_freq <= self.freq_max_GHz:
                positions.append(ScanPosition(
                    center_freq_GHz=center_freq,
                    bandwidth_MHz=self.channel_bandwidth_MHz,
                ))

        return positions

    def calculate_poi_single_dwell(self, emitter: EmitterModel,
                                    dwell_time_ms: float,
                                    range_km: float) -> float:
        """
        Calculate probability of intercept for single dwell.

        This accounts for:
        1. Signal being strong enough (SNR requirement)
        2. Receiver being tuned to correct frequency
        3. Emitter beam pointing at receiver (if scanning)
        4. Emitter actually transmitting (duty cycle)

        Args:
            emitter: EmitterModel describing the threat
            dwell_time_ms: Dwell time at the scan position
            range_km: Range to emitter in km

        Returns:
            Probability of intercept during this dwell
        """
        # Get number of pulses during dwell
        n_pulses = emitter.pulses_per_dwell(dwell_time_ms)

        if n_pulses < 1:
            # Need at least one pulse
            return 0.0

        # Calculate detection probability for the signal level
        pd = self.detector.calculate_detection_probability(
            emitter.radar, range_km, int(max(1, n_pulses)))

        # Probability that receiver is on correct frequency
        # For narrowband emitter, this is the ratio of channel BW to scan BW
        emitter_bw_MHz = emitter.radar.bandwidth_MHz
        scan_bw_MHz = (self.freq_max_GHz - self.freq_min_GHz) * 1000

        if emitter_bw_MHz >= self.channel_bandwidth_MHz:
            p_freq_overlap = 1.0
        else:
            # Emitter is narrowband - only detect when in correct channel
            p_freq_overlap = self.channel_bandwidth_MHz / scan_bw_MHz

        # Probability of beam illumination during dwell
        dwell_time_s = dwell_time_ms / 1000
        if emitter.antenna_scan_type == "fixed":
            p_beam = 1.0
        elif emitter.antenna_scan_type == "phased_array":
            # Phased array can point anywhere - assume some illumination time
            p_beam = min(1.0, dwell_time_s / (emitter.radar.scan_period_s * 0.1))
        else:  # rotating
            # For rotating antenna, beam illumination is brief
            beam_illumination_time_s = (emitter.radar.scan_period_s *
                                         emitter.antenna_beamwidth_deg / 360)
            p_beam = min(1.0, (dwell_time_s + beam_illumination_time_s) /
                         emitter.radar.scan_period_s)

        # Combined POI
        poi = pd * p_freq_overlap * p_beam

        return min(max(poi, 0.0), 1.0)

    def calculate_poi_full_scan(self, emitter: EmitterModel,
                                 schedule: DwellSchedule,
                                 range_km: float) -> float:
        """
        Calculate cumulative POI over a full scan cycle.

        Uses P(detection) = 1 - product(1 - P_i) for independent trials.

        Args:
            emitter: EmitterModel describing the threat
            schedule: DwellSchedule to evaluate
            range_km: Range to emitter in km

        Returns:
            Cumulative probability of intercept over full scan
        """
        # Find which channels could contain the emitter
        emitter_freq = emitter.radar.freq_GHz
        emitter_bw = emitter.radar.bandwidth_MHz / 1000  # Convert to GHz

        p_miss = 1.0

        for pos in schedule.positions:
            # Check if this channel overlaps with emitter frequency
            if (pos.freq_min_GHz <= emitter_freq + emitter_bw / 2 and
                    pos.freq_max_GHz >= emitter_freq - emitter_bw / 2):
                poi = self.calculate_poi_single_dwell(
                    emitter, pos.dwell_time_ms, range_km)
                p_miss *= (1 - poi)

        return 1 - p_miss

    def calculate_time_to_intercept(self, emitter: EmitterModel,
                                     schedule: DwellSchedule,
                                     range_km: float,
                                     poi_threshold: float = 0.9) -> float:
        """
        Calculate expected time to achieve target POI.

        Args:
            emitter: EmitterModel describing the threat
            schedule: DwellSchedule to use
            range_km: Range to emitter in km
            poi_threshold: Target cumulative POI

        Returns:
            Expected time in seconds to achieve poi_threshold
        """
        poi_per_scan = self.calculate_poi_full_scan(emitter, schedule, range_km)

        if poi_per_scan >= poi_threshold:
            # Can achieve in single scan
            return schedule.scan_revisit_time_s

        if poi_per_scan <= 0:
            return np.inf

        # Calculate number of scans needed
        # P(detect in N scans) = 1 - (1 - poi_per_scan)^N >= threshold
        # N >= log(1 - threshold) / log(1 - poi_per_scan)
        n_scans = np.ceil(np.log(1 - poi_threshold) /
                          np.log(1 - poi_per_scan))

        return n_scans * schedule.scan_revisit_time_s

    def create_uniform_schedule(self, dwell_time_ms: float = 10.0) -> DwellSchedule:
        """
        Create schedule with uniform dwell time at all positions.

        Args:
            dwell_time_ms: Dwell time at each position

        Returns:
            DwellSchedule with uniform dwells
        """
        positions = []
        for pos in self.positions:
            new_pos = ScanPosition(
                center_freq_GHz=pos.center_freq_GHz,
                bandwidth_MHz=pos.bandwidth_MHz,
                dwell_time_ms=dwell_time_ms,
                priority=1.0,
            )
            positions.append(new_pos)

        total_time = len(positions) * dwell_time_ms

        return DwellSchedule(
            positions=positions,
            total_scan_time_ms=total_time,
            strategy=ScanStrategy.UNIFORM,
        )

    def create_threat_weighted_schedule(self, threats: List[EmitterModel],
                                         total_scan_time_ms: float,
                                         min_dwell_ms: float = 5.0,
                                         max_dwell_ms: float = 50.0) -> DwellSchedule:
        """
        Create schedule weighted by threat locations.

        Allocates more dwell time to frequency bands where threats are expected.

        Args:
            threats: List of EmitterModels representing threats
            total_scan_time_ms: Total scan cycle time budget
            min_dwell_ms: Minimum dwell time at any position
            max_dwell_ms: Maximum dwell time at any position

        Returns:
            DwellSchedule weighted by threats
        """
        # Calculate priority for each position based on threat coverage
        priorities = np.ones(len(self.positions))

        for threat in threats:
            threat_freq = threat.radar.freq_GHz
            threat_bw = threat.radar.bandwidth_MHz / 1000

            for i, pos in enumerate(self.positions):
                # Calculate overlap between position and threat band
                overlap_min = max(pos.freq_min_GHz, threat_freq - threat_bw / 2)
                overlap_max = min(pos.freq_max_GHz, threat_freq + threat_bw / 2)

                if overlap_max > overlap_min:
                    # There is overlap - increase priority
                    overlap_fraction = (overlap_max - overlap_min) / (pos.bandwidth_MHz / 1000)
                    priorities[i] += overlap_fraction * threat.radar.eirp_W / 1e6

        # Normalize priorities
        priorities = priorities / priorities.sum()

        # Allocate dwell times proportionally
        positions = []
        for i, pos in enumerate(self.positions):
            dwell_time = priorities[i] * total_scan_time_ms
            dwell_time = max(min_dwell_ms, min(max_dwell_ms, dwell_time))

            new_pos = ScanPosition(
                center_freq_GHz=pos.center_freq_GHz,
                bandwidth_MHz=pos.bandwidth_MHz,
                dwell_time_ms=dwell_time,
                priority=priorities[i],
            )
            positions.append(new_pos)

        actual_total_time = sum(p.dwell_time_ms for p in positions)

        return DwellSchedule(
            positions=positions,
            total_scan_time_ms=actual_total_time,
            strategy=ScanStrategy.THREAT_WEIGHTED,
        )

    def optimize_schedule_for_poi(self, threats: List[EmitterModel],
                                   range_km: float,
                                   total_scan_time_ms: float,
                                   poi_target: float = 0.9,
                                   min_dwell_ms: float = 5.0,
                                   max_dwell_ms: float = 100.0) -> DwellSchedule:
        """
        Optimize dwell schedule to maximize minimum POI across threats.

        Uses iterative optimization to balance dwell times.

        Args:
            threats: List of EmitterModels to detect
            range_km: Range to threats in km
            total_scan_time_ms: Total scan time budget
            poi_target: Target POI for each threat
            min_dwell_ms: Minimum dwell at any position
            max_dwell_ms: Maximum dwell at any position

        Returns:
            Optimized DwellSchedule
        """
        # Start with threat-weighted schedule
        schedule = self.create_threat_weighted_schedule(
            threats, total_scan_time_ms, min_dwell_ms, max_dwell_ms)

        # Iteratively adjust to improve worst-case POI
        n_iterations = 50
        learning_rate = 0.1

        for iteration in range(n_iterations):
            # Calculate POI for each threat
            pois = []
            for threat in threats:
                poi = self.calculate_poi_full_scan(threat, schedule, range_km)
                pois.append(poi)

            worst_poi = min(pois)
            if worst_poi >= poi_target:
                break

            # Find which threat has worst POI
            worst_idx = np.argmin(pois)
            worst_threat = threats[worst_idx]

            # Increase dwell time at channels that cover worst threat
            for i, pos in enumerate(schedule.positions):
                threat_freq = worst_threat.radar.freq_GHz
                if (pos.freq_min_GHz <= threat_freq <= pos.freq_max_GHz):
                    # Increase dwell time
                    new_dwell = min(pos.dwell_time_ms * (1 + learning_rate), max_dwell_ms)
                    schedule.positions[i].dwell_time_ms = new_dwell
                else:
                    # Decrease slightly to maintain total time
                    new_dwell = max(pos.dwell_time_ms * (1 - learning_rate * 0.1), min_dwell_ms)
                    schedule.positions[i].dwell_time_ms = new_dwell

            # Update total time
            schedule.total_scan_time_ms = sum(p.dwell_time_ms for p in schedule.positions)

        # Store final POI estimates
        schedule.poi_estimates = {
            f"threat_{i}": self.calculate_poi_full_scan(t, schedule, range_km)
            for i, t in enumerate(threats)
        }
        schedule.strategy = ScanStrategy.OPTIMIZED

        return schedule

    def evaluate_schedule(self, schedule: DwellSchedule,
                          threats: List[EmitterModel],
                          range_km: float) -> Dict:
        """
        Evaluate a schedule's performance against threats.

        Args:
            schedule: DwellSchedule to evaluate
            threats: List of threats to detect
            range_km: Range to threats

        Returns:
            Dictionary with evaluation metrics
        """
        results = {
            'scan_revisit_time_s': schedule.scan_revisit_time_s,
            'n_positions': schedule.n_positions,
            'total_scan_time_ms': schedule.total_scan_time_ms,
            'threats': [],
        }

        for i, threat in enumerate(threats):
            poi = self.calculate_poi_full_scan(threat, schedule, range_km)
            tti = self.calculate_time_to_intercept(threat, schedule, range_km)

            threat_result = {
                'threat_id': i,
                'freq_GHz': threat.radar.freq_GHz,
                'eirp_dBW': threat.radar.eirp_dBW,
                'poi_per_scan': poi,
                'time_to_intercept_s': tti,
                'detection_range_km': self.detector.calculate_detection_range(threat.radar),
            }
            results['threats'].append(threat_result)

        # Summary statistics
        pois = [t['poi_per_scan'] for t in results['threats']]
        ttis = [t['time_to_intercept_s'] for t in results['threats']]

        results['summary'] = {
            'min_poi': min(pois),
            'mean_poi': np.mean(pois),
            'max_tti_s': max(ttis) if max(ttis) < np.inf else np.inf,
            'mean_tti_s': np.mean([t for t in ttis if t < np.inf]),
        }

        return results


def generate_threat_set(n_threats: int = 5,
                        freq_min_GHz: float = 2.0,
                        freq_max_GHz: float = 18.0,
                        eirp_min_dBW: float = 40.0,
                        eirp_max_dBW: float = 80.0,
                        random_seed: Optional[int] = None) -> List[EmitterModel]:
    """
    Generate a random set of threat emitters.

    Args:
        n_threats: Number of threats to generate
        freq_min_GHz: Minimum frequency
        freq_max_GHz: Maximum frequency
        eirp_min_dBW: Minimum EIRP
        eirp_max_dBW: Maximum EIRP
        random_seed: Random seed for reproducibility

    Returns:
        List of EmitterModel objects
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    threats = []
    for i in range(n_threats):
        radar = RadarParameters(
            eirp_dBW=np.random.uniform(eirp_min_dBW, eirp_max_dBW),
            freq_GHz=np.random.uniform(freq_min_GHz, freq_max_GHz),
            bandwidth_MHz=np.random.choice([1, 2, 5, 10, 20]),
            pulse_width_us=np.random.uniform(0.5, 10),
            pri_us=np.random.uniform(100, 5000),
            scan_period_s=np.random.uniform(2, 20),
        )

        scan_types = ["rotating", "phased_array", "fixed"]
        emitter = EmitterModel(
            radar=radar,
            antenna_scan_type=np.random.choice(scan_types),
            antenna_beamwidth_deg=np.random.uniform(1, 10),
        )
        threats.append(emitter)

    return threats
