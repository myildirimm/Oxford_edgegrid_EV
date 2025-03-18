import osmnx as ox
import networkx as nx
import folium
from folium import plugins
import numpy as np
import random
from datetime import datetime, timedelta

class Vehicle:
    def __init__(self, vehicle_id, position, battery_capacity=60.0):  # 60 kWh battery
        self.id = vehicle_id
        self.position = position  # (lat, lon)
        self.battery_capacity = battery_capacity
        self.battery_level = random.uniform(0.6, 0.9) * battery_capacity  # Start with 60-90% charge
        self.route = []
        self.charging = False
        self.next_destination = None
        self.route_nodes = []  # Store the route as graph nodes
        self.current_route_index = 0
        self.speed = 30  # km/h average speed
        self.energy_consumption = 0.02  # Reduced from 0.05 to 0.02 kWh per km for slower discharge
        self.progress = 0.0  # Progress between current and next point (0.0 to 1.0)
        self.stranded = False  # New flag to indicate if vehicle has run out of battery
        # Assign a unique color to each vehicle with more distinct colors
        colors = [
            '#FF0000',  # Red
            '#00FF00',  # Lime
            '#0000FF',  # Blue
            '#FF00FF',  # Magenta
            '#00FFFF',  # Cyan
            '#FFA500',  # Orange
            '#800080',  # Purple
            '#008000',  # Green
            '#000080',  # Navy
            '#FF1493',  # Deep Pink
            '#4B0082',  # Indigo
            '#FF4500',  # Orange Red
            '#2E8B57',  # Sea Green
            '#8B4513',  # Saddle Brown
            '#483D8B'   # Dark Slate Blue
        ]
        self.color = colors[int(vehicle_id.split('_')[1]) % len(colors)]  # Use vehicle ID to pick color

class ChargingStation:
    def __init__(self, station_id, position, capacity=50.0):  # 50 kW charging capacity
        self.id = station_id
        self.position = position  # (lat, lon)
        self.capacity = capacity
        self.available = True
        self.current_vehicle = None

class PowerPlant:
    def __init__(self, plant_id, position, capacity=10000.0):  # 10 MW capacity
        self.id = plant_id
        self.position = position  # (lat, lon)
        self.capacity = capacity
        self.current_output = 0.0

class SolarPanel:
    def __init__(self, panel_id, position, capacity=100.0):  # 100 kW capacity
        self.id = panel_id
        self.position = position  # (lat, lon)
        self.capacity = capacity
        self.current_output = 0.0

class OxfordCitySimulation:
    def __init__(self):
        # Oxford city center coordinates
        self.center_lat = 51.7520
        self.center_lon = -1.2577
        
        # Initialize city graph
        self.city_graph = ox.graph_from_point(
            (self.center_lat, self.center_lon),
            dist=3000,  # 3km radius
            network_type='drive'
        )
        
        # Convert graph to projected graph for accurate distance calculations
        self.projected_graph = ox.project_graph(self.city_graph)
        
        # Initialize components
        self.vehicles = []
        self.charging_stations = []
        self.power_plants = []
        self.solar_panels = []
        
        # Initialize map
        self.map = None
        self.setup_map()
        self.setup_infrastructure()
        
        # Store nodes for route planning
        self.nodes = list(self.city_graph.nodes())
    
    def setup_map(self):
        """Initialize the map centered on Oxford"""
        self.map = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=14,
            tiles='cartodbpositron'
        )
        
    def setup_infrastructure(self):
        """Set up charging stations, power plant, and solar panels"""
        # Add charging stations at key locations
        charging_locations = [
            (51.7520, -1.2577),  # City center
            (51.7540, -1.2600),  # Near train station
            (51.7500, -1.2500),  # East Oxford
            (51.7480, -1.2620),  # West Oxford
            (51.7560, -1.2540)   # North Oxford
        ]
        
        for i, loc in enumerate(charging_locations):
            station = ChargingStation(f"CS_{i}", loc)
            self.charging_stations.append(station)
        
        # Add power plant
        self.power_plants.append(
            PowerPlant("PP_1", (51.7420, -1.2677))  # South Oxford
        )
        
        # Add solar panels
        solar_locations = [
            (51.7510, -1.2590),
            (51.7530, -1.2520),
            (51.7490, -1.2550),
            (51.7515, -1.2600)
        ]
        
        for i, loc in enumerate(solar_locations):
            panel = SolarPanel(f"SP_{i}", loc)
            self.solar_panels.append(panel)
    
    def add_vehicles(self, num_vehicles):
        """Add vehicles to the simulation"""
        nodes = list(self.city_graph.nodes())
        for i in range(num_vehicles):
            node = random.choice(nodes)
            pos = (
                self.city_graph.nodes[node]['y'],
                self.city_graph.nodes[node]['x']
            )
            vehicle = Vehicle(f"V_{i}", pos)
            self.vehicles.append(vehicle)
    
    def get_random_route(self, start_node):
        """Generate a random route for a vehicle"""
        try:
            end_node = random.choice(self.nodes)
            route = nx.shortest_path(
                self.city_graph,
                start_node,
                end_node,
                weight='length'
            )
            return route
        except nx.NetworkXNoPath:
            return None
    
    def get_node_coordinates(self, node):
        """Get coordinates for a node"""
        return (
            self.city_graph.nodes[node]['y'],
            self.city_graph.nodes[node]['x']
        )
    
    def update_vehicle_positions(self):
        """Update vehicle positions based on their routes"""
        print(f"Updating positions for {len(self.vehicles)} vehicles")  # Debug print
        
        for vehicle in self.vehicles:
            if vehicle.charging or vehicle.stranded:
                status = "charging" if vehicle.charging else "stranded"
                print(f"Vehicle {vehicle.id} is {status}")  # Debug print
                continue
                
            # If vehicle has no route or has completed current route
            if not vehicle.route_nodes or vehicle.current_route_index >= len(vehicle.route_nodes) - 1:
                print(f"Vehicle {vehicle.id} needs new route")  # Debug print
                # Find closest node to vehicle's current position
                closest_node = ox.nearest_nodes(
                    self.city_graph,
                    vehicle.position[1],  # lon
                    vehicle.position[0]   # lat
                )
                
                # If vehicle needs charging, route to nearest charging station
                if vehicle.battery_level < 0.3 * vehicle.battery_capacity:  # Increased threshold to 30%
                    print(f"Vehicle {vehicle.id} needs charging")  # Debug print
                    nearest_station = self.find_nearest_charging_station(vehicle)
                    if nearest_station and nearest_station.available:
                        print(f"Vehicle {vehicle.id} found charging station {nearest_station.id}")  # Debug print
                        end_node = ox.nearest_nodes(
                            self.city_graph,
                            nearest_station.position[1],  # lon
                            nearest_station.position[0]   # lat
                        )
                        try:
                            route = nx.shortest_path(
                                self.city_graph,
                                closest_node,
                                end_node,
                                weight='length'
                            )
                            # Calculate if vehicle can make it to the charging station
                            total_distance = sum(
                                ox.distance.great_circle_vec(
                                    lat1=self.city_graph.nodes[route[i]]['y'],
                                    lng1=self.city_graph.nodes[route[i]]['x'],
                                    lat2=self.city_graph.nodes[route[i+1]]['y'],
                                    lng2=self.city_graph.nodes[route[i+1]]['x']
                                )
                                for i in range(len(route)-1)
                            )
                            energy_needed = total_distance * vehicle.energy_consumption
                            
                            if energy_needed <= vehicle.battery_level:
                                vehicle.route_nodes = route
                                vehicle.route = [self.get_node_coordinates(node) for node in route]
                                vehicle.current_route_index = 0
                                vehicle.progress = 0.0
                                nearest_station.available = False  # Reserve the station
                                vehicle.next_destination = nearest_station
                                print(f"Vehicle {vehicle.id} heading to charging station {nearest_station.id}")
                            else:
                                print(f"Vehicle {vehicle.id} cannot reach charging station - insufficient battery")
                                self.get_new_random_route(vehicle, closest_node)
                        except nx.NetworkXNoPath:
                            print(f"No path found for vehicle {vehicle.id} to charging station")
                            self.get_new_random_route(vehicle, closest_node)
                    else:
                        self.get_new_random_route(vehicle, closest_node)
                else:
                    self.get_new_random_route(vehicle, closest_node)
            
            # Move along current route with interpolation
            if vehicle.route and vehicle.current_route_index < len(vehicle.route) - 1:
                current_pos = vehicle.route[vehicle.current_route_index]
                next_pos = vehicle.route[vehicle.current_route_index + 1]
                
                # Calculate energy needed for next step
                distance = ox.distance.great_circle_vec(
                    lat1=current_pos[0],
                    lng1=current_pos[1],
                    lat2=next_pos[0],
                    lng2=next_pos[1]
                )
                energy_needed = distance * vehicle.energy_consumption
                
                # Check if vehicle has enough battery to make the next move
                if energy_needed > vehicle.battery_level:
                    print(f"Vehicle {vehicle.id} has run out of battery and is stranded")
                    vehicle.stranded = True
                    continue
                
                # Update progress - increased for more noticeable movement
                vehicle.progress += 0.8  # Significantly increased speed for more noticeable movement
                
                if vehicle.progress >= 1.0:
                    print(f"Vehicle {vehicle.id} reached next point")  # Debug print
                    vehicle.current_route_index += 1
                    vehicle.progress = 0.0
                    vehicle.position = next_pos  # Update position to exact next point
                    
                    # Calculate energy consumption
                    energy_used = distance * vehicle.energy_consumption
                    vehicle.battery_level = max(0, vehicle.battery_level - energy_used)  # Prevent negative battery
                    print(f"Vehicle {vehicle.id} battery: {vehicle.battery_level:.1f} kWh")  # Debug print
                    
                    # Check if vehicle has reached charging station
                    if vehicle.next_destination and vehicle.current_route_index >= len(vehicle.route_nodes) - 1:
                        station = vehicle.next_destination
                        if isinstance(station, ChargingStation):
                            print(f"Vehicle {vehicle.id} arrived at charging station {station.id}")
                            vehicle.charging = True
                            station.current_vehicle = vehicle
                            vehicle.next_destination = None
                else:
                    # Interpolate position
                    vehicle.position = (
                        current_pos[0] + (next_pos[0] - current_pos[0]) * vehicle.progress,
                        current_pos[1] + (next_pos[1] - current_pos[1]) * vehicle.progress
                    )
                    print(f"Vehicle {vehicle.id} at position {vehicle.position}")  # Debug print
    
    def get_new_random_route(self, vehicle, start_node):
        """Helper method to get a new random route for a vehicle"""
        new_route = self.get_random_route(start_node)
        if new_route:
            print(f"Vehicle {vehicle.id} got new random route with {len(new_route)} nodes")
            vehicle.route_nodes = new_route
            vehicle.current_route_index = 0
            vehicle.progress = 0.0
            vehicle.route = [self.get_node_coordinates(node) for node in new_route]
            if vehicle.route:
                vehicle.position = vehicle.route[0]
    
    def find_nearest_charging_station(self, vehicle):
        """Find the nearest available charging station"""
        available_stations = [s for s in self.charging_stations if s.available]
        if not available_stations:
            return None
            
        # Calculate distances using unpacked coordinates
        distances = [
            ox.distance.great_circle_vec(
                lat1=vehicle.position[0],
                lng1=vehicle.position[1],
                lat2=station.position[0],
                lng2=station.position[1]
            )
            for station in available_stations
        ]
        return available_stations[np.argmin(distances)]
    
    def update_charging_stations(self):
        """Update charging station status"""
        for station in self.charging_stations:
            if station.current_vehicle:
                vehicle = station.current_vehicle
                charge_amount = min(
                    station.capacity * 0.016,  # Amount per minute (kWh)
                    vehicle.battery_capacity - vehicle.battery_level
                )
                vehicle.battery_level += charge_amount
                print(f"Vehicle {vehicle.id} charging at station {station.id}, battery: {vehicle.battery_level:.1f} kWh")
                
                # When battery is sufficiently charged
                if vehicle.battery_level >= 0.8 * vehicle.battery_capacity:
                    print(f"Vehicle {vehicle.id} finished charging, finding new route")
                    vehicle.charging = False
                    station.available = True
                    station.current_vehicle = None
                    
                    # Find closest node to current position for new route
                    closest_node = ox.nearest_nodes(
                        self.city_graph,
                        station.position[1],  # lon
                        station.position[0]   # lat
                    )
                    
                    # Get new random route for the vehicle
                    self.get_new_random_route(vehicle, closest_node)
                    print(f"Vehicle {vehicle.id} starting new route with {len(vehicle.route_nodes)} nodes")
    
    def update_power_sources(self):
        """Update power plant and solar panel outputs"""
        # Simple day/night cycle for solar panels
        hour = datetime.now().hour
        solar_efficiency = max(0, np.sin(np.pi * (hour - 6) / 12))  # Peak at noon
        
        for panel in self.solar_panels:
            panel.current_output = panel.capacity * solar_efficiency
        
        # Update power plant output based on demand
        total_charging_demand = sum(
            station.capacity for station in self.charging_stations
            if station.current_vehicle
        )
        total_solar_output = sum(panel.current_output for panel in self.solar_panels)
        
        for plant in self.power_plants:
            plant.current_output = max(0, total_charging_demand - total_solar_output)
    
    def visualize(self):
        """Create visualization of the current state"""
        self.setup_map()
        
        # Add legend with dynamic vehicle colors
        legend_html = '''
        <div style="position: fixed; 
                    top: 10px; 
                    right: 10px; 
                    z-index: 1000; 
                    background-color: white; 
                    padding: 10px; 
                    border-radius: 5px; 
                    border: 2px solid gray;
                    font-size: 14px;">
        '''
        # Add vehicle-specific legend entries
        for vehicle in self.vehicles:
            battery_percent = (vehicle.battery_level / vehicle.battery_capacity) * 100
            legend_html += f'''
            <div style="margin-bottom: 5px;">
                <span style="color: {vehicle.color};">{'🔋' if vehicle.charging else '🚙'}</span> 
                Vehicle {vehicle.id} - {battery_percent:.1f}% {' (Charging)' if vehicle.charging else ''}
            </div>
            '''
        
        # Add other legend items
        legend_html += '''
            <div style="margin-bottom: 5px;"><span style="color: green;">⚡</span> Available Stations</div>
            <div style="margin-bottom: 5px;"><span style="color: red;">🔌</span> Occupied Stations</div>
            <div style="margin-bottom: 5px;"><span style="color: black;">🏭</span> Power Plant</div>
            <div><span style="color: #FFD700;">☀️</span> Solar Panels</div>
        </div>
        '''
        self.map.get_root().html.add_child(folium.Element(legend_html))
        
        # Add road network using folium directly
        edges = ox.graph_to_gdfs(self.city_graph, nodes=False, edges=True)
        folium.GeoJson(
            edges,
            style_function=lambda x: {
                'color': 'gray',
                'weight': 2,
                'opacity': 0.6
            }
        ).add_to(self.map)
        
        # Add charging stations
        for station in self.charging_stations:
            color = 'red' if not station.available else 'green'
            icon = '🔌' if not station.available else '⚡'
            icon_html = f'''
                <div style="font-size: 24px; text-align: center;">
                    <span style="color: {color};">{icon}</span>
                </div>
            '''
            folium.DivIcon(
                html=icon_html
            ).add_to(folium.Marker(
                location=station.position,
                popup=f"""
                <b>Charging Station {station.id}</b><br>
                Status: {'Occupied' if not station.available else 'Available'}<br>
                Capacity: {station.capacity} kW
                """
            ).add_to(self.map))
        
        # Add vehicles and their routes
        for vehicle in self.vehicles:
            # Draw vehicle route if it exists
            if vehicle.route and len(vehicle.route) > vehicle.current_route_index:
                remaining_route = vehicle.route[vehicle.current_route_index:]
                route_coords = [(pos[0], pos[1]) for pos in remaining_route]
                folium.PolyLine(
                    route_coords,
                    weight=3,  # Made route lines thicker
                    color=vehicle.color,  # Use vehicle's color for route
                    opacity=0.8
                ).add_to(self.map)
            
            # Draw vehicle with appropriate icon in vehicle's color
            battery_percent = (vehicle.battery_level / vehicle.battery_capacity) * 100
            route_progress = (vehicle.current_route_index / len(vehicle.route_nodes) * 100) if vehicle.route_nodes else 0
            
            # Choose appropriate icon based on vehicle state
            if vehicle.stranded:
                icon = '⚠️'  # Warning sign for stranded vehicles
            else:
                icon = '🔋' if vehicle.charging else '🚙'
            
            # Define status message
            if vehicle.stranded:
                status = "Out of battery!"
            elif vehicle.charging:
                status = f"Charging at {vehicle.battery_level:.1f} kWh"
            else:
                status = "Moving"
            
            # Create marker with colored icon
            icon_html = f'''
                <div style="font-size: 24px; text-align: center;">
                    <span style="color: {vehicle.color};">{icon}</span>
                </div>
            '''
            folium.DivIcon(
                html=icon_html
            ).add_to(folium.Marker(
                location=vehicle.position,
                popup=f"""
                <b>Vehicle {vehicle.id}</b><br>
                Battery: {battery_percent:.1f}%<br>
                Status: {status}<br>
                Route Progress: {route_progress:.1f}%
                """
            ).add_to(self.map))
        
        # Add power plant with factory emoji
        for plant in self.power_plants:
            icon_html = '''
                <div style="font-size: 24px; text-align: center;">
                    <span style="color: black;">🏭</span>
                </div>
            '''
            folium.DivIcon(
                html=icon_html
            ).add_to(folium.Marker(
                location=plant.position,
                popup=f"""
                <b>Power Plant {plant.id}</b><br>
                Output: {plant.current_output:.1f} kW<br>
                Capacity: {plant.capacity:.1f} kW
                """
            ).add_to(self.map))
        
        # Add solar panels with sun emoji
        for panel in self.solar_panels:
            icon_html = '''
                <div style="font-size: 24px; text-align: center;">
                    <span style="color: #FFD700;">☀️</span>
                </div>
            '''
            folium.DivIcon(
                html=icon_html
            ).add_to(folium.Marker(
                location=panel.position,
                popup=f"""
                <b>Solar Panel {panel.id}</b><br>
                Output: {panel.current_output:.1f} kW<br>
                Capacity: {panel.capacity:.1f} kW
                """
            ).add_to(self.map))
        
        return self.map
    
    def run_simulation_step(self):
        """Run one step of the simulation"""
        self.update_vehicle_positions()
        self.update_charging_stations()
        self.update_power_sources()
        return self.visualize()

# Example usage
if __name__ == "__main__":
    simulation = OxfordCitySimulation()
    simulation.add_vehicles(10)
    
    # Run simulation for a few steps
    for _ in range(5):
        map_view = simulation.run_simulation_step()
        # Save the map to an HTML file
        map_view.save(f"oxford_simulation_step_{_}.html") 