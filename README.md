# EV Charging Coordination Environment

A PyGame-based environment for coordinating electric vehicle (EV) charging using multi-agent reinforcement learning.

## Features

- Real-time visualization of EV charging states
- Dynamic electricity pricing based on time-of-day and renewable availability
- Grid load monitoring and transformer capacity constraints
- Smart charging policy considering multiple factors:
  - Renewable energy availability
  - Electricity prices
  - Grid stability
  - Individual EV constraints (departure time, charging power limits)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ev-charging-coordination.git
cd ev-charging-coordination
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the simulation:
```bash
python src/example.py
```

The visualization shows:
- Individual EV states (State of Charge, Time until departure, Charging power limit)
- Grid metrics (Renewable availability, Electricity price, Grid load)
- Real-time simulation of charging coordination

## Project Structure

```
.
├── src/
│   ├── environment.py    # Main environment implementation
│   └── example.py        # Example usage and visualization
├── tests/                # Test files
├── docs/                 # Documentation
├── requirements.txt      # Project dependencies
└── README.md            # This file
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 