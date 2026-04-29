import { Route, Coordinates, RouteSegment, Weights, TransportModes } from '../store/transit-store';

const algorithms: Array<'A*' | 'Dijkstra' | 'Bidirectional'> = ['A*', 'Dijkstra', 'Bidirectional'];

const calculateStressLevel = (transfers: number, walkingDistance: number, waitingTime: number): 'low' | 'medium' | 'high' => {
  const score = transfers * 2 + (walkingDistance / 1000) * 1.5 + waitingTime * 0.5;
  if (score < 5) return 'low';
  if (score < 10) return 'medium';
  return 'high';
};

function generateCoordinates(start: Coordinates, end: Coordinates, steps: number): Coordinates[] {
  const coords: Coordinates[] = [];
  for (let i = 0; i <= steps; i++) {
    const ratio = i / steps;
    coords.push({
      lat: start.lat + (end.lat - start.lat) * ratio,
      lng: start.lng + (end.lng - start.lng) * ratio,
    });
  }
  return coords;
}

export function generateMockRoutes(
  start: Coordinates,
  end: Coordinates,
  weights: Weights,
  modes: TransportModes
): Route[] {
  const routes: Route[] = [];

  const mid1 = {
    lat: start.lat + (end.lat - start.lat) * 0.3,
    lng: start.lng + (end.lng - start.lng) * 0.3,
  };
  const mid2 = {
    lat: start.lat + (end.lat - start.lat) * 0.7,
    lng: start.lng + (end.lng - start.lng) * 0.7,
  };

  if (modes.metro) {
    const segments: RouteSegment[] = [
      {
        mode: 'walk',
        from: 'Start',
        to: 'Metro Station A',
        duration: 5,
        distance: 400,
        cost: 0,
        co2: 0,
        waitingTime: 0,
        departureTime: '09:00',
        arrivalTime: '09:05',
        coordinates: generateCoordinates(start, mid1, 3),
      },
      {
        mode: 'metro',
        from: 'Metro Station A',
        to: 'Metro Station B',
        duration: 15,
        distance: 8000,
        line: 'M1',
        cost: 2.5,
        co2: 120,
        waitingTime: 3,
        departureTime: '09:08',
        arrivalTime: '09:23',
        coordinates: generateCoordinates(mid1, mid2, 8),
      },
      {
        mode: 'walk',
        from: 'Metro Station B',
        to: 'Destination',
        duration: 4,
        distance: 350,
        cost: 0,
        co2: 0,
        waitingTime: 0,
        departureTime: '09:23',
        arrivalTime: '09:27',
        coordinates: generateCoordinates(mid2, end, 3),
      },
    ];

    const totalWalking = 750;
    const totalWaiting = 3;

    routes.push({
      id: 'fastest',
      name: 'Fastest Route',
      type: 'fastest',
      segments,
      totalTime: 27,
      totalCost: 2.5,
      totalCO2: 120,
      totalDistance: 8750,
      totalWalkingDistance: totalWalking,
      totalWaitingTime: totalWaiting,
      transfers: 1,
      algorithm: 'A*',
      explanation: 'This route uses the A* algorithm with time-optimal heuristics. Direct metro connection minimizes travel time despite moderate walking.',
      stressLevel: calculateStressLevel(1, totalWalking, totalWaiting),
    });
  }

  if (modes.bus) {
    const busSegments: RouteSegment[] = [
      {
        mode: 'walk',
        from: 'Start',
        to: 'Bus Stop 1',
        duration: 3,
        distance: 200,
        cost: 0,
        co2: 0,
        waitingTime: 0,
        departureTime: '09:00',
        arrivalTime: '09:03',
        coordinates: generateCoordinates(start, mid1, 2),
      },
      {
        mode: 'bus',
        from: 'Bus Stop 1',
        to: 'Bus Stop 2',
        duration: 18,
        distance: 6000,
        line: '42',
        cost: 1.8,
        co2: 90,
        waitingTime: 5,
        departureTime: '09:08',
        arrivalTime: '09:26',
        coordinates: generateCoordinates(mid1, mid2, 6),
      },
      {
        mode: 'walk',
        from: 'Bus Stop 2',
        to: 'Destination',
        duration: 6,
        distance: 450,
        cost: 0,
        co2: 0,
        waitingTime: 0,
        departureTime: '09:26',
        arrivalTime: '09:32',
        coordinates: generateCoordinates(mid2, end, 3),
      },
    ];

    const totalWalking = 650;
    const totalWaiting = 5;

    routes.push({
      id: 'cheapest',
      name: 'Cheapest Route',
      type: 'cheapest',
      segments: busSegments,
      totalTime: 32,
      totalCost: 1.8,
      totalCO2: 90,
      totalDistance: 6650,
      totalWalkingDistance: totalWalking,
      totalWaitingTime: totalWaiting,
      transfers: 1,
      algorithm: 'Dijkstra',
      explanation: 'Dijkstra algorithm found this route by minimizing cost. Bus fare is lower than metro, providing best value despite slightly longer journey.',
      stressLevel: calculateStressLevel(1, totalWalking, totalWaiting),
    });
  }

  if (modes.tram && modes.train) {
    const ecoSegments: RouteSegment[] = [
      {
        mode: 'walk',
        from: 'Start',
        to: 'Tram Stop A',
        duration: 4,
        distance: 300,
        cost: 0,
        co2: 0,
        waitingTime: 0,
        departureTime: '09:00',
        arrivalTime: '09:04',
        coordinates: generateCoordinates(start, mid1, 3),
      },
      {
        mode: 'tram',
        from: 'Tram Stop A',
        to: 'Transfer Hub',
        duration: 12,
        distance: 4500,
        line: 'T3',
        cost: 1.5,
        co2: 35,
        waitingTime: 4,
        departureTime: '09:08',
        arrivalTime: '09:20',
        coordinates: generateCoordinates(mid1, mid2, 5),
      },
      {
        mode: 'train',
        from: 'Transfer Hub',
        to: 'Station Central',
        duration: 10,
        distance: 5000,
        line: 'RER B',
        cost: 0.5,
        co2: 25,
        waitingTime: 3,
        departureTime: '09:23',
        arrivalTime: '09:33',
        coordinates: generateCoordinates(mid2, { lat: mid2.lat + (end.lat - mid2.lat) * 0.7, lng: mid2.lng + (end.lng - mid2.lng) * 0.7 }, 4),
      },
      {
        mode: 'walk',
        from: 'Station Central',
        to: 'Destination',
        duration: 5,
        distance: 400,
        cost: 0,
        co2: 0,
        waitingTime: 0,
        departureTime: '09:33',
        arrivalTime: '09:38',
        coordinates: generateCoordinates({ lat: mid2.lat + (end.lat - mid2.lat) * 0.7, lng: mid2.lng + (end.lng - mid2.lng) * 0.7 }, end, 3),
      },
    ];

    const totalWalking = 700;
    const totalWaiting = 7;

    routes.push({
      id: 'greenest',
      name: 'Greenest Route',
      type: 'greenest',
      segments: ecoSegments,
      totalTime: 38,
      totalCost: 2.0,
      totalCO2: 60,
      totalDistance: 10200,
      totalWalkingDistance: totalWalking,
      totalWaitingTime: totalWaiting,
      transfers: 2,
      algorithm: 'Bidirectional',
      explanation: 'Bidirectional search optimized for CO₂ emissions. Electric tram and train combination produces 50% less emissions than bus alternatives.',
      stressLevel: calculateStressLevel(2, totalWalking, totalWaiting),
    });
  }

  routes.sort((a, b) => {
    const scoreA = weights.time * a.totalTime + weights.price * a.totalCost * 10 + weights.co2 * a.totalCO2 / 10;
    const scoreB = weights.time * b.totalTime + weights.price * b.totalCost * 10 + weights.co2 * b.totalCO2 / 10;
    return scoreA - scoreB;
  });

  return routes;
}
