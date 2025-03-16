from flask import Flask, render_template_string
from city_simulation import OxfordCitySimulation
import threading
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Create a global simulation object and lock
simulation = OxfordCitySimulation()
simulation.add_vehicles(5)  # Reduced number of vehicles for better visibility
simulation_lock = threading.Lock()

# HTML template with faster refresh rate
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Oxford City Simulation</title>
    <meta http-equiv="refresh" content="1">  <!-- Refresh every 1 second to match simulation rate -->
    <style>
        body { margin: 0; }
        #map { height: 100vh; width: 100vw; }
    </style>
</head>
<body>
    {{ map_html|safe }}
</body>
</html>
"""

def run_simulation():
    """Background thread to run the simulation"""
    while True:
        try:
            with simulation_lock:
                logger.info("Updating simulation...")
                simulation.run_simulation_step()
                # Log vehicle positions for debugging
                for vehicle in simulation.vehicles:
                    logger.info(f"Vehicle {vehicle.id}: pos={vehicle.position}, charging={vehicle.charging}, battery={vehicle.battery_level:.1f}")
        except Exception as e:
            logger.error(f"Error in simulation thread: {e}")
        time.sleep(1)  # Update every second

@app.route('/')
def index():
    """Render the simulation visualization"""
    try:
        with simulation_lock:
            map_view = simulation.visualize()  # Only visualize, don't update
            return render_template_string(HTML_TEMPLATE, map_html=map_view._repr_html_())
    except Exception as e:
        logger.error(f"Error rendering map: {e}")
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    # Start the simulation in a background thread
    simulation_thread = threading.Thread(target=run_simulation, daemon=True)
    simulation_thread.start()
    
    # Run the Flask app
    app.run(debug=False, use_reloader=False)  # Disable debug mode to avoid multiple threads 