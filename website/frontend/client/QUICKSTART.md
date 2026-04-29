# 🚀 Quick Start Guide

## Immediate Preview

The application is **already running** in your Figma Make preview panel! 

Simply look at the preview window to see the application live.

---

## How to Use (First Time)

### Step 1: Set Your Route
1. **Click** anywhere on the map → A **purple marker** appears (your start point)
2. **Click** another location → A **pink marker** appears (your destination)

### Step 2: Find Routes
1. Click the **"Find Routes"** button in the left sidebar
2. Wait for the loading animation (~1.5 seconds)
3. Three route options appear: Fastest, Cheapest, Greenest

### Step 3: Compare & Select
1. **Click** any route card to view details
2. See the route highlighted on the map
3. View step-by-step directions in the right panel (desktop)

### Step 4: Customize (Optional)
- **Adjust priorities**: Drag the Time/Price/CO₂ sliders
- **Quick presets**: Click Fastest/Cheapest/Greenest buttons
- **Toggle modes**: Enable/disable Walk/Bus/Tram/Metro
- **Save favorites**: Click the heart icon ❤️

---

## 🎨 Visual Guide

### Color Meanings
| Color | Meaning |
|-------|---------|
| 🟣 Purple (#C6B7E2) | Fastest route / Time priority |
| 🩷 Pink (#F2C4CE) | Cheapest route / Price priority |
| 🟢 Teal (#BEEEDB) | Greenest route / CO₂ priority |
| 🔴 Maroon (#670627) | Accent / Metro mode |

### Map Markers
- **Purple pin**: Start location
- **Pink pin**: End location
- **Colored lines**: Route paths (color = route type)

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + R` | Reset everything |
| `Ctrl/Cmd + D` | Toggle dark/light mode |
| `Ctrl/Cmd + 1` | Apply "Fastest" preset |
| `Ctrl/Cmd + 2` | Apply "Cheapest" preset |
| `Ctrl/Cmd + 3` | Apply "Greenest" preset |

**Tip**: Click the keyboard icon (bottom left) to see all shortcuts.

---

## 📱 Mobile vs Desktop

### Desktop Layout (1280px+)
- Left sidebar: Controls
- Center: Map
- Right panel: Route details + Charts

### Tablet Layout (1024px - 1279px)
- Left sidebar: Controls
- Right side: Map (full width)
- Bottom: Route details (swipe sheet)

### Mobile Layout (< 1024px)
- Top: Controls (collapsible)
- Center: Map
- Bottom: Swipe-up sheet (Details/Analytics tabs)

---

## 🔧 Development Commands

### Install Dependencies
```bash
pnpm install
```

### Run Development Server
The dev server is **already running** in Figma Make!

If you're running locally:
```bash
pnpm run dev
# Opens on http://localhost:5173
```

### Build for Production
```bash
pnpm run build
# Creates optimized build in /dist
```

---

## 🐛 Troubleshooting

### Map Not Loading?
- Check your internet connection (map tiles load from OpenStreetMap)
- Try refreshing the page

### Routes Not Appearing?
- Ensure both start and end points are set (purple + pink markers)
- Click "Find Routes" button
- Check that at least one transport mode is enabled

### Markers Not Appearing?
- Click directly on the map (not on UI elements)
- The first click sets start (purple), second sets end (pink)
- Third click resets start point

### Sliders Not Responding?
- They're working! The percentages always sum to 100%
- Try the preset buttons instead
- All three values are normalized automatically

---

## 📂 Project Structure Overview

```
src/
├── app/
│   ├── App.tsx                 ← Main application
│   ├── components/             ← UI components
│   ├── store/                  ← State management (Zustand)
│   ├── utils/                  ← Helper functions
│   └── hooks/                  ← Custom React hooks
├── styles/
│   ├── index.css               ← Global styles entry
│   ├── theme.css               ← Color theme
│   └── custom.css              ← Custom animations
└── [config files]
```

---

## 🎯 Testing the Demo

### Scenario 1: Quick Route
1. Click map twice (any two points)
2. Click "Find Routes"
3. Select any route
4. Export or share

**Time**: ~30 seconds

### Scenario 2: Eco-Friendly Journey
1. Set start and end points
2. Click "Greenest" preset
3. Compare CO₂ on chart
4. See environmental savings

**Time**: ~1 minute

### Scenario 3: Custom Optimization
1. Set points
2. Adjust sliders manually (e.g., 60% time, 30% price, 10% eco)
3. Find routes
4. Save favorite
5. Toggle dark mode

**Time**: ~2 minutes

---

## 🌐 Browser Support

### Fully Supported
- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers (iOS Safari, Chrome Android)

### Features by Browser
| Feature | Chrome | Firefox | Safari |
|---------|--------|---------|--------|
| Core app | ✅ | ✅ | ✅ |
| Web Share API | ✅ | ❌ | ✅ |
| Clipboard API | ✅ | ✅ | ✅ |
| LocalStorage | ✅ | ✅ | ✅ |

---

## 💾 Data Storage

### What's Saved?
- ✅ Favorite routes → Browser LocalStorage
- ✅ Persists across sessions
- ✅ Private to your browser

### What's NOT Saved?
- ❌ Current map position (resets on reload)
- ❌ Search history
- ❌ Theme preference (could be added)

---

## 🔌 Backend Integration (For Developers)

### Current State
- Using **mock data** (generated in browser)
- Simulates realistic routes

### To Connect Real Backend

1. **Implement API endpoint** at `/api/route`
2. **Update ControlPanel.tsx**:
   ```typescript
   // Line ~30-35
   // Replace:
   const mockRoutes = generateMockRoutes(startPoint, endPoint, weights, transportModes);
   setRoutes(mockRoutes);
   
   // With:
   import { fetchRoutes } from '../utils/api';
   const routes = await fetchRoutes(startPoint, endPoint, weights, transportModes);
   setRoutes(routes);
   ```
3. **Done!** Frontend automatically adapts.

See `src/app/utils/api.ts` for API contract details.

---

## 📊 What to Showcase in Demo

### Must-Show Features (Core)
1. ✅ Map interaction (click to set points)
2. ✅ Route finding
3. ✅ Route comparison
4. ✅ Weight sliders
5. ✅ CO₂ visualization

### Bonus Features (Impress Factor)
1. ✨ Quick presets
2. ✨ Dark mode toggle
3. ✨ Export/share
4. ✨ Keyboard shortcuts
5. ✨ Mobile responsive design
6. ✨ Favorite routes

---

## 🎓 For Academic Submission

### Included Documentation
- ✅ README.md (overview + technical)
- ✅ FEATURES.md (complete feature list)
- ✅ DEMO_GUIDE.md (presentation script)
- ✅ PROJECT_SUMMARY.md (comprehensive details)
- ✅ QUICKSTART.md (this file)

### Code Quality
- ✅ TypeScript throughout
- ✅ Component-based architecture
- ✅ Clean separation of concerns
- ✅ Reusable utilities
- ✅ Production-ready patterns

### Ready for Evaluation
- ✅ Runs immediately (no setup needed)
- ✅ Professional appearance
- ✅ All features functional
- ✅ Responsive design tested
- ✅ Documentation complete

---

## ❓ Common Questions

**Q: Can I change the map style?**  
A: Yes! Edit `MapView.tsx` and change the TileLayer URL. See Leaflet providers list.

**Q: Can I add more transport modes?**  
A: Yes! Update `TransportModes` interface in `transit-store.ts` and add to `TransportToggle.tsx`.

**Q: How do I change colors?**  
A: Edit `src/styles/theme.css` CSS variables. Colors are centralized there.

**Q: Can I deploy this?**  
A: Yes! Run `pnpm run build` and deploy the `dist/` folder to any static host (Vercel, Netlify, etc.).

**Q: Is the map data real?**  
A: Map tiles are real (OpenStreetMap). Route data is currently mock but follows realistic patterns.

---

## 🎉 You're Ready!

The application is **fully functional** and ready to demo right now.

**Next Steps**:
1. Explore the interface
2. Test all features
3. Read DEMO_GUIDE.md for presentation tips
4. Prepare your demo scenarios
5. Impress your audience! 🚀

---

**Need help?** All documentation is in the project root:
- Technical details → README.md
- Feature list → FEATURES.md
- Demo script → DEMO_GUIDE.md
- Overview → PROJECT_SUMMARY.md

**Happy routing! 🌿🚇🚌🚊**
