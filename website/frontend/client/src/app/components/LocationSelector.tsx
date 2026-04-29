import { MapPin, Navigation, X } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';
import { motion } from 'motion/react';

export default function LocationSelector() {
  const { startPoint, endPoint, setStartPoint, setEndPoint } = useTransitStore();

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <label className="text-xs text-muted-foreground uppercase tracking-wide">
          Journey Setup
        </label>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => {
            if (startPoint) {
              setStartPoint(null);
            }
          }}
          className={`
            w-full p-4 rounded-xl border-2 transition-all text-left
            ${startPoint
              ? 'border-primary/60 bg-gradient-to-r from-primary/20 to-primary/5'
              : 'border-dashed border-primary/40 bg-primary/5 hover:bg-primary/10 hover:border-primary/60'
            }
          `}
        >
          <div className="flex items-start gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{
                backgroundColor: startPoint ? '#C6B7E2' : 'rgba(198, 183, 226, 0.2)',
              }}
            >
              <MapPin
                className="w-5 h-5"
                style={{ color: startPoint ? '#0A1628' : '#C6B7E2' }}
              />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <p
                  className="font-medium"
                  style={{ color: startPoint ? '#C6B7E2' : 'rgba(198, 183, 226, 0.8)' }}
                >
                  Starting Point
                </p>
                {startPoint && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setStartPoint(null);
                    }}
                    className="p-1 rounded hover:bg-primary/20 transition-colors"
                  >
                    <X className="w-4 h-4" style={{ color: '#C6B7E2' }} />
                  </button>
                )}
              </div>
              {startPoint ? (
                <p className="text-xs text-muted-foreground">
                  Lat: {startPoint.lat.toFixed(4)}, Lng: {startPoint.lng.toFixed(4)}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Click on the map to set your starting location
                </p>
              )}
            </div>
          </div>
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => {
            if (endPoint) {
              setEndPoint(null);
            }
          }}
          className={`
            w-full p-4 rounded-xl border-2 transition-all text-left
            ${endPoint
              ? 'border-secondary/60 bg-gradient-to-r from-secondary/20 to-secondary/5'
              : 'border-dashed border-secondary/40 bg-secondary/5 hover:bg-secondary/10 hover:border-secondary/60'
            }
          `}
        >
          <div className="flex items-start gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{
                backgroundColor: endPoint ? '#F2C4CE' : 'rgba(242, 196, 206, 0.2)',
              }}
            >
              <Navigation
                className="w-5 h-5"
                style={{ color: endPoint ? '#0A1628' : '#F2C4CE' }}
              />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <p
                  className="font-medium"
                  style={{ color: endPoint ? '#F2C4CE' : 'rgba(242, 196, 206, 0.8)' }}
                >
                  Destination
                </p>
                {endPoint && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setEndPoint(null);
                    }}
                    className="p-1 rounded hover:bg-secondary/20 transition-colors"
                  >
                    <X className="w-4 h-4" style={{ color: '#F2C4CE' }} />
                  </button>
                )}
              </div>
              {endPoint ? (
                <p className="text-xs text-muted-foreground">
                  Lat: {endPoint.lat.toFixed(4)}, Lng: {endPoint.lng.toFixed(4)}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Click on the map to set your destination
                </p>
              )}
            </div>
          </div>
        </motion.button>
      </div>

      {startPoint && endPoint && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3 rounded-lg bg-gradient-to-r from-primary/10 to-secondary/10 border border-primary/20"
        >
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1 rounded-full bg-gradient-to-r from-primary to-secondary" />
          </div>
          <p className="text-xs text-center mt-2 text-muted-foreground">
            Route ready! Click "Find Routes" to see options
          </p>
        </motion.div>
      )}
    </div>
  );
}
