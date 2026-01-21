import time
import random


class RadarSynchronizer:
    def __init__(self, prf_hz, range_clock_frequency_hz):
        """
        Simulates the Master Clock / Synchronizer of a Radar.

        :param prf_hz: Pulse Repetition Frequency (How often we fire).
                       e.g., 1000 Hz = 1 pulse every 1 millisecond.
        :param range_clock_frequency_hz: The speed of the internal counter.
                       Higher freq = Better accuracy (Range Resolution).
        """
        self.c = 299792458  # Speed of light (m/s)
        self.prf = prf_hz
        self.clock_freq = range_clock_frequency_hz

        # Calculate timing constants
        self.pri_seconds = 1.0 / self.prf  # Pulse Repetition Interval (Time between pulses)
        self.clock_tick_duration = 1.0 / self.clock_freq

        # State variables
        self.range_counter = 0  # The "Range Clock"
        self.is_transmitting = False  # Status of Transmitter
        self.is_listening = False  # Status of Receiver
        self.last_pulse_time = 0
        self.simulation_time = 0.0

    def tick(self):
        """
        The Master Clock "Heartbeat".
        This function is called in a high-speed loop to advance time.
        """
        self.simulation_time += self.clock_tick_duration

        # 1. GENERATE HEARTBEAT & TRIGGER PULSE
        # Check if enough time has passed to fire the next pulse (PRI)
        if self.simulation_time - self.last_pulse_time >= self.pri_seconds:
            self._fire_trigger()

        # 2. MANAGE RANGE CLOCK
        # If we are listening, increment the counter (counting distance)
        if self.is_listening:
            self.range_counter += 1

    def _fire_trigger(self):
        """
        Internal method: Sends the Trigger Pulse to Tx and resets Rx Clock.
        """
        self.last_pulse_time = self.simulation_time

        # A. Trigger the Transmitter
        self.is_transmitting = True
        print(f"\n[TIME {self.simulation_time * 1000:.3f} ms] >>> MASTER CLOCK: TRIGGER FIRED! (Tx ON)")

        # B. Start/Reset the Range Clock
        self.range_counter = 0
        self.is_listening = True
        print(f"                                   >>> MASTER CLOCK: RANGE COUNTER RESET TO 0")

        # Simulate pulse duration (very short, e.g., 1 microsecond)
        # In simulation, we turn off Tx immediately next tick for simplicity
        self.is_transmitting = False

    def echo_received(self):
        """
        Simulates the Receiver (Rx) telling the Master Clock
        that a signal threshold was crossed.
        """
        if self.is_listening:
            # STOP the clock logic momentarily to capture the value
            captured_ticks = self.range_counter

            # Calculate Distance logic:
            # Time = Ticks * TimePerTick
            # Distance = (Time * c) / 2
            time_of_flight = captured_ticks * self.clock_tick_duration
            distance = (time_of_flight * self.c) / 2.0

            print(f"[ECHO] Signal Received!")
            print(f"       Range Clock stopped at: {captured_ticks} ticks")
            print(f"       Calculated Time:        {time_of_flight * 1e6:.2f} microseconds")
            print(f"       CALCULATED RANGE:       {distance:.2f} meters")

            return distance
        return None


# --- MAIN SIMULATION LOOP ---
if __name__ == "__main__":
    print("--- RADAR SYNCHRONIZER STARTING ---")

    # SETUP:
    # 1 kHz PRF (Fire every 1ms)
    # 10 MHz Range Clock (Count every 0.1 microseconds)
    # 10 MHz gives us a resolution of about 15 meters.
    radar_brain = RadarSynchronizer(prf_hz=1000, range_clock_frequency_hz=10_000_000)

    # Simulation Setup
    total_simulation_steps = 25000  # Run for a short burst

    # We will pretend a target exists at a specific time delay
    # Target is approx 4.5km away (which takes ~30 microseconds round trip)
    target_echo_delay_ticks = 300

    try:
        current_step = 0
        while current_step < total_simulation_steps:

            # 1. Tick the Master Clock
            radar_brain.tick()

            # 2. Simulate the physics of a target reflection
            # The logic below simulates the "Environment" returning the signal
            if radar_brain.is_listening:
                if radar_brain.range_counter == target_echo_delay_ticks:
                    radar_brain.echo_received()

            current_step += 1

    except KeyboardInterrupt:
        print("Simulation stopped.")

    print("\n--- SIMULATION COMPLETE ---")