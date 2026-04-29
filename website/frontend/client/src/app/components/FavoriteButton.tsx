import { Heart } from 'lucide-react';
import { Route } from '../store/transit-store';
import { useFavoriteRoutes } from '../hooks/useFavoriteRoutes';
import { motion } from 'motion/react';

interface FavoriteButtonProps {
  route: Route;
}

export default function FavoriteButton({ route }: FavoriteButtonProps) {
  const { isFavorite, addFavorite, removeFavorite } = useFavoriteRoutes();
  const favorited = isFavorite(route.id);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (favorited) {
      removeFavorite(route.id);
    } else {
      addFavorite(route);
    }
  };

  return (
    <motion.button
      whileTap={{ scale: 0.9 }}
      onClick={handleClick}
      className="p-2 rounded-lg hover:bg-muted/50 transition-colors"
      aria-label={favorited ? 'Remove from favorites' : 'Add to favorites'}
    >
      <Heart
        className={`w-4 h-4 transition-all ${
          favorited ? 'fill-accent text-accent' : 'text-muted-foreground'
        }`}
      />
    </motion.button>
  );
}
