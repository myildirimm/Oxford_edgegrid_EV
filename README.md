# Electric Vehicle Charging Simulation in Oxford

This project simulates electric vehicles moving around Oxford city, managing their battery levels, and interacting with charging stations. The simulation includes power plants and solar panels to model the energy infrastructure.

## Features

- Real-time visualization of vehicles moving through Oxford's road network
- Dynamic battery management and charging station interactions
- Realistic vehicle movement with energy consumption
- Power infrastructure simulation including charging stations, power plants, and solar panels
- Interactive map with vehicle routes and infrastructure locations
- Vehicle status monitoring including battery levels and charging states

## Requirements

- Python 3.8+
- Required packages listed in `requirements.txt`

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/oxford-ev-simulation.git
cd oxford-ev-simulation
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the simulation:
```bash
python city_simulation.py
```

The simulation will:
1. Create a map of Oxford city center
2. Initialize vehicles, charging stations, power plants, and solar panels
3. Run the simulation steps
4. Generate HTML files for each simulation step showing the current state

## Simulation Components

### Vehicles
- Simulated electric vehicles with realistic battery consumption
- Dynamic route planning and charging station seeking behavior
- Visual indicators for vehicle status (moving, charging, stranded)

### Charging Stations
- Multiple charging stations across the city
- Dynamic availability status
- Charging speed and capacity limitations

### Power Infrastructure
- Power plants with variable output
- Solar panels with day/night cycle efficiency
- Real-time power demand and supply simulation

## Visualization

The simulation creates an interactive map showing:
- Vehicles with their current routes and status
- Charging stations (available/occupied)
- Power plants and solar panels
- Real-time battery levels and charging status
- Color-coded vehicle routes

## Contributing

Feel free to submit issues and enhancement requests! 