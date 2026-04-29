/**
 * Hook: useFavoriteRoutes
 * Manages favorite routes in localStorage (max 10, LRU eviction)
 */

import { useState, useCallback, useEffect } from 'react';
import type { Route } from '../utils/algorithms';

const STORAGE_KEY = 'algiers_fav_routes';
const MAX_FAVORITES = 10;

interface FavoriteRoute {
  route: Route;
  savedAt: string;
  fromName: string;
  toName: string;
}

export function useFavoriteRoutes() {
  const [favorites, setFavorites] = useState<FavoriteRoute[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
    } catch { /* ignore */ }
  }, [favorites]);

  const addFavorite = useCallback((route: Route) => {
    setFavorites(prev => {
      const exists = prev.some(f => f.route.id === route.id);
      if (exists) return prev;

      const fromName = route.segments[0]?.fromName || 'Unknown';
      const toName = route.segments[route.segments.length - 1]?.toName || 'Unknown';
      const newFav: FavoriteRoute = {
        route,
        savedAt: new Date().toISOString(),
        fromName,
        toName,
      };

      const updated = [newFav, ...prev];
      if (updated.length > MAX_FAVORITES) updated.pop(); // LRU eviction
      return updated;
    });
  }, []);

  const removeFavorite = useCallback((routeId: string) => {
    setFavorites(prev => prev.filter(f => f.route.id !== routeId));
  }, []);

  const isFavorite = useCallback((routeId: string) => {
    return favorites.some(f => f.route.id === routeId);
  }, [favorites]);

  return { favorites, addFavorite, removeFavorite, isFavorite };
}
