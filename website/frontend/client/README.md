# Green Multi-Modal Public Transit Router

An intelligent route optimization system for public transportation that balances time, cost, and environmental impact.

## 🎯 Features

### Core Functionality
- **Interactive Map Interface**: Click to set start and end points
- **Multi-Modal Transportation**: Walk, Bus, Tram, and Metro support
- **Smart Route Optimization**: Adjustable weights for time, price, and CO₂ emissions
- **Real-time Visualization**: See routes overlaid on an interactive map
- **Comparative Analysis**: View multiple route options simultaneously

### User Interface
- **Modern SaaS Design**: Clean, minimal interface with smooth animations
- **Dark/Light Mode**: Toggle between themes
- **Responsive Layout**: Desktop and mobile optimized
- **Real-time Updates**: Live route recalculation based on priority changes

### Analytics
- **CO₂ Comparison Charts**: Visual comparison between routes
- **Transit vs. Car Analysis**: See environmental impact savings
- **Detailed Route Breakdown**: Step-by-step journey information
- **Transfer Warnings**: Alerts for excessive walking or transfers

## 🚀 Technology Stack

- **React** with TypeScript
- **Zustand** for state management
- **React Leaflet** for mapping
- **Recharts** for data visualization
- **Tailwind CSS** for styling
- **Motion** for animations
- **Lucide React** for icons

## 📦 Installation

```bash
# Install dependencies
pnpm install

# Start development server (already running)
# Preview is available in the Figma Make interface
```

## 🎨 Color Palette

- Main Background: `#0A1628` (Dark Blue)
- Accent Purple: `#C6B7E2`
- Accent Pink: `#F2C4CE`
- Accent Teal: `#BEEEDB`
- Accent Red: `#670627`

## 🏗️ Architecture

### Component Structure
```
App.tsx
├── ControlPanel
│   ├── TransportToggle
│   ├── WeightSliders
│   └── RouteCard (multiple)
├── MapView
│   ├── MapClickHandler
│   ├── RoutePolylines
│   └── Markers
├── RouteDetails
│   └── SegmentCard (multiple)
└── ChartPanel
    ├── CO₂ Comparison Chart
    └── Transit vs. Car Chart
```

### State Management
Centralized Zustand store managing:
- Start/end coordinates
- Route data
- User preferences (weights, transport modes)
- UI state (loading, selected route, theme)

## 🔌 Backend Integration

### API Endpoint
```typescript
POST /api/route
Content-Type: application/json

{
  "start": { "lat": 48.8566, "lng": 2.3522 },
  "end": { "lat": 48.8606, "lng": 2.3376 },
  "weights": {
    "time": 0.4,
    "price": 0.3,
    "co2": 0.3
  },
  "transportModes": {
    "walk": true,
    "bus": true,
    "tram": true,
    "metro": true
  }
}
```

### Expected Response
```typescript
{
  "routes": [
    {
      "id": "fastest",
      "name": "Fastest Route",
      "type": "fastest",
      "segments": [
        {
          "mode": "walk",
          "from": "Start",
          "to": "Metro Station",
          "duration": 5,
          "distance": 400,
          "cost": 0,
          "co2": 0,
          "coordinates": [
            { "lat": 48.8566, "lng": 2.3522 },
            // ... more coordinates
          ]
        }
        // ... more segments
      ],
      "totalTime": 24,
      "totalCost": 2.5,
      "totalCO2": 120,
      "totalDistance": 8750,
      "transfers": 1
    }
    // ... more routes
  ]
}
```

## 📝 Usage

1. **Set Points**: Click on the map to set start (purple marker) and end (pink marker) points
2. **Configure Preferences**: 
   - Toggle transport modes on/off
   - Adjust priority sliders (time/price/eco)
3. **Find Routes**: Click "Find Routes" button
4. **Compare Options**: Review the fastest, cheapest, and greenest routes
5. **View Details**: Select a route to see step-by-step directions
6. **Analyze Impact**: Check the charts for environmental comparison

## 🔄 Switching to Real Backend

Replace the mock data in `ControlPanel.tsx`:

```typescript
// Current (mock)
const mockRoutes = generateMockRoutes(startPoint, endPoint, weights, transportModes);
setRoutes(mockRoutes);

// Replace with (real API)
import { fetchRoutes } from '../utils/api';
const routes = await fetchRoutes(startPoint, endPoint, weights, transportModes);
setRoutes(routes);
```

## ⚡ Optimization Formula

Routes are scored using:
```
Cost(n) = w₁ × Time + w₂ × Price + w₃ × CO₂
```

Where:
- w₁, w₂, w₃ are normalized weights (sum = 1)
- Lower cost = better route

## 🎓 Built For

Academic project demonstrating:
- Modern frontend architecture
- Real-world UX/UI design
- Environmental awareness in tech
- Production-ready code quality

---

Built with 💚 for sustainable urban mobility
