import numpy as np
import time
from environment import GridEdgeEnv

def smart_charging_policy(observation, num_evs):
    """
    A simple rule-based charging policy that considers:
    1. Renewable energy availability
    2. Electricity price
    3. Time until departure
    4. Current state of charge
    """
    # Extract global states from observation
    ev_states = observation[:-4]  # All EV states
    time_of_day = observation[-4]
    electricity_price = observation[-3]
    renewable_availability = observation[-2]
    grid_load = observation[-1]
    
    # Initialize charging decisions
    charging_rates = np.zeros(num_evs)
    
    # Process each EV's state and make charging decisions
    for i in range(num_evs):
        # Extract individual EV state
        soc = ev_states[i * 4]
        time_until_departure = ev_states[i * 4 + 1] * 24  # Denormalize to hours
        charging_power = ev_states[i * 4 + 2] * 22  # Denormalize to kW
        price_threshold = ev_states[i * 4 + 3] * 0.5  # Denormalize to $/kWh
        
        # Determine charging rate based on conditions
        if soc < 0.2 or time_until_departure < 2:  # Emergency charging
            charging_rates[i] = 1.0
        elif renewable_availability > 0.6:  # High renewable availability
            charging_rates[i] = 0.8
        elif electricity_price < price_threshold and soc < 0.8:  # Low price opportunity
            charging_rates[i] = 0.6
        elif time_until_departure < 5 and soc < 0.9:  # Approaching departure
            charging_rates[i] = 0.4
        elif grid_load > 0.8:  # High grid load
            charging_rates[i] = 0.1
        elif soc < 0.6:  # Normal charging
            charging_rates[i] = 0.3
    
    return charging_rates

def main():
    # Create environment with 10 EVs
    env = GridEdgeEnv(
        num_evs=10,
        render_mode="human",
        window_size=(1024, 768)
    )
    
    # Reset environment
    observation, info = env.reset()
    
    # Run simulation indefinitely (until user interrupts)
    try:
        while True:
            # Get charging decisions from the smart charging policy
            action = smart_charging_policy(observation, env.num_evs)
            
            # Step environment
            observation, reward, terminated, truncated, info = env.step(action)
            
            # Print current metrics
            print(f"\rTime: {int(env.current_hour):02d}:{int((env.current_hour % 1) * 60):02d} | "
                  f"Renewable: {info['renewable_availability']:.2f} | "
                  f"Price: ${info['price']:.2f}/kWh | "
                  f"Load: {info['total_load']:.1f} kW | "
                  f"Reward: {reward:.2f}", end="")
            
            # Render environment
            env.render()
            
            # Add delay to make visualization easier to follow
            time.sleep(0.5)
            
            # Check if episode is done
            if terminated or truncated:
                observation, info = env.reset()
                
    except KeyboardInterrupt:
        print("\nSimulation stopped by user")
    finally:
        env.close()

if __name__ == "__main__":
    main() 