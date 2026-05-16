

const translations = {
  fr: {
    
    'nav.home': 'Accueil',
    'nav.itinerary': 'Itinéraire',
    'nav.explorer': 'Explorer',
    'nav.profile': 'Profil',
    'nav.settings': 'Paramètres',
    'nav.lang-title': 'Passer en anglais',
    'nav.theme-title': 'Basculer thème clair / sombre',
    'nav.login': 'Connexion',

    
    'hero.tag1': '🌍 Wilaya d\'Alger',
    'hero.tag2': '6 modes de transport',
    'hero.h1': 'Voyagez à Alger<br><span class="grad-mint">Plus Vert.</span><br><span class="grad-purple">Plus Intelligent.</span>',
    'hero.desc': 'Planification multi-modale alimentée par l\'IA — métro, tram, bus, train, téléphérique et marche. Minimisez le temps, le coût et l\'empreinte CO₂ en un clic.',
    'hero.btn-plan': 'Planifier un trajet',
    'hero.btn-discover': 'Découvrir →',
    'hero.stat1-lbl': 'Algorithmes IA',
    'hero.stat2-lbl': 'Stations couvertes',
    'hero.stat3-lbl': 'Profils voyage',
    'hero.card-title': 'Exemple de trajet',
    'hero.card-route': 'Martyrs → Zeralda',
    'hero.card-dur': 'Durée',
    'hero.card-cost': 'Coût',

    
    'feat.tag': 'Optimisation Multi-Critères',
    'feat.h2': 'Tout optimisé en une seule requête',
    'feat.desc': 'Choisissez votre profil de priorité — rapidité, économie, écologie ou équilibre.',
    'feat.c1-h3': 'Suivi CO₂ réel',
    'feat.c1-p': 'Facteurs d\'émission par mode. Bus: 68g/km · Métro: 5g/km · Tram: 4g/km.',
    'feat.c2-h3': '3 Algorithmes IA',
    'feat.c2-p': 'Dijkstra, A* et Recherche Bi-Directionnelle. Comparaison en temps réel.',
    'feat.c3-h3': 'Double saisie',
    'feat.c3-p': 'Entrez les noms des arrêts par texte <strong style="color:var(--text-p)">ou</strong> cliquez directement sur la carte d\'Alger.',
    'feat.c4-h3': '4 Profils utilisateur',
    'feat.c4-p': 'Rapide, Économique, Écologique, Équilibré — ou personnalisez les poids manuellement.',

    
    'algo.tag': 'Performance des Algorithmes',
    'algo.h2': 'Même résultat, trois chemins différents',
    'algo.desc': 'Les trois algorithmes garantissent le même coût optimal. La différence : le nombre de nœuds explorés.',
    'algo.a1-h': 'Dijkstra (baseline)',
    'algo.a1-p': 'Explore tous les nœuds — optimal garanti, sans heuristique',
    'algo.a2-h': 'A* Search',
    'algo.a2-p': 'h(n) = w₁·d/Vmax×60 — heuristique admissible, moins d\'expansions',
    'algo.a3-h': 'Bi-Directionnel',
    'algo.a3-p': 'Recherches avant + arrière se rejoignent au milieu — le plus efficace',
    'algo.btn': 'Lancer la comparaison →',
    'algo.card-lbl': 'Nœuds explorés — Martyrs → Zeralda',

    
    'cta.h2': 'Prêt à voyager vert ?',
    'cta.desc': 'Rejoignez la communauté LYHLYH et planifiez des trajets intelligents à travers la wilaya d\'Alger.',
    'cta.btn1': 'Créer un compte',
    'cta.btn2': 'Essayer sans compte',

    
    'footer.course': 'Introduction à l\'IA — Printemps 2025–2026 · Projet 5',
    'footer.loc': 'Alger, Algérie 🇩🇿',

    
    'dash.menu-lbl': 'Menu Principal',
    'dash.itinerary': 'Itinéraire',
    'dash.explorer': 'Explorer',
    'dash.profile': 'Profil',
    'dash.favorites': 'Favoris',
    'dash.fav1': 'Maison → Travail',
    'dash.fav2': 'Université',
    'dash.profile-lbl': 'Profil de recherche',
    'dash.prof-bal': '⚖️ Équilibré',
    'dash.prof-fast': '⚡ Le plus rapide',
    'dash.prof-cheap': '💰 Le moins cher',
    'dash.prof-green': '🌿 Écologique',
    'dash.help-title': 'Besoin d\'aide ?',
    'dash.help-desc': 'Appuyez sur \'Echap\' pour fermer les menus.',
    'dash.help-btn': 'Tutoriel',

    
    'map.network-btn': 'Afficher réseau',
    'map.click-hint': '📍 Cliquez sur la carte pour définir le départ',
    'map.origin-btn': '📍 Départ',
    'map.dest-btn': '🎯 Arrivée',
    'map.origin-ph': 'Où êtes-vous ?',
    'map.dest-ph': 'Où allez-vous ?',
    'map.algo-lbl': 'Algorithme d\'IA',
    'map.filters': '+ Filtres / Contraintes',
    'map.cost-lbl': 'Coût max (DA)',
    'map.cost-ph': 'Ex: 100',
    'map.weight-lbl': 'Poids coût financier (0.0 à 1.0)',
    'map.weight-ph': 'Ex: 0.8',
    'map.reset': 'Rétablir défaut',
    'map.plan-btn': 'Planifier l\'itinéraire',
    'map.status': 'Cliquez sur la carte pour définir le départ',
    'map.legend-m': 'Métro L1',
    'map.legend-t': 'Tramway T1',
    'map.legend-k': 'Train banlieue',
    'map.legend-tel': 'Téléphérique',
    'map.legend-route': 'Trajet généré',
    'map.loading': 'Calcul en cours...',
    'map.loading-api': 'Calcul du trajet sur le serveur…',
    'map.loading-sub': 'Exploration de l\'arbre d\'états multi-modal',

    
    'res.tab-itin': 'Itinéraire',
    'res.tab-stats': 'Statistiques',
    'res.chart-lbl': 'RÉPARTITION DU TEMPS',
    'res.steps-lbl': 'ÉTAPES DU TRAJET',
    'res.summary': 'RÉSUMÉ',
    'res.detail': 'DÉTAIL DES SEGMENTS (HORS MARCHE)',

    
    'auth.title': 'Bon retour',
    'auth.sub': 'Connectez-vous à LYHLYH',
    'auth.tab-login': 'Connexion',
    'auth.tab-signup': 'Inscription',
    'auth.email': 'Email',
    'auth.pass': 'Mot de passe',
    'auth.forgot': 'Oublié ?',
    'auth.btn-login': 'Se connecter',
    'auth.name': 'Nom complet',
    'auth.btn-signup': 'Créer mon compte',

    
    'exp.title': 'Explorer le réseau',
    'exp.desc': 'Découvrez les trajets fréquents et le plan de la wilaya d\'Alger.',
    'exp.search-ph': 'Rechercher (ex: Zeralda)...',
    'exp.sort-time': 'Trier par temps',
    'exp.sort-cost': 'Trier par coût',
    'exp.sort-co2': 'Trier par CO₂',
    'exp.sort-tf': 'Trier par corresp.',

    
    'prof.member': 'Membre depuis Jan 2026',
    'prof.level': 'Niveau 4 — Explorateur',
    'prof.usage-lbl': 'Utilisation des modes (30j)',
    'prof.tab-hist': 'Historique',
    'prof.tab-badges': 'Badges',
    'prof.tab-stats': 'Statistiques',
    'prof.stat1-lbl': 'Trajets planifiés',
    'prof.stat1-delta': '↗ +12 ce mois',
    'prof.stat2-lbl': 'DA économisés (vs Voiture)',
    'prof.stat2-delta': '↗ +3k ce mois',
    'prof.stat3-lbl': 'Heures de marche',
    'prof.stat3-delta': '↗ +2h ce mois',
    'prof.stat4-lbl': 'kg CO₂ évités',
    'prof.stat4-delta': '↗ +1.2kg ce mois',

    
    'set.title': 'Paramètres de l\'IA',
    'set.desc': 'Personnalisez le comportement des algorithmes de routage par défaut.',
    'set.prof-lbl': 'Profils prédéfinis',
    'set.weights-lbl': 'Poids des critères (Avancé)',
    'set.w1': 'Temps (w₁)',
    'set.w2': 'Coût financier (w₂)',
    'set.w3': 'Émissions CO₂ (w₃)',
    'set.weights-desc': 'L\'algorithme A* et Bi-Directionnel utilisent ces poids pour minimiser le coût fonctionnel total. La somme n\'a pas besoin d\'être 1.0, mais ils représentent l\'importance relative dans l\'heuristique de la wilaya.',

    
    '404.title': 'Vous êtes hors réseau',
    '404.desc': 'La page que vous cherchez n\'existe pas ou n\'est pas desservie par LYHLYH.',
    '404.btn': 'Retour à l\'accueil',
    'tut.title': 'Comment utiliser LYHLYH',
    'tut.s1-h': 'Définir les points :',
    'tut.s1-d': 'Cliquez sur la carte ou tapez le nom d\'une station d\'Alger (ex: Tafourah).',
    'tut.s2-h': 'Choisir l\'IA :',
    'tut.s2-d': 'A* est le plus équilibré. Dijkstra garantit le chemin absolu. Bi-Dir est le plus rapide en exécution.',
    'tut.s3-h': 'Profils :',
    'tut.s3-d': 'Ajustez vos priorités dans les paramètres (Temps vs Argent vs CO₂).',
    'tut.s4-h': 'Résultats :',
    'tut.s4-d': 'Analysez les coûts, l\'empreinte carbone et suivez la ligne animée sur la carte.',
    'tut.btn': 'J\'ai compris',

    
    'notif.settings-reset-title': 'Paramètres réinitialisés',
    'notif.settings-reset-msg': 'Valeurs globales utilisées',
    'notif.missing-pts-title': 'Départ ou arrivée manquant',
    'notif.missing-pts-msg': 'Sélectionnez les deux points',
    'notif.same-pt-title': 'Même arrêt',
    'notif.same-pt-msg': 'Les deux points doivent être différents',
    'notif.route-found-title': 'Itinéraire trouvé !',
    'notif.route-variants': '{n} variante(s)',
    'notif.empty-result-title': 'Résultat vide',
    'notif.empty-result-msg': 'Réessayez avec d’autres points',
    'notif.network-error-title': 'Erreur réseau',
    'notif.network-error-msg': 'Vérifiez que l’API tourne sur http://localhost:8000',
    'notif.calc-in': 'Calculé en',
    'notif.pt-set-title': 'défini',
    'notif.pt-origin': 'Départ',
    'notif.pt-dest': 'Arrivée',
    'notif.no-station-msg': 'Aucun arrêt proche — position libre',
    'notif.nearest-fallback-msg': 'Aucun arrêt renvoyé — utilisation des coordonnées',
    'notif.missing-fields-title': 'Champs manquants',
    'notif.missing-fields-msg': 'Veuillez remplir tous les champs',
    'notif.login-title': 'Connecté !',
    'notif.login-msg': 'Bienvenue, Ahmed 👋',
    'notif.signup-title': 'Compte créé !',
    'notif.signup-msg': 'Bienvenue chez LYHLYH 🌿',

    
    'time.min': 'min',
    'res.ride-time': 'Temps trajet',
    'res.wait-time': 'Temps attente',
    'res.walk': 'Marche',
    'res.modes': 'Modes',
    'res.nodes': 'nœuds',
    'res.calculated-with': 'Calculé avec',
    'res.optimal': 'optimal garanti',
    'res.custom-params': 'params perso.',
    'res.transfers': 'corresp.',
    'res.no-transfer': 'Aucune correspondance',
    'res.transfer-s': 'correspondance(s)',
    'res.price-total': 'Prix total',
    'res.cost-dist': '💰 RÉPARTITION DES COÛTS',
    'res.total': 'Total',
    'res.dist': 'Distance',
    'res.segments-tot': 'segments total',
    'res.efficiency': 'Efficacité',
    'res.profile': 'profil',
    'res.no-route': 'Aucun itinéraire trouvé',
    'res.no-route-hint': 'Sélectionnez un départ et une arrivée pour planifier un trajet.',
    'res.no-route-same': 'Le départ et l\'arrivée doivent être différents.',
    'res.no-route-empty': 'Le serveur n’a renvoyé aucune variante.',
    'res.no-path-server': 'Le serveur n’a pas trouvé de chemin pour ces critères.',
    'res.free': 'Gratuit',
    'res.summary-title': 'Résumé du trajet',
    'res.card-fast': 'Plus rapide',
    'res.card-cheap': 'Moins cher',
    'res.card-green': 'Plus vert',
    'res.label-fastest': 'Plus rapide',
    'res.label-cheapest': 'Moins cher',
    'res.label-greenest': 'Plus vert',
    'res.label-recommended': '⭐ Recommandé',
    'res.route-via': 'Trajet via',
    'res.using': 'En utilisant',
    'res.time': 'Temps :',
    'res.cost': 'Coût :',
    'res.mode': 'Mode :',
    'res.no-itin': 'Pas d\'itin.',
    'res.walk-to': 'Marcher vers',
    'res.take': 'Prendre',
    'res.change-to': 'Changer pour',
    'res.until': 'jusqu\'à',
    'res.get-off-at': 'Descendre à',
    'res.walk-to-dest': 'Marcher jusqu\'à la destination',
    'prof.days-ago': 'Il y a 2 jours',
    'prof.today': 'Aujourd\'hui',
    'prof.achiev': 'Achèvement',
    'prof.completed': 'Complété',
    'auth.pw-weak': 'Faible',
    'auth.pw-med': 'Moyen',
    'auth.pw-good': 'Bon',
    'auth.pw-str': 'Fort',
    'map.station-of': 'Station de',
    'map.connexions': 'Correspondances',
    'map.hide-network': 'Masquer réseau',
    'map.show-network': 'Afficher réseau',
    'map.custom-origin': 'Départ personnalisé',
    'map.custom-dest': 'Arrivée personnalisée',
    'map.click-origin': '📍 Cliquez sur la carte pour définir le départ',
    'map.click-dest': '🎯 Cliquez sur la carte pour définir l\'arrivée'
  },
  en: {
    
    'nav.home': 'Home',
    'nav.itinerary': 'Itinerary',
    'nav.explorer': 'Explorer',
    'nav.profile': 'Profile',
    'nav.settings': 'Settings',
    'nav.lang-title': 'Switch to French',
    'nav.theme-title': 'Toggle Dark / Light Mode',
    'nav.login': 'Log in',

    
    'hero.tag1': '🌍 Algiers Province',
    'hero.tag2': '6 transport modes',
    'hero.h1': 'Travel across Algiers<br><span class="grad-mint">Greener.</span><br><span class="grad-purple">Smarter.</span>',
    'hero.desc': 'AI-powered multi-modal planning — metro, tram, bus, train, cable car, and walking. Minimize time, cost, and CO₂ footprint in one click.',
    'hero.btn-plan': 'Plan a trip',
    'hero.btn-discover': 'Discover →',
    'hero.stat1-lbl': 'AI Algorithms',
    'hero.stat2-lbl': 'Stations covered',
    'hero.stat3-lbl': 'Travel profiles',
    'hero.card-title': 'Sample Route',
    'hero.card-route': 'Martyrs → Zeralda',
    'hero.card-dur': 'Duration',
    'hero.card-cost': 'Cost',

    
    'feat.tag': 'Multi-Criteria Optimization',
    'feat.h2': 'Everything optimized in one query',
    'feat.desc': 'Choose your priority profile — speed, economy, ecology, or balanced.',
    'feat.c1-h3': 'Real-time CO₂ tracking',
    'feat.c1-p': 'Emission factors per mode. Bus: 68g/km · Metro: 5g/km · Tram: 4g/km.',
    'feat.c2-h3': '3 AI Algorithms',
    'feat.c2-p': 'Dijkstra, A* and Bi-Directional Search. Real-time comparison.',
    'feat.c3-h3': 'Dual Input',
    'feat.c3-p': 'Enter station names via text <strong style="color:var(--text-p)">or</strong> click directly on the Algiers map.',
    'feat.c4-h3': '4 User Profiles',
    'feat.c4-p': 'Fastest, Cheapest, Greenest, Balanced — or customize weights manually.',

    
    'algo.tag': 'Algorithm Performance',
    'algo.h2': 'Same result, three different paths',
    'algo.desc': 'All three algorithms guarantee the same optimal cost. The difference: the number of expanded nodes.',
    'algo.a1-h': 'Dijkstra (baseline)',
    'algo.a1-p': 'Explores all nodes — guaranteed optimal, no heuristic',
    'algo.a2-h': 'A* Search',
    'algo.a2-p': 'h(n) = w₁·d/Vmax×60 — admissible heuristic, fewer expansions',
    'algo.a3-h': 'Bi-Directional',
    'algo.a3-p': 'Forward + backward searches meet in the middle — most efficient',
    'algo.btn': 'Start the comparison →',
    'algo.card-lbl': 'Expanded nodes — Martyrs → Zeralda',

    
    'cta.h2': 'Ready to travel green?',
    'cta.desc': 'Join the LYHLYH community and plan smart trips across Algiers.',
    'cta.btn1': 'Create an account',
    'cta.btn2': 'Try without account',

    
    'footer.course': 'Intro to AI — Spring 2025–2026 · Project 5',
    'footer.loc': 'Algiers, Algeria 🇩🇿',

    
    'dash.menu-lbl': 'Main Menu',
    'dash.itinerary': 'Itinerary',
    'dash.explorer': 'Explorer',
    'dash.profile': 'Profile',
    'dash.favorites': 'Favorites',
    'dash.fav1': 'Home → Work',
    'dash.fav2': 'University',
    'dash.profile-lbl': 'Search Profile',
    'dash.prof-bal': '⚖️ Balanced',
    'dash.prof-fast': '⚡ Fastest',
    'dash.prof-cheap': '💰 Cheapest',
    'dash.prof-green': '🌿 Greenest',
    'dash.help-title': 'Need help?',
    'dash.help-desc': 'Press \'Escape\' to close menus.',
    'dash.help-btn': 'Tutorial',

    
    'map.network-btn': 'Show network',
    'map.click-hint': '📍 Click on the map to set origin',
    'map.origin-btn': '📍 Origin',
    'map.dest-btn': '🎯 Destination',
    'map.origin-ph': 'Where are you?',
    'map.dest-ph': 'Where are you going?',
    'map.algo-lbl': 'AI Algorithm',
    'map.filters': '+ Filters / Constraints',
    'map.cost-lbl': 'Max cost (DZD)',
    'map.cost-ph': 'Ex: 100',
    'map.weight-lbl': 'Financial cost weight (0.0 to 1.0)',
    'map.weight-ph': 'Ex: 0.8',
    'map.reset': 'Reset to default',
    'map.plan-btn': 'Plan route',
    'map.status': 'Click on the map to set origin',
    'map.legend-m': 'Metro L1',
    'map.legend-t': 'Tramway T1',
    'map.legend-k': 'Suburban Train',
    'map.legend-tel': 'Cable car',
    'map.legend-route': 'Generated route',
    'map.loading': 'Computing...',
    'map.loading-api': 'Computing route on server…',
    'map.loading-sub': 'Exploring multi-modal state tree',

    
    'res.tab-itin': 'Itinerary',
    'res.tab-stats': 'Statistics',
    'res.chart-lbl': 'TIME BREAKDOWN',
    'res.steps-lbl': 'ROUTE STEPS',
    'res.summary': 'SUMMARY',
    'res.detail': 'SEGMENT DETAILS (EXCLUDING WALKING)',

    
    'auth.title': 'Welcome back',
    'auth.sub': 'Log in to LYHLYH',
    'auth.tab-login': 'Log in',
    'auth.tab-signup': 'Sign up',
    'auth.email': 'Email',
    'auth.pass': 'Password',
    'auth.forgot': 'Forgot?',
    'auth.btn-login': 'Log in',
    'auth.name': 'Full name',
    'auth.btn-signup': 'Create account',

    
    'exp.title': 'Network Explorer',
    'exp.desc': 'Discover frequent routes and the map of Algiers.',
    'exp.search-ph': 'Search (ex: Zeralda)...',
    'exp.sort-time': 'Sort by time',
    'exp.sort-cost': 'Sort by cost',
    'exp.sort-co2': 'Sort by CO₂',
    'exp.sort-tf': 'Sort by transfers',

    
    'prof.member': 'Member since Jan 2026',
    'prof.level': 'Level 4 — Explorer',
    'prof.usage-lbl': 'Mode usage (30d)',
    'prof.tab-hist': 'History',
    'prof.tab-badges': 'Badges',
    'prof.tab-stats': 'Statistics',
    'prof.stat1-lbl': 'Planned trips',
    'prof.stat1-delta': '↗ +12 this month',
    'prof.stat2-lbl': 'DZD saved (vs Car)',
    'prof.stat2-delta': '↗ +3k this month',
    'prof.stat3-lbl': 'Hours walked',
    'prof.stat3-delta': '↗ +2h this month',
    'prof.stat4-lbl': 'kg CO₂ avoided',
    'prof.stat4-delta': '↗ +1.2kg this month',

    
    'set.title': 'AI Settings',
    'set.desc': 'Customize default routing algorithm behavior.',
    'set.prof-lbl': 'Preset profiles',
    'set.weights-lbl': 'Criteria weights (Advanced)',
    'set.w1': 'Time (w₁)',
    'set.w2': 'Financial cost (w₂)',
    'set.w3': 'CO₂ Emissions (w₃)',
    'set.weights-desc': 'A* and Bi-Directional algorithms use these weights to minimize total functional cost. Sum doesn\'t need to be 1.0, but represents relative importance in the Algiers heuristic.',

    
    '404.title': 'Out of network',
    '404.desc': 'The page you\'re looking for doesn\'t exist or isn\'t served by LYHLYH.',
    '404.btn': 'Back to home',
    'tut.title': 'How to use LYHLYH',
    'tut.s1-h': 'Define your points:',
    'tut.s1-d': 'Click on the map or type an Algiers station name (e.g. Tafourah).',
    'tut.s2-h': 'Choose the AI:',
    'tut.s2-d': 'A* is balanced. Dijkstra guarantees absolute shortest path. Bi-Dir is the fastest in execution.',
    'tut.s3-h': 'Profiles:',
    'tut.s3-d': 'Adjust priorities in settings (Time vs Money vs CO₂).',
    'tut.s4-h': 'Results:',
    'tut.s4-d': 'Analyze costs, carbon footprint, and follow the animated line on the map.',
    'tut.btn': 'Got it',

    
    'notif.settings-reset-title': 'Settings reset',
    'notif.settings-reset-msg': 'Global values restored',
    'notif.missing-pts-title': 'Missing origin or destination',
    'notif.missing-pts-msg': 'Please select both points',
    'notif.same-pt-title': 'Same station',
    'notif.same-pt-msg': 'Origin and destination must be different',
    'notif.route-found-title': 'Route found!',
    'notif.route-variants': '{n} variant(s)',
    'notif.empty-result-title': 'Empty result',
    'notif.empty-result-msg': 'Try different points',
    'notif.network-error-title': 'Network error',
    'notif.network-error-msg': 'Ensure the API is running at http://localhost:8000',
    'notif.calc-in': 'Calculated in',
    'notif.pt-set-title': 'set',
    'notif.pt-origin': 'Origin',
    'notif.pt-dest': 'Destination',
    'notif.no-station-msg': 'No close station — free position',
    'notif.nearest-fallback-msg': 'No stop returned — using raw coordinates',
    'notif.missing-fields-title': 'Missing fields',
    'notif.missing-fields-msg': 'Please fill all fields',
    'notif.login-title': 'Logged in!',
    'notif.login-msg': 'Welcome back, Ahmed 👋',
    'notif.signup-title': 'Account created!',
    'notif.signup-msg': 'Welcome to LYHLYH 🌿',

    
    'time.min': 'min',
    'res.ride-time': 'Ride time',
    'res.wait-time': 'Wait time',
    'res.walk': 'Walk',
    'res.modes': 'Modes',
    'res.nodes': 'nodes',
    'res.calculated-with': 'Calculated with',
    'res.optimal': 'guaranteed optimal',
    'res.custom-params': 'custom params',
    'res.transfers': 'transfers',
    'res.no-transfer': 'No transfers',
    'res.transfer-s': 'transfer(s)',
    'res.price-total': 'Total price',
    'res.cost-dist': '💰 COST DISTRIBUTION',
    'res.total': 'Total',
    'res.dist': 'Distance',
    'res.segments-tot': 'total segments',
    'res.efficiency': 'Efficiency',
    'res.profile': 'profile',
    'res.no-route': 'No route found',
    'res.no-route-hint': 'Select an origin and destination to plan a trip.',
    'res.no-route-same': 'Origin and destination must be different.',
    'res.no-route-empty': 'The server returned no route variants.',
    'res.no-path-server': 'No path found for these criteria.',
    'res.free': 'Free',
    'res.summary-title': 'Trip summary',
    'res.card-fast': 'Fastest',
    'res.card-cheap': 'Cheapest',
    'res.card-green': 'Greenest',
    'res.label-fastest': 'Fastest',
    'res.label-cheapest': 'Cheapest',
    'res.label-greenest': 'Greenest',
    'res.label-recommended': '⭐ Recommended',
    'res.route-via': 'Route via',
    'res.using': 'Using',
    'res.time': 'Time:',
    'res.cost': 'Cost:',
    'res.mode': 'Mode:',
    'res.no-itin': 'No route',
    'res.walk-to': 'Walk to',
    'res.take': 'Take',
    'res.change-to': 'Change for',
    'res.until': 'until',
    'res.get-off-at': 'Get off at',
    'res.walk-to-dest': 'Walk to destination',
    'prof.days-ago': '2 days ago',
    'prof.today': 'Today',
    'prof.achiev': 'Achievement',
    'prof.completed': 'Completed',
    'auth.pw-weak': 'Weak',
    'auth.pw-med': 'Medium',
    'auth.pw-good': 'Good',
    'auth.pw-str': 'Strong',
    'map.station-of': 'Station of',
    'map.connexions': 'Connexions',
    'map.hide-network': 'Hide network',
    'map.show-network': 'Show network',
    'map.custom-origin': 'Custom origin',
    'map.custom-dest': 'Custom destination',
    'map.click-origin': '📍 Click on the map to set the origin',
    'map.click-dest': '🎯 Click on the map to set the destination'
  }
};

let currentLang = localStorage.getItem('lyhlyh-lang') || 'fr';

window.t = function(key) {
  return translations[currentLang]?.[key] || key;
};

function applyLang(lang) {
  if (!translations[lang]) return;
  currentLang = lang;
  document.documentElement.lang = lang;
  localStorage.setItem('lyhlyh-lang', lang);

  const btn = document.getElementById('lang-toggle');
  if (btn) {
    const textEl = btn.querySelector('.lang-text');
    const nextLang = lang === 'fr' ? 'EN' : 'FR';
    if (textEl) {
      textEl.textContent = nextLang;
    } else {
      btn.textContent = nextLang;
    }
    btn.title = lang === 'fr' ? 'Switch to English' : 'Passer en français';
    btn.setAttribute('aria-label', btn.title);
  }

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const val = translations[lang][el.getAttribute('data-i18n')];
    if (val) el.textContent = val;
  });

  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const val = translations[lang][el.getAttribute('data-i18n-html')];
    if (val) el.innerHTML = val;
  });

  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const val = translations[lang][el.getAttribute('data-i18n-placeholder')];
    if (val) el.setAttribute('placeholder', val);
  });

  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const val = translations[lang][el.getAttribute('data-i18n-title')];
    if (val) {
      el.setAttribute('title', val);
      el.setAttribute('aria-label', val);
    }
  });

  document.dispatchEvent(new CustomEvent('lang-changed', { detail: { lang } }));
}

function toggleLang() {
  applyLang(currentLang === 'fr' ? 'en' : 'fr');
}

document.addEventListener('DOMContentLoaded', () => {
  applyLang(currentLang);
});
