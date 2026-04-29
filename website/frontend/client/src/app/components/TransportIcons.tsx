import { Bus, Train, Footprints, TramFront, ArrowUpDown } from 'lucide-react';

export const getTransportIcon = (mode: string) => {
  switch (mode) {
    case 'walk':
      return Footprints;
    case 'bus':
      return Bus;
    case 'tram':
      return TramFront;
    case 'metro':
      return Train;
    case 'train':
      return Train;
    case 'escalator':
      return ArrowUpDown;
    default:
      return Footprints;
  }
};

export const getTransportColor = (mode: string) => {
  switch (mode) {
    case 'walk':
      return '#BEEEDB';
    case 'bus':
      return '#C6B7E2';
    case 'tram':
      return '#F2C4CE';
    case 'metro':
      return '#670627';
    case 'train':
      return '#4A90E2';
    case 'escalator':
      return '#95A5A6';
    default:
      return '#8ea9c1';
  }
};

export const getTransportLabel = (mode: string) => {
  switch (mode) {
    case 'walk':
      return 'Walk';
    case 'bus':
      return 'Bus';
    case 'tram':
      return 'Tram';
    case 'metro':
      return 'Metro';
    case 'train':
      return 'Train';
    case 'escalator':
      return 'Escalator';
    default:
      return mode;
  }
};
