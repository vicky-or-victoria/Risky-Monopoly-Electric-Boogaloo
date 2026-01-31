# Collectibles data - Cars, Planes, Real Estate, Boats, Jewelry, etc.

COLLECTIBLE_CATEGORIES = {
    'cars': {
        'name': '🚗 Luxury Cars',
        'emoji': '🚗',
        'description': 'High-end automotive collectibles'
    },
    'planes': {
        'name': '✈️ Private Jets',
        'emoji': '✈️',
        'description': 'Exclusive aircraft collection'
    },
    'real_estate': {
        'name': '🏰 Real Estate',
        'emoji': '🏰',
        'description': 'Premium properties worldwide'
    },
    'boats': {
        'name': '🛥️ Yachts & Boats',
        'emoji': '🛥️',
        'description': 'Luxury maritime vessels'
    },
    'jewelry': {
        'name': '💎 Jewelry',
        'emoji': '💎',
        'description': 'Precious gems and timepieces'
    },
    'art': {
        'name': '🎨 Fine Art',
        'emoji': '🎨',
        'description': 'Prestigious artwork and sculptures'
    }
}

COLLECTIBLES = {
    # LUXURY CARS
    'bugatti_chiron': {
        'name': 'Bugatti Chiron Super Sport',
        'category': 'cars',
        'price': 3900000,
        'rarity': 'legendary',
        'description': 'One of the fastest production cars in the world',
        'emoji': '🏎️'
    },
    'ferrari_laferrari': {
        'name': 'Ferrari LaFerrari',
        'category': 'cars',
        'price': 1500000,
        'rarity': 'epic',
        'description': 'Limited edition hybrid supercar',
        'emoji': '🏎️'
    },
    'lamborghini_aventador': {
        'name': 'Lamborghini Aventador SVJ',
        'category': 'cars',
        'price': 517770,
        'rarity': 'epic',
        'description': 'Italian masterpiece of engineering',
        'emoji': '🚗'
    },
    'mclaren_p1': {
        'name': 'McLaren P1',
        'category': 'cars',
        'price': 1150000,
        'rarity': 'epic',
        'description': 'British hybrid hypercar',
        'emoji': '🏎️'
    },
    'rolls_royce_phantom': {
        'name': 'Rolls-Royce Phantom VIII',
        'category': 'cars',
        'price': 460000,
        'rarity': 'rare',
        'description': 'The pinnacle of luxury motoring',
        'emoji': '🚙'
    },
    'bentley_continental': {
        'name': 'Bentley Continental GT',
        'category': 'cars',
        'price': 230000,
        'rarity': 'rare',
        'description': 'Grand touring excellence',
        'emoji': '🚗'
    },
    'porsche_911_gt3': {
        'name': 'Porsche 911 GT3 RS',
        'category': 'cars',
        'price': 225250,
        'rarity': 'rare',
        'description': 'Track-focused performance car',
        'emoji': '🚗'
    },
    'mercedes_amg_one': {
        'name': 'Mercedes-AMG ONE',
        'category': 'cars',
        'price': 2700000,
        'rarity': 'legendary',
        'description': 'F1 technology for the road',
        'emoji': '🏎️'
    },
    
    # PRIVATE JETS
    'gulfstream_g700': {
        'name': 'Gulfstream G700',
        'category': 'planes',
        'price': 75000000,
        'rarity': 'legendary',
        'description': 'The flagship of business aviation',
        'emoji': '✈️'
    },
    'bombardier_global_7500': {
        'name': 'Bombardier Global 7500',
        'category': 'planes',
        'price': 73000000,
        'rarity': 'legendary',
        'description': 'Ultra-long-range business jet',
        'emoji': '✈️'
    },
    'cessna_citation_x': {
        'name': 'Cessna Citation X+',
        'category': 'planes',
        'price': 23000000,
        'rarity': 'epic',
        'description': 'Fastest civilian aircraft',
        'emoji': '✈️'
    },
    'embraer_phenom_300': {
        'name': 'Embraer Phenom 300E',
        'category': 'planes',
        'price': 9500000,
        'rarity': 'rare',
        'description': 'Light jet with impressive range',
        'emoji': '🛩️'
    },
    'learjet_75': {
        'name': 'Learjet 75 Liberty',
        'category': 'planes',
        'price': 9900000,
        'rarity': 'rare',
        'description': 'Iconic light business jet',
        'emoji': '🛩️'
    },
    
    # REAL ESTATE
    'manhattan_penthouse': {
        'name': 'Manhattan Penthouse',
        'category': 'real_estate',
        'price': 95000000,
        'rarity': 'legendary',
        'description': 'Luxury penthouse in New York City',
        'emoji': '🏙️'
    },
    'beverly_hills_mansion': {
        'name': 'Beverly Hills Mansion',
        'category': 'real_estate',
        'price': 70000000,
        'rarity': 'legendary',
        'description': 'Sprawling estate in exclusive neighborhood',
        'emoji': '🏡'
    },
    'dubai_villa': {
        'name': 'Dubai Palm Villa',
        'category': 'real_estate',
        'price': 45000000,
        'rarity': 'epic',
        'description': 'Waterfront villa on Palm Jumeirah',
        'emoji': '🏝️'
    },
    'paris_apartment': {
        'name': 'Paris Haussmann Apartment',
        'category': 'real_estate',
        'price': 15000000,
        'rarity': 'epic',
        'description': 'Historic apartment in the heart of Paris',
        'emoji': '🗼'
    },
    'london_townhouse': {
        'name': 'Kensington Townhouse',
        'category': 'real_estate',
        'price': 25000000,
        'rarity': 'epic',
        'description': 'Victorian townhouse in London',
        'emoji': '🏛️'
    },
    'aspen_chalet': {
        'name': 'Aspen Ski Chalet',
        'category': 'real_estate',
        'price': 18000000,
        'rarity': 'rare',
        'description': 'Mountain retreat in Colorado',
        'emoji': '⛷️'
    },
    'miami_condo': {
        'name': 'Miami Beach Condo',
        'category': 'real_estate',
        'price': 8000000,
        'rarity': 'rare',
        'description': 'Oceanfront luxury condominium',
        'emoji': '🏖️'
    },
    
    # YACHTS & BOATS
    'eclipse_yacht': {
        'name': 'Eclipse Superyacht',
        'category': 'boats',
        'price': 500000000,
        'rarity': 'legendary',
        'description': 'One of the largest private yachts',
        'emoji': '🛳️'
    },
    'azzam_yacht': {
        'name': 'Azzam Megayacht',
        'category': 'boats',
        'price': 600000000,
        'rarity': 'legendary',
        'description': 'The longest private motor yacht',
        'emoji': '🛳️'
    },
    'sunseeker_predator': {
        'name': 'Sunseeker Predator 80',
        'category': 'boats',
        'price': 4500000,
        'rarity': 'epic',
        'description': 'High-performance motor yacht',
        'emoji': '🛥️'
    },
    'riva_opera': {
        'name': 'Riva Opera Super',
        'category': 'boats',
        'price': 7500000,
        'rarity': 'epic',
        'description': 'Italian luxury yacht',
        'emoji': '⛵'
    },
    'benetti_yacht': {
        'name': 'Benetti Classic Supreme',
        'category': 'boats',
        'price': 25000000,
        'rarity': 'epic',
        'description': 'Custom Italian superyacht',
        'emoji': '🛥️'
    },
    'princess_yacht': {
        'name': 'Princess Y85',
        'category': 'boats',
        'price': 6000000,
        'rarity': 'rare',
        'description': 'British motor yacht elegance',
        'emoji': '⛵'
    },
    
    # JEWELRY & WATCHES
    'patek_philippe_grandmaster': {
        'name': 'Patek Philippe Grandmaster Chime',
        'category': 'jewelry',
        'price': 31000000,
        'rarity': 'legendary',
        'description': 'Most complicated wristwatch ever made',
        'emoji': '⌚'
    },
    'graff_pink_diamond': {
        'name': 'Graff Pink Diamond',
        'category': 'jewelry',
        'price': 46000000,
        'rarity': 'legendary',
        'description': '24.78-carat fancy intense pink diamond',
        'emoji': '💎'
    },
    'blue_moon_diamond': {
        'name': 'Blue Moon of Josephine',
        'category': 'jewelry',
        'price': 48500000,
        'rarity': 'legendary',
        'description': '12.03-carat blue diamond',
        'emoji': '💎'
    },
    'rolex_daytona_rainbow': {
        'name': 'Rolex Daytona Rainbow',
        'category': 'jewelry',
        'price': 1000000,
        'rarity': 'epic',
        'description': 'Gem-set chronograph masterpiece',
        'emoji': '⌚'
    },
    'cartier_panther': {
        'name': 'Cartier Panthère',
        'category': 'jewelry',
        'price': 1500000,
        'rarity': 'epic',
        'description': 'Iconic diamond and onyx bracelet',
        'emoji': '💍'
    },
    'tiffany_yellow_diamond': {
        'name': 'Tiffany Yellow Diamond Necklace',
        'category': 'jewelry',
        'price': 30000000,
        'rarity': 'legendary',
        'description': '128.54-carat yellow diamond',
        'emoji': '💎'
    },
    'audemars_piguet_royal_oak': {
        'name': 'Audemars Piguet Royal Oak',
        'category': 'jewelry',
        'price': 450000,
        'rarity': 'rare',
        'description': 'Legendary luxury sports watch',
        'emoji': '⌚'
    },
    
    # FINE ART
    'salvator_mundi': {
        'name': 'Salvator Mundi (da Vinci)',
        'category': 'art',
        'price': 450000000,
        'rarity': 'legendary',
        'description': 'Leonardo da Vinci masterpiece',
        'emoji': '🖼️'
    },
    'basquiat_untitled': {
        'name': 'Untitled (Basquiat, 1982)',
        'category': 'art',
        'price': 110500000,
        'rarity': 'legendary',
        'description': 'Jean-Michel Basquiat artwork',
        'emoji': '🎨'
    },
    'picasso_women_algiers': {
        'name': 'Women of Algiers (Picasso)',
        'category': 'art',
        'price': 179400000,
        'rarity': 'legendary',
        'description': 'Pablo Picasso cubist masterpiece',
        'emoji': '🖼️'
    },
    'monet_water_lilies': {
        'name': 'Water Lilies (Monet)',
        'category': 'art',
        'price': 54000000,
        'rarity': 'epic',
        'description': 'Claude Monet impressionist painting',
        'emoji': '🖼️'
    },
    'warhol_marilyn': {
        'name': 'Shot Sage Blue Marilyn (Warhol)',
        'category': 'art',
        'price': 195000000,
        'rarity': 'legendary',
        'description': 'Andy Warhol pop art icon',
        'emoji': '🎨'
    },
    'rodin_thinker': {
        'name': 'The Thinker (Rodin Bronze)',
        'category': 'art',
        'price': 15000000,
        'rarity': 'epic',
        'description': 'Auguste Rodin sculpture',
        'emoji': '🗿'
    }
}

# Rarity colors
RARITY_COLORS = {
    'legendary': 0xFFD700,  # Gold
    'epic': 0x9B30FF,       # Purple
    'rare': 0x4169E1,       # Blue
    'uncommon': 0x32CD32,   # Green
    'common': 0x808080      # Gray
}

def get_collectibles_by_category(category: str):
    """Get all collectibles in a category"""
    return {k: v for k, v in COLLECTIBLES.items() if v['category'] == category}

def get_collectible_by_id(collectible_id: str):
    """Get a collectible by its ID"""
    return COLLECTIBLES.get(collectible_id)

def get_all_categories():
    """Get all collectible categories"""
    return COLLECTIBLE_CATEGORIES
