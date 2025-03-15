import pygame
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class EVState:
    soc: float  # State of Charge [0,1]
    time_until_departure: float  # Hours until departure
    charging_power_limit: float  # kW
    preferred_cost_threshold: float  # $/kWh

class GridEdgeEnv(gym.Env):
    """
    A PyGame-based environment for coordinating EV charging schedules.
    """
    
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}
    
    def __init__(
        self,
        num_evs: int = 10,
        render_mode: Optional[str] = None,
        window_size: Tuple[int, int] = (1024, 768)
    ):
        super().__init__()
        
        # Environment parameters
        self.num_evs = num_evs
        self.max_charging_power = 22.0  # kW (fast charger)
        self.transformer_capacity = self.num_evs * 7.0  # kW (assumed capacity)
        self.base_electricity_price = 0.15  # $/kWh
        self.peak_price_multiplier = 3.0
        
        # Time simulation
        self.current_hour = 0.0  # 24-hour format
        self.renewable_availability = 0.0
        self.current_load = 0.0  # Track current load
        
        # Initialize EV states
        self.ev_states = []
        
        # Colors
        self.COLORS = {
            'background': (240, 240, 240),
            'text': (50, 50, 50),
            'ev': (100, 149, 237),  # Cornflower blue
            'grid_ok': (46, 204, 113),  # Emerald green
            'grid_warning': (231, 76, 60),  # Pomegranate red
            'renewable': (241, 196, 15),  # Sun yellow
            'price': (255, 165, 0),  # Orange
            'grid': (200, 200, 200)
        }
        
        # Action and observation spaces (rest of the init remains the same)
        self.action_space = spaces.Box(
            low=0,
            high=1,
            shape=(self.num_evs,),
            dtype=np.float32
        )
        
        self.observation_space = spaces.Box(
            low=0,
            high=1,
            shape=(self.num_evs * 4 + 4,),  # 4 states per EV + 4 global states
            dtype=np.float32
        )
        
        # PyGame setup
        self.window_size = window_size
        self.render_mode = render_mode
        self.window = None
        self.clock = None
        self.font = None
        
        # Initialize state
        self.reset()
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # Reset time
        self.current_hour = np.random.uniform(0, 24)
        
        # Reset EV states
        self.ev_states = [
            EVState(
                soc=np.random.uniform(0.2, 0.8),
                time_until_departure=np.random.uniform(1, 24),
                charging_power_limit=np.random.choice([3.7, 7.4, 22.0]),
                preferred_cost_threshold=np.random.uniform(0.2, 0.4)
            )
            for _ in range(self.num_evs)
        ]
        
        # Reset grid conditions
        self.renewable_availability = self._calculate_renewable_availability()
        
        # Initialize rendering
        if self.render_mode == "human":
            self._init_render()
            
        return self._get_observation(), {}
    
    def _calculate_renewable_availability(self):
        # Simulate solar availability based on time of day
        hour = self.current_hour
        if 6 <= hour <= 18:  # Daylight hours
            solar = np.sin(np.pi * (hour - 6) / 12) * 0.8
            return max(0, solar + np.random.normal(0, 0.1))
        return max(0, np.random.normal(0, 0.1))  # Small random availability at night
    
    def _calculate_electricity_price(self):
        # Base price modified by time of day and renewable availability
        hour = self.current_hour
        is_peak = (9 <= hour <= 12) or (17 <= hour <= 20)
        price = self.base_electricity_price
        if is_peak:
            price *= self.peak_price_multiplier
        # Discount when renewables are available
        price *= (1 - 0.3 * self.renewable_availability)
        return price
    
    def _calculate_total_load(self, charging_rates):
        return np.sum([rate * ev.charging_power_limit 
                      for rate, ev in zip(charging_rates, self.ev_states)])
    
    def step(self, action):
        # Update time (15-minute intervals)
        self.current_hour = (self.current_hour + 0.25) % 24
        
        # Update renewable availability
        self.renewable_availability = self._calculate_renewable_availability()
        
        # Calculate electricity price
        current_price = self._calculate_electricity_price()
        
        # Apply charging actions and calculate total load
        charging_rates = np.clip(action, 0, 1)
        self.current_load = self._calculate_total_load(charging_rates)  # Store current load
        
        # Update EV states
        reward = 0
        for i, (ev, rate) in enumerate(zip(self.ev_states, charging_rates)):
            # Update SOC (assuming 100 kWh battery)
            energy_charged = rate * ev.charging_power_limit * 0.25  # 15-minute interval
            ev.soc = min(1.0, ev.soc + energy_charged / 100.0)
            
            # Update time until departure
            ev.time_until_departure -= 0.25
            
            # Calculate individual EV reward
            reward += self._calculate_ev_reward(ev, rate, current_price, self.current_load)
            
            # Reset if departed
            if ev.time_until_departure <= 0:
                ev.soc = np.random.uniform(0.2, 0.8)
                ev.time_until_departure = np.random.uniform(1, 24)
        
        # Check termination conditions
        terminated = False
        truncated = False
        
        return self._get_observation(), reward, terminated, truncated, {
            "total_load": self.current_load,
            "price": current_price,
            "renewable_availability": self.renewable_availability
        }
    
    def _calculate_ev_reward(self, ev: EVState, charging_rate: float, price: float, total_load: float):
        reward = 0
        
        # Cost incentive
        charging_cost = charging_rate * ev.charging_power_limit * price * 0.25
        reward -= charging_cost
        
        # Departure readiness
        if ev.time_until_departure <= 0.5 and ev.soc < 0.8:
            reward -= 10.0  # Heavy penalty for not being ready
        
        # Grid stability
        if total_load > self.transformer_capacity:
            reward -= 5.0
        
        # Renewable energy utilization
        if charging_rate > 0:
            reward += 2.0 * self.renewable_availability * charging_rate
        
        # Price sensitivity
        if price > ev.preferred_cost_threshold and charging_rate > 0.2:
            reward -= 1.0
        
        return reward
    
    def _get_observation(self):
        # Compile all state information
        ev_states = []
        for ev in self.ev_states:
            ev_states.extend([
                ev.soc,
                ev.time_until_departure / 24.0,  # Normalize to [0,1]
                ev.charging_power_limit / 22.0,  # Normalize to [0,1]
                ev.preferred_cost_threshold / 0.5  # Normalize to [0,1]
            ])
        
        # Add global states
        global_states = [
            self.current_hour / 24.0,  # Normalize to [0,1]
            self._calculate_electricity_price() / (self.base_electricity_price * self.peak_price_multiplier),
            self.renewable_availability,
            self._calculate_total_load(np.zeros(self.num_evs)) / self.transformer_capacity
        ]
        
        return np.array(ev_states + global_states, dtype=np.float32)
    
    def render(self):
        if self.render_mode is None:
            return
            
        if self.window is None:
            self._init_render()
            
        # Clear screen
        self.window.fill(self.COLORS['background'])
        
        # Draw title and time
        self._draw_text("EV Charging Coordination", (self.window_size[0]//2, 30), 
                       centered=True, size='large')
        
        hours = int(self.current_hour)
        minutes = int((self.current_hour % 1) * 60)
        time_str = f"Time: {hours:02d}:{minutes:02d}"
        self._draw_text(time_str, (self.window_size[0] - 150, 30))
        
        # Draw grid metrics
        self._draw_grid_metrics()
        
        # Draw EVs
        self._draw_evs()
        
        # Draw legend
        self._draw_legend()
        
        if self.render_mode == "human":
            pygame.display.flip()
            self.clock.tick(self.metadata["render_fps"])
            
        return np.transpose(
            np.array(pygame.surfarray.pixels3d(self.window)), axes=(1, 0, 2)
        )
    
    def _init_render(self):
        pygame.init()
        pygame.display.init()
        self.window = pygame.display.set_mode(self.window_size)
        pygame.display.set_caption("EV Charging Coordination")
        self.clock = pygame.time.Clock()
        self.font = {
            'small': pygame.font.Font(None, 24),
            'medium': pygame.font.Font(None, 36),
            'large': pygame.font.Font(None, 48)
        }
    
    def _draw_text(self, text, position, color=None, centered=False, size='small'):
        if color is None:
            color = self.COLORS['text']
        
        text_surface = self.font[size].render(text, True, color)
        text_rect = text_surface.get_rect()
        
        if centered:
            text_rect.center = position
        else:
            text_rect.topleft = position
            
        self.window.blit(text_surface, text_rect)
    
    def _draw_grid_metrics(self):
        # Draw grid metrics section background
        metrics_rect = pygame.Rect(50, self.window_size[1] - 200, 400, 150)
        pygame.draw.rect(self.window, self.COLORS['grid'], metrics_rect, border_radius=10)
        
        # Draw section title
        self._draw_text("Grid Metrics", (metrics_rect.centerx, metrics_rect.top + 20), 
                       centered=True, size='medium')
        
        # Calculate positions for metrics
        left_margin = metrics_rect.left + 40
        bar_width = 40
        bar_spacing = 120
        
        # Draw renewable availability
        renewable_height = int(self.renewable_availability * 100)
        self._draw_text("Renewable", (left_margin, metrics_rect.bottom - 130))
        self._draw_text(f"{self.renewable_availability:.2f}", (left_margin, metrics_rect.bottom - 100))
        pygame.draw.rect(
            self.window,
            self.COLORS['renewable'],
            (left_margin, metrics_rect.bottom - 20 - renewable_height, bar_width, renewable_height)
        )
        
        # Draw price indicator
        price = self._calculate_electricity_price()
        price_height = int((price / (self.base_electricity_price * self.peak_price_multiplier)) * 100)
        self._draw_text("Price", (left_margin + bar_spacing, metrics_rect.bottom - 130))
        self._draw_text(f"${price:.2f}/kWh", (left_margin + bar_spacing, metrics_rect.bottom - 100))
        pygame.draw.rect(
            self.window,
            self.COLORS['price'],
            (left_margin + bar_spacing, metrics_rect.bottom - 20 - price_height, bar_width, price_height)
        )
        
        # Draw load indicator using current_load
        load_height = int((self.current_load / self.transformer_capacity) * 100)
        load_color = self.COLORS['grid_ok'] if self.current_load <= self.transformer_capacity else self.COLORS['grid_warning']
        self._draw_text("Grid Load", (left_margin + 2 * bar_spacing, metrics_rect.bottom - 130))
        self._draw_text(f"{self.current_load:.1f}/{self.transformer_capacity:.1f} kW", 
                       (left_margin + 2 * bar_spacing, metrics_rect.bottom - 100))
        pygame.draw.rect(
            self.window,
            load_color,
            (left_margin + 2 * bar_spacing, metrics_rect.bottom - 20 - load_height, bar_width, load_height)
        )
    
    def _draw_evs(self):
        ev_section = pygame.Rect(50, 100, self.window_size[0] - 100, self.window_size[1] - 350)
        pygame.draw.rect(self.window, self.COLORS['grid'], ev_section, border_radius=10)
        
        # Draw section title
        self._draw_text("Electric Vehicles", (ev_section.centerx, ev_section.top + 20),
                       centered=True, size='medium')
        
        # Calculate layout
        spacing = (ev_section.width - 100) // self.num_evs
        bar_width = 40
        bar_max_height = 200  # Fixed maximum height for bars
        base_y = ev_section.bottom - 70  # Moved up slightly to make room for labels
        
        # Draw scale on the left
        scale_x = ev_section.left + 20
        for i in range(11):  # Draw scale from 0 to 1.0
            y = base_y - (i * bar_max_height // 10)
            value = i / 10
            if i % 2 == 0:  # Draw every other label to avoid crowding
                self._draw_text(f"{value:.1f}", (scale_x, y - 8))
            # Draw tick mark
            pygame.draw.line(self.window, self.COLORS['text'], 
                           (scale_x + 20, y), (scale_x + 25, y), 1)
        
        # Draw EVs
        for i, ev in enumerate(self.ev_states):
            x = ev_section.left + 50 + i * spacing
            
            # Draw background bar (empty)
            pygame.draw.rect(
                self.window,
                self.COLORS['grid'],
                (x, base_y - bar_max_height, bar_width, bar_max_height),
                1  # Draw outline only
            )
            
            # Draw SOC bar
            height = int(ev.soc * bar_max_height)
            pygame.draw.rect(
                self.window,
                self.COLORS['ev'],
                (x, base_y - height, bar_width, height)
            )
            
            # Draw SOC value
            self._draw_text(f"SOC: {ev.soc:.2f}", (x, base_y - bar_max_height - 35))
            
            # Draw time until departure
            self._draw_text(f"Time: {ev.time_until_departure:.1f}h", (x, base_y - bar_max_height - 20))
            
            # Draw charging power limit
            self._draw_text(f"{ev.charging_power_limit:.1f}kW", (x, base_y - bar_max_height - 50))
            
            # Draw EV label
            self._draw_text(f"EV {i+1}", (x, base_y + 20))
            
        # Draw horizontal lines for better readability
        for i in range(11):
            y = base_y - (i * bar_max_height // 10)
            pygame.draw.line(self.window, self.COLORS['grid'], 
                           (ev_section.left + 45, y), 
                           (ev_section.right - 20, y), 
                           1)
    
    def _draw_legend(self):
        legend_items = [
            ("State of Charge", self.COLORS['ev']),
            ("Renewable Energy", self.COLORS['renewable']),
            ("Electricity Price", self.COLORS['price']),
            ("Grid Load", self.COLORS['grid_ok'])
        ]
        
        x = self.window_size[0] - 200
        y = 100
        
        for text, color in legend_items:
            pygame.draw.rect(self.window, color, (x, y, 20, 20))
            self._draw_text(text, (x + 30, y))
            y += 30
    
    def close(self):
        if self.window is not None:
            pygame.display.quit()
            pygame.quit() 