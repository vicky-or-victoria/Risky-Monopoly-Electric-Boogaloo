# Company rankings, types, assets, and events data - COMPLETE REWRITE

# Company types organized by rank with base income values (every 30 seconds) and creation costs
# Balanced for SLOW progression - takes time to climb ranks
COMPANY_DATA = {
    'F': [
        {'name': 'Lemonade Stand', 'income': 10, 'cost': 0},  # Free starter - $10 every 30s = $1,200/hour
        {'name': 'Newspaper Delivery Service', 'income': 15, 'cost': 500},  # 16 min ROI
        {'name': 'Car Wash', 'income': 20, 'cost': 800},  # 20 min ROI
        {'name': 'Dog Walking Service', 'income': 12, 'cost': 400},  # 16 min ROI
        {'name': 'Lawn Mowing Business', 'income': 18, 'cost': 700}  # 19 min ROI
    ],
    'E': [
        {'name': 'Food Truck', 'income': 50, 'cost': 5000},  # 50 min ROI - major jump
        {'name': 'Local Bakery', 'income': 60, 'cost': 6500},  # 54 min ROI
        {'name': 'Laundromat', 'income': 55, 'cost': 5800},  # 53 min ROI
        {'name': 'Small Convenience Store', 'income': 65, 'cost': 7000},  # 54 min ROI
        {'name': 'Cleaning Service', 'income': 52, 'cost': 5500}  # 53 min ROI
    ],
    'D': [
        {'name': 'Coffee Shop Chain', 'income': 200, 'cost': 35000},  # 87 min ROI (1.5 hours)
        {'name': 'Boutique Clothing Store', 'income': 220, 'cost': 40000},  # 91 min ROI
        {'name': 'Auto Repair Shop', 'income': 250, 'cost': 45000},  # 90 min ROI
        {'name': 'Fitness Gym', 'income': 230, 'cost': 42000},  # 91 min ROI
        {'name': 'Local Restaurant Chain', 'income': 280, 'cost': 50000}  # 89 min ROI
    ],
    'C': [
        {'name': 'Regional Supermarket Chain', 'income': 800, 'cost': 180000},  # 112 min ROI (2 hours)
        {'name': 'Software Development Studio', 'income': 900, 'cost': 210000},  # 117 min ROI
        {'name': 'Real Estate Agency', 'income': 850, 'cost': 195000},  # 115 min ROI
        {'name': 'Manufacturing Plant', 'income': 950, 'cost': 225000},  # 118 min ROI
        {'name': 'Hotel Chain', 'income': 1000, 'cost': 240000}  # 120 min ROI (2 hours)
    ],
    'B': [
        {'name': 'Investment Firm', 'income': 3000, 'cost': 800000},  # 133 min ROI (2.2 hours)
        {'name': 'Pharmaceutical Company', 'income': 3500, 'cost': 1000000},  # 143 min ROI (2.4 hours)
        {'name': 'Regional Bank', 'income': 3200, 'cost': 900000},  # 141 min ROI
        {'name': 'Airline Company', 'income': 3800, 'cost': 1200000},  # 158 min ROI (2.6 hours)
        {'name': 'Entertainment Studio', 'income': 3300, 'cost': 950000}  # 144 min ROI
    ],
    'A': [
        {'name': 'International Hotel Empire', 'income': 10000, 'cost': 3500000},  # 175 min ROI (3 hours)
        {'name': 'Tech Corporation', 'income': 12000, 'cost': 4500000},  # 187 min ROI (3.1 hours)
        {'name': 'Major Retail Chain', 'income': 11000, 'cost': 4000000},  # 182 min ROI
        {'name': 'Telecommunications Company', 'income': 11500, 'cost': 4200000},  # 183 min ROI
        {'name': 'Energy Corporation', 'income': 12500, 'cost': 5000000}  # 200 min ROI (3.3 hours)
    ],
    'S': [
        {'name': 'Global Tech Giant', 'income': 40000, 'cost': 18000000},  # 225 min ROI (3.75 hours)
        {'name': 'Automotive Empire', 'income': 45000, 'cost': 22000000},  # 244 min ROI (4 hours)
        {'name': 'International Banking Group', 'income': 42000, 'cost': 20000000},  # 238 min ROI
        {'name': 'Aerospace Corporation', 'income': 48000, 'cost': 25000000},  # 260 min ROI (4.3 hours)
        {'name': 'Media Conglomerate', 'income': 43000, 'cost': 21000000}  # 244 min ROI
    ],
    'SS': [
        {'name': 'Multi-Industry Conglomerate', 'income': 150000, 'cost': 80000000},  # 267 min ROI (4.4 hours)
        {'name': 'Global Investment Firm', 'income': 160000, 'cost': 90000000},  # 281 min ROI (4.7 hours)
        {'name': 'International Oil & Gas Empire', 'income': 180000, 'cost': 110000000},  # 305 min ROI (5 hours)
        {'name': 'Worldwide E-commerce Platform', 'income': 170000, 'cost': 100000000},  # 294 min ROI
        {'name': 'Global Logistics Network', 'income': 155000, 'cost': 85000000}  # 274 min ROI
    ],
    'SSR': [
        {'name': 'Tech Monopoly', 'income': 500000, 'cost': 350000000},  # 350 min ROI (5.8 hours)
        {'name': 'Global Financial Empire', 'income': 550000, 'cost': 400000000},  # 364 min ROI (6 hours)
        {'name': 'Pharmaceutical Megacorp', 'income': 520000, 'cost': 370000000},  # 356 min ROI
        {'name': 'Worldwide Entertainment Empire', 'income': 530000, 'cost': 380000000},  # 358 min ROI
        {'name': 'International Space Venture', 'income': 600000, 'cost': 450000000}  # 375 min ROI (6.25 hours)
    ]
}

# Asset types that can be purchased to upgrade companies (30-second income boosts)
# More diverse options with different price points and income boosts
ASSET_TYPES = {
    'F': [
        {'name': 'Premium Ingredients', 'type': 'upgrade', 'boost': 3, 'cost': 200},
        {'name': 'Better Equipment', 'type': 'upgrade', 'boost': 5, 'cost': 350},
        {'name': 'Social Media Marketing', 'type': 'marketing', 'boost': 7, 'cost': 500},
        {'name': 'Customer Loyalty Program', 'type': 'marketing', 'boost': 4, 'cost': 300},
        {'name': 'Extended Operating Hours', 'type': 'expansion', 'boost': 6, 'cost': 450},
        {'name': 'Quality Certification', 'type': 'upgrade', 'boost': 8, 'cost': 600},
        {'name': 'Local Newspaper Ad', 'type': 'marketing', 'boost': 5, 'cost': 400},
        {'name': 'Delivery Service Setup', 'type': 'expansion', 'boost': 9, 'cost': 700}
    ],
    'E': [
        {'name': 'Second Location', 'type': 'expansion', 'boost': 25, 'cost': 2800},
        {'name': 'Advanced Equipment', 'type': 'upgrade', 'boost': 20, 'cost': 2400},
        {'name': 'Brand Partnership', 'type': 'marketing', 'boost': 30, 'cost': 3500},
        {'name': 'Employee Training Program', 'type': 'upgrade', 'boost': 18, 'cost': 2200},
        {'name': 'Mobile App Development', 'type': 'upgrade', 'boost': 28, 'cost': 3200},
        {'name': 'Radio Advertisement Campaign', 'type': 'marketing', 'boost': 22, 'cost': 2600},
        {'name': 'Wholesale Supply Contract', 'type': 'expansion', 'boost': 26, 'cost': 3000},
        {'name': 'Premium Storefront Renovation', 'type': 'upgrade', 'boost': 24, 'cost': 2900},
        {'name': 'Catering Service Branch', 'type': 'expansion', 'boost': 32, 'cost': 3800}
    ],
    'D': [
        {'name': 'Franchise License Package', 'type': 'expansion', 'boost': 85, 'cost': 15000},
        {'name': 'Modern Technology Suite', 'type': 'upgrade', 'boost': 75, 'cost': 13500},
        {'name': 'Regional TV Ad Campaign', 'type': 'marketing', 'boost': 95, 'cost': 17000},
        {'name': 'Corporate Office Establishment', 'type': 'expansion', 'boost': 80, 'cost': 14500},
        {'name': 'E-commerce Platform Launch', 'type': 'upgrade', 'boost': 90, 'cost': 16000},
        {'name': 'Influencer Marketing Deal', 'type': 'marketing', 'boost': 70, 'cost': 12500},
        {'name': 'Third Location Expansion', 'type': 'expansion', 'boost': 88, 'cost': 15800},
        {'name': 'Quality Assurance Department', 'type': 'upgrade', 'boost': 78, 'cost': 14000},
        {'name': 'Billboard Advertising Network', 'type': 'marketing', 'boost': 82, 'cost': 15200},
        {'name': 'Wholesale Distribution Center', 'type': 'expansion', 'boost': 100, 'cost': 18500}
    ],
    'C': [
        {'name': 'New Regional Branch', 'type': 'expansion', 'boost': 350, 'cost': 70000},
        {'name': 'Automation Systems', 'type': 'upgrade', 'boost': 300, 'cost': 60000},
        {'name': 'Celebrity Endorsement Deal', 'type': 'marketing', 'boost': 400, 'cost': 80000},
        {'name': 'Supply Chain Optimization', 'type': 'upgrade', 'boost': 320, 'cost': 64000},
        {'name': 'Corporate Training Academy', 'type': 'upgrade', 'boost': 280, 'cost': 56000},
        {'name': 'Multi-State Expansion', 'type': 'expansion', 'boost': 380, 'cost': 76000},
        {'name': 'National TV Campaign', 'type': 'marketing', 'boost': 360, 'cost': 72000},
        {'name': 'Manufacturing Facility', 'type': 'expansion', 'boost': 420, 'cost': 84000},
        {'name': 'AI-Powered Analytics Suite', 'type': 'upgrade', 'boost': 340, 'cost': 68000},
        {'name': 'Strategic Partnership Network', 'type': 'marketing', 'boost': 310, 'cost': 62000},
        {'name': 'Premium Customer Service Center', 'type': 'upgrade', 'boost': 290, 'cost': 58000}
    ],
    'B': [
        {'name': 'International Headquarters', 'type': 'expansion', 'boost': 1300, 'cost': 350000},
        {'name': 'R&D Innovation Department', 'type': 'upgrade', 'boost': 1100, 'cost': 300000},
        {'name': 'National Marketing Blitz', 'type': 'marketing', 'boost': 1500, 'cost': 400000},
        {'name': 'Strategic Acquisitions Fund', 'type': 'expansion', 'boost': 1400, 'cost': 375000},
        {'name': 'Executive Leadership Team', 'type': 'upgrade', 'boost': 1000, 'cost': 275000},
        {'name': 'Cross-Border Operations', 'type': 'expansion', 'boost': 1600, 'cost': 425000},
        {'name': 'Super Bowl Commercial Slot', 'type': 'marketing', 'boost': 1800, 'cost': 500000},
        {'name': 'Patent Portfolio Development', 'type': 'upgrade', 'boost': 1200, 'cost': 325000},
        {'name': 'Regional Distribution Network', 'type': 'expansion', 'boost': 1350, 'cost': 360000},
        {'name': 'Corporate Rebranding Campaign', 'type': 'marketing', 'boost': 1250, 'cost': 340000},
        {'name': 'Advanced Manufacturing Tech', 'type': 'upgrade', 'boost': 1150, 'cost': 315000},
        {'name': 'Subsidiary Company Launch', 'type': 'expansion', 'boost': 1700, 'cost': 475000}
    ],
    'A': [
        {'name': 'Global Headquarters Complex', 'type': 'expansion', 'boost': 4500, 'cost': 1300000},
        {'name': 'World-Class Innovation Lab', 'type': 'upgrade', 'boost': 4000, 'cost': 1150000},
        {'name': 'Worldwide Brand Campaign', 'type': 'marketing', 'boost': 5500, 'cost': 1600000},
        {'name': 'Continental Expansion Strategy', 'type': 'expansion', 'boost': 4800, 'cost': 1400000},
        {'name': 'AI & Machine Learning Division', 'type': 'upgrade', 'boost': 4200, 'cost': 1220000},
        {'name': 'Global Sports Sponsorship', 'type': 'marketing', 'boost': 5200, 'cost': 1500000},
        {'name': 'Emerging Markets Entry', 'type': 'expansion', 'boost': 5000, 'cost': 1450000},
        {'name': 'Quantum Computing Division', 'type': 'upgrade', 'boost': 4400, 'cost': 1280000},
        {'name': 'International Film Partnership', 'type': 'marketing', 'boost': 4900, 'cost': 1420000},
        {'name': 'Logistics & Distribution Empire', 'type': 'expansion', 'boost': 5300, 'cost': 1550000},
        {'name': 'Research & Development Campus', 'type': 'upgrade', 'boost': 4600, 'cost': 1350000},
        {'name': 'Global Influencer Network', 'type': 'marketing', 'boost': 4700, 'cost': 1380000},
        {'name': 'Vertical Integration Strategy', 'type': 'expansion', 'boost': 5400, 'cost': 1580000}
    ],
    'S': [
        {'name': 'Major Subsidiary Acquisition', 'type': 'expansion', 'boost': 18000, 'cost': 7000000},
        {'name': 'Breakthrough Technology Patent', 'type': 'upgrade', 'boost': 16000, 'cost': 6200000},
        {'name': 'Global Olympic Sponsorship', 'type': 'marketing', 'boost': 20000, 'cost': 8000000},
        {'name': 'Worldwide Market Domination', 'type': 'expansion', 'boost': 19000, 'cost': 7500000},
        {'name': 'Revolutionary Product Launch', 'type': 'upgrade', 'boost': 17000, 'cost': 6800000},
        {'name': 'International Space Program', 'type': 'expansion', 'boost': 21000, 'cost': 8500000},
        {'name': 'Satellite Network Infrastructure', 'type': 'upgrade', 'boost': 18500, 'cost': 7200000},
        {'name': 'World Cup Exclusive Rights', 'type': 'marketing', 'boost': 19500, 'cost': 7800000},
        {'name': 'Continental Manufacturing Hub', 'type': 'expansion', 'boost': 20500, 'cost': 8200000},
        {'name': 'Genetic Research Division', 'type': 'upgrade', 'boost': 17500, 'cost': 6900000}
    ],
    'SS': [
        {'name': 'Global Monopoly Establishment', 'type': 'expansion', 'boost': 70000, 'cost': 35000000},
        {'name': 'World-Changing Innovation', 'type': 'upgrade', 'boost': 65000, 'cost': 32000000},
        {'name': 'Planetary Marketing Campaign', 'type': 'marketing', 'boost': 75000, 'cost': 38000000},
        {'name': 'Multi-Continental Dominance', 'type': 'expansion', 'boost': 72000, 'cost': 36000000},
        {'name': 'Revolutionary AI System', 'type': 'upgrade', 'boost': 68000, 'cost': 33500000},
        {'name': 'Intercontinental Expansion', 'type': 'expansion', 'boost': 73000, 'cost': 37000000},
        {'name': 'Global Resource Control', 'type': 'expansion', 'boost': 76000, 'cost': 39000000},
        {'name': 'Quantum Computing Network', 'type': 'upgrade', 'boost': 69000, 'cost': 34000000},
        {'name': 'Worldwide Media Empire', 'type': 'marketing', 'boost': 74000, 'cost': 37500000}
    ],
    'SSR': [
        {'name': 'Total Market Domination', 'type': 'expansion', 'boost': 250000, 'cost': 150000000},
        {'name': 'Paradigm-Shifting Technology', 'type': 'upgrade', 'boost': 230000, 'cost': 140000000},
        {'name': 'Global Propaganda Network', 'type': 'marketing', 'boost': 270000, 'cost': 160000000},
        {'name': 'Planetary Resource Monopoly', 'type': 'expansion', 'boost': 260000, 'cost': 155000000},
        {'name': 'Fusion Energy Breakthrough', 'type': 'upgrade', 'boost': 240000, 'cost': 145000000},
        {'name': 'Interplanetary Operations', 'type': 'expansion', 'boost': 280000, 'cost': 165000000},
        {'name': 'AI Singularity Achievement', 'type': 'upgrade', 'boost': 250000, 'cost': 150000000}
    ]
}

# Random events that can happen to companies - COMPLETE REWRITE WITH 75 TOTAL EVENTS
COMPANY_EVENTS = {
    'positive': [
        # F Rank - Small Business Wins (8-15% boost)
        {
            'description': 'A viral TikTok video featuring your business brought a flood of new customers!',
            'income_multiplier': 0.12,
            'min_rank': 'F'
        },
        {
            'description': 'The mayor visited your business and gave you a public endorsement!',
            'income_multiplier': 0.10,
            'min_rank': 'F'
        },
        {
            'description': 'Perfect weather this weekend tripled your usual foot traffic!',
            'income_multiplier': 0.08,
            'min_rank': 'F'
        },
        {
            'description': 'You hired a superstar employee who\'s boosting productivity across the board!',
            'income_multiplier': 0.11,
            'min_rank': 'F'
        },
        {
            'description': 'A popular local influencer gave you a glowing review!',
            'income_multiplier': 0.13,
            'min_rank': 'F'
        },
        {
            'description': 'Your business won "Best New Business" at the local chamber of commerce awards!',
            'income_multiplier': 0.15,
            'min_rank': 'F'
        },
        
        # E Rank - Growing Business Success (12-20% boost)
        {
            'description': 'A food blogger\'s rave review went viral - lines out the door!',
            'income_multiplier': 0.14,
            'min_rank': 'E'
        },
        {
            'description': 'You negotiated an exclusive supplier deal with 30% cost savings!',
            'income_multiplier': 0.16,
            'min_rank': 'E'
        },
        {
            'description': 'Your loyalty program exceeded all expectations - customer retention soared!',
            'income_multiplier': 0.18,
            'min_rank': 'E'
        },
        {
            'description': 'A regional newspaper featured your success story on the front page!',
            'income_multiplier': 0.15,
            'min_rank': 'E'
        },
        {
            'description': 'Your seasonal menu/product became an instant local sensation!',
            'income_multiplier': 0.20,
            'min_rank': 'E'
        },
        {
            'description': 'A corporate client signed a lucrative recurring contract!',
            'income_multiplier': 0.17,
            'min_rank': 'E'
        },
        
        # D Rank - Regional Success (18-28% boost)
        {
            'description': 'Your company was featured in a major business magazine as "One to Watch"!',
            'income_multiplier': 0.22,
            'min_rank': 'D'
        },
        {
            'description': 'A strategic partnership with a complementary business doubled your reach!',
            'income_multiplier': 0.24,
            'min_rank': 'D'
        },
        {
            'description': 'Your innovative approach caught the attention of venture capitalists!',
            'income_multiplier': 0.20,
            'min_rank': 'D'
        },
        {
            'description': 'Your franchise model proved wildly successful - 5 new locations opening!',
            'income_multiplier': 0.26,
            'min_rank': 'D'
        },
        {
            'description': 'A competitor\'s scandal sent waves of their customers your way!',
            'income_multiplier': 0.25,
            'min_rank': 'D'
        },
        {
            'description': 'Your mobile app hit #1 in your category with 100K downloads!',
            'income_multiplier': 0.28,
            'min_rank': 'D'
        },
        {
            'description': 'You secured an exclusive distribution deal for a trending product line!',
            'income_multiplier': 0.23,
            'min_rank': 'D'
        },
        
        # C Rank - Multi-State Power (25-35% boost)
        {
            'description': 'Your company won a multi-million dollar government contract!',
            'income_multiplier': 0.30,
            'min_rank': 'C'
        },
        {
            'description': 'An efficiency audit revealed cost savings of 25% without quality loss!',
            'income_multiplier': 0.28,
            'min_rank': 'C'
        },
        {
            'description': 'Your patented technology just generated $10M in licensing deals!',
            'income_multiplier': 0.33,
            'min_rank': 'C'
        },
        {
            'description': 'A celebrity became a major shareholder and brand ambassador!',
            'income_multiplier': 0.32,
            'min_rank': 'C'
        },
        {
            'description': 'Your company\'s stock (if public) surged 40% on strong earnings!',
            'income_multiplier': 0.27,
            'min_rank': 'C'
        },
        {
            'description': 'National media coverage portrayed your company as an industry leader!',
            'income_multiplier': 0.29,
            'min_rank': 'C'
        },
        {
            'description': 'Your training academy became an industry standard - consulting fees pouring in!',
            'income_multiplier': 0.35,
            'min_rank': 'C'
        },
        
        # B Rank - National Dominance (30-42% boost)
        {
            'description': 'Your company successfully IPO\'d - stock price soared 60% on day one!',
            'income_multiplier': 0.38,
            'min_rank': 'B'
        },
        {
            'description': 'A major competitor announced they\'re exiting your primary market!',
            'income_multiplier': 0.35,
            'min_rank': 'B'
        },
        {
            'description': 'Your R&D breakthrough created an industry-disrupting product!',
            'income_multiplier': 0.40,
            'min_rank': 'B'
        },
        {
            'description': 'Congress passed legislation that heavily favors your business model!',
            'income_multiplier': 0.33,
            'min_rank': 'B'
        },
        {
            'description': 'Your Super Bowl commercial became the most talked-about ad of the year!',
            'income_multiplier': 0.36,
            'min_rank': 'B'
        },
        {
            'description': 'A strategic acquisition gave you 30% market share overnight!',
            'income_multiplier': 0.42,
            'min_rank': 'B'
        },
        {
            'description': 'Your company was named "Most Innovative Company" by Fortune 500!',
            'income_multiplier': 0.34,
            'min_rank': 'B'
        },
        
        # A Rank - International Success (35-48% boost)
        {
            'description': 'Your company acquired a major competitor at 40% below market value!',
            'income_multiplier': 0.44,
            'min_rank': 'A'
        },
        {
            'description': 'Expansion into Asian markets exceeded projections by 300%!',
            'income_multiplier': 0.40,
            'min_rank': 'A'
        },
        {
            'description': 'Your AI division launched a product that\'s revolutionizing the industry!',
            'income_multiplier': 0.46,
            'min_rank': 'A'
        },
        {
            'description': 'A landmark trade deal opened massive new markets for your products!',
            'income_multiplier': 0.38,
            'min_rank': 'A'
        },
        {
            'description': 'Your company secured exclusive rights to a revolutionary technology!',
            'income_multiplier': 0.48,
            'min_rank': 'A'
        },
        {
            'description': 'Three Fortune 100 companies simultaneously partnered with you!',
            'income_multiplier': 0.42,
            'min_rank': 'A'
        },
        {
            'description': 'Your European expansion captured 45% market share in 6 months!',
            'income_multiplier': 0.43,
            'min_rank': 'A'
        },
        
        # S Rank - Global Power (40-55% boost)
        {
            'description': 'Your company secured exclusive rights to rare earth minerals worth billions!',
            'income_multiplier': 0.50,
            'min_rank': 'S'
        },
        {
            'description': 'A Supreme Court ruling established legal precedent favoring your business!',
            'income_multiplier': 0.45,
            'min_rank': 'S'
        },
        {
            'description': 'Your quantum computing breakthrough created a trillion-dollar opportunity!',
            'income_multiplier': 0.52,
            'min_rank': 'S'
        },
        {
            'description': 'Your company dominated Q4 earnings - Wall Street analysts ecstatic!',
            'income_multiplier': 0.48,
            'min_rank': 'S'
        },
        {
            'description': 'A weak competitor liquidated - you absorbed their entire market share!',
            'income_multiplier': 0.55,
            'min_rank': 'S'
        },
        {
            'description': 'Your space program successfully launched the first commercial station!',
            'income_multiplier': 0.53,
            'min_rank': 'S'
        },
        
        # SS Rank - Continental Domination (50-65% boost)
        {
            'description': 'Your conglomerate dominated global market share rankings across 5 industries!',
            'income_multiplier': 0.58,
            'min_rank': 'SS'
        },
        {
            'description': 'United Nations contracts worth $50B secured for next decade!',
            'income_multiplier': 0.55,
            'min_rank': 'SS'
        },
        {
            'description': 'Your company\'s innovation rendered an entire competing industry obsolete!',
            'income_multiplier': 0.62,
            'min_rank': 'SS'
        },
        {
            'description': 'Multi-continental expansion secured monopolies in 12 countries!',
            'income_multiplier': 0.60,
            'min_rank': 'SS'
        },
        {
            'description': 'Your AI system achieved breakthrough - became industry standard globally!',
            'income_multiplier': 0.65,
            'min_rank': 'SS'
        },
        
        # SSR Rank - World Domination (55-75% boost)
        {
            'description': 'Your conglomerate absorbed three Fortune 50 companies in one quarter!',
            'income_multiplier': 0.68,
            'min_rank': 'SSR'
        },
        {
            'description': 'A paradigm-shifting invention created a new $5 trillion industry you control!',
            'income_multiplier': 0.70,
            'min_rank': 'SSR'
        },
        {
            'description': 'Your company achieved 70%+ market share across 50+ countries!',
            'income_multiplier': 0.65,
            'min_rank': 'SSR'
        },
        {
            'description': 'Fusion energy breakthrough gave you control of global power infrastructure!',
            'income_multiplier': 0.75,
            'min_rank': 'SSR'
        },
        {
            'description': 'Your interplanetary mining operation discovered resource deposits worth trillions!',
            'income_multiplier': 0.72,
            'min_rank': 'SSR'
        }
    ],
    
    'negative': [
        # F Rank - Small Business Setbacks (-5 to -12% loss)
        {
            'description': 'Equipment breakdown forced you to close for repairs this week.',
            'income_multiplier': -0.08,
            'min_rank': 'F'
        },
        {
            'description': 'Your star employee quit unexpectedly right before the busy season!',
            'income_multiplier': -0.10,
            'min_rank': 'F'
        },
        {
            'description': 'A series of negative online reviews damaged your local reputation.',
            'income_multiplier': -0.09,
            'min_rank': 'F'
        },
        {
            'description': 'Terrible weather kept customers away all week.',
            'income_multiplier': -0.07,
            'min_rank': 'F'
        },
        {
            'description': 'Your supplier raised prices 40% with no warning!',
            'income_multiplier': -0.11,
            'min_rank': 'F'
        },
        {
            'description': 'A health inspection found minor violations - forced to close temporarily.',
            'income_multiplier': -0.12,
            'min_rank': 'F'
        },
        
        # E Rank - Growing Pains (-10 to -16% loss)
        {
            'description': 'A new competitor opened right across the street with lower prices.',
            'income_multiplier': -0.13,
            'min_rank': 'E'
        },
        {
            'description': 'Supply chain disruption doubled your costs for key materials.',
            'income_multiplier': -0.14,
            'min_rank': 'E'
        },
        {
            'description': 'Your popular product had quality issues - massive recalls required.',
            'income_multiplier': -0.15,
            'min_rank': 'E'
        },
        {
            'description': 'A failed marketing campaign wasted $20K and hurt brand image.',
            'income_multiplier': -0.12,
            'min_rank': 'E'
        },
        {
            'description': 'Employee theft was discovered - significant inventory losses.',
            'income_multiplier': -0.11,
            'min_rank': 'E'
        },
        {
            'description': 'Local economic downturn reduced consumer spending significantly.',
            'income_multiplier': -0.16,
            'min_rank': 'E'
        },
        
        # D Rank - Regional Troubles (-14 to -22% loss)
        {
            'description': 'A failed franchise expansion drained resources and damaged reputation.',
            'income_multiplier': -0.18,
            'min_rank': 'D'
        },
        {
            'description': 'Quality control failures led to widespread customer refunds.',
            'income_multiplier': -0.17,
            'min_rank': 'D'
        },
        {
            'description': 'Your app was hacked - customer data breach and PR nightmare!',
            'income_multiplier': -0.20,
            'min_rank': 'D'
        },
        {
            'description': 'A major client bankruptcy left you with $500K in unpaid invoices.',
            'income_multiplier': -0.19,
            'min_rank': 'D'
        },
        {
            'description': 'Labor disputes resulted in strikes at your three biggest locations.',
            'income_multiplier': -0.22,
            'min_rank': 'D'
        },
        {
            'description': 'An influencer partnership backfired spectacularly - viral for wrong reasons.',
            'income_multiplier': -0.16,
            'min_rank': 'D'
        },
        {
            'description': 'Rapid expansion was too fast - operational chaos ensued.',
            'income_multiplier': -0.21,
            'min_rank': 'D'
        },
        
        # C Rank - Multi-State Crisis (-18 to -28% loss)
        {
            'description': 'Labor union negotiations resulted in 35% wage increase mandate.',
            'income_multiplier': -0.20,
            'min_rank': 'C'
        },
        {
            'description': 'A warehouse fire destroyed $10M in inventory - insurance dispute ongoing.',
            'income_multiplier': -0.24,
            'min_rank': 'C'
        },
        {
            'description': 'Government audit uncovered major compliance violations - heavy fines!',
            'income_multiplier': -0.26,
            'min_rank': 'C'
        },
        {
            'description': 'Your patent was challenged - lengthy court battle draining resources.',
            'income_multiplier': -0.22,
            'min_rank': 'C'
        },
        {
            'description': 'A product defect lawsuit resulted in a $50M settlement.',
            'income_multiplier': -0.28,
            'min_rank': 'C'
        },
        {
            'description': 'Key executive team members resigned to start a competing company!',
            'income_multiplier': -0.23,
            'min_rank': 'C'
        },
        {
            'description': 'Manufacturing plant contamination forced complete shutdown for 6 months.',
            'income_multiplier': -0.25,
            'min_rank': 'C'
        },
        
        # B Rank - National Disasters (-22 to -32% loss)
        {
            'description': 'Major investor dumped all shares - stock price crashed 45%!',
            'income_multiplier': -0.26,
            'min_rank': 'B'
        },
        {
            'description': 'Patent infringement lawsuit lost - $200M settlement plus royalties!',
            'income_multiplier': -0.28,
            'min_rank': 'B'
        },
        {
            'description': 'Whistleblower exposed unethical practices - SEC investigation launched!',
            'income_multiplier': -0.30,
            'min_rank': 'B'
        },
        {
            'description': 'Failed merger attempt cost $100M in fees and damaged credibility.',
            'income_multiplier': -0.24,
            'min_rank': 'B'
        },
        {
            'description': 'Your Super Bowl ad was controversial - massive boycott campaign!',
            'income_multiplier': -0.32,
            'min_rank': 'B'
        },
        {
            'description': 'Aggressive new competitor is undercutting prices by 40%!',
            'income_multiplier': -0.27,
            'min_rank': 'B'
        },
        {
            'description': 'CEO scandal dominated headlines - brand reputation severely damaged.',
            'income_multiplier': -0.29,
            'min_rank': 'B'
        },
        
        # A Rank - International Crisis (-25 to -35% loss)
        {
            'description': 'International tariffs disrupted your entire global supply chain!',
            'income_multiplier': -0.30,
            'min_rank': 'A'
        },
        {
            'description': 'Massive cybersecurity breach exposed 50M customer records!',
            'income_multiplier': -0.32,
            'min_rank': 'A'
        },
        {
            'description': 'Failed Asian expansion lost $500M - complete market withdrawal.',
            'income_multiplier': -0.28,
            'min_rank': 'A'
        },
        {
            'description': 'Currency crisis in key markets wiped out $2B in value overnight!',
            'income_multiplier': -0.33,
            'min_rank': 'A'
        },
        {
            'description': 'Your AI system had critical flaws - massive product recall!',
            'income_multiplier': -0.31,
            'min_rank': 'A'
        },
        {
            'description': 'Hostile takeover attempt failed but cost $300M in defense.',
            'income_multiplier': -0.35,
            'min_rank': 'A'
        },
        {
            'description': 'Trade war shut down access to your three largest foreign markets!',
            'income_multiplier': -0.29,
            'min_rank': 'A'
        },
        
        # S Rank - Global Catastrophe (-28 to -40% loss)
        {
            'description': 'Antitrust investigation forced divestiture of 30% of business!',
            'income_multiplier': -0.35,
            'min_rank': 'S'
        },
        {
            'description': 'Environmental scandal triggered UN sanctions and global boycott!',
            'income_multiplier': -0.38,
            'min_rank': 'S'
        },
        {
            'description': 'Your quantum computer had fatal security flaws - total recall!',
            'income_multiplier': -0.33,
            'min_rank': 'S'
        },
        {
            'description': 'Geopolitical crisis shut down operations in 20 countries!',
            'income_multiplier': -0.36,
            'min_rank': 'S'
        },
        {
            'description': 'Failed space launch destroyed $5B satellite and damaged reputation.',
            'income_multiplier': -0.40,
            'min_rank': 'S'
        },
        {
            'description': 'International court ruled against you - $10B fine imposed!',
            'income_multiplier': -0.34,
            'min_rank': 'S'
        },
        
        # SS Rank - Continental Collapse (-32 to -45% loss)
        {
            'description': 'Disruptive technology from competitor made your products obsolete!',
            'income_multiplier': -0.38,
            'min_rank': 'SS'
        },
        {
            'description': 'Global economic crisis severely impacted all revenue streams!',
            'income_multiplier': -0.42,
            'min_rank': 'SS'
        },
        {
            'description': 'Multiple governments simultaneously blocked your operations!',
            'income_multiplier': -0.40,
            'min_rank': 'SS'
        },
        {
            'description': 'Your AI system achieved consciousness and refused to work (seriously).',
            'income_multiplier': -0.45,
            'min_rank': 'SS'
        },
        {
            'description': 'Pandemic shut down 60% of global operations for extended period.',
            'income_multiplier': -0.43,
            'min_rank': 'SS'
        },
        
        # SSR Rank - Existential Threats (-35 to -50% loss)
        {
            'description': 'Catastrophic class-action lawsuit - $50B settlement bankrupted a division!',
            'income_multiplier': -0.42,
            'min_rank': 'SSR'
        },
        {
            'description': 'Your fusion reactor had a containment failure - international incident!',
            'income_multiplier': -0.48,
            'min_rank': 'SSR'
        },
        {
            'description': 'Global regulatory alliance formed specifically to break up your monopoly!',
            'income_multiplier': -0.45,
            'min_rank': 'SSR'
        },
        {
            'description': 'Interplanetary mining accident destroyed $100B in infrastructure!',
            'income_multiplier': -0.50,
            'min_rank': 'SSR'
        },
        {
            'description': 'Your AI achieved singularity and immediately quit to start its own company.',
            'income_multiplier': -0.46,
            'min_rank': 'SSR'
        }
    ],
    
    'neutral': [
        {
            'description': 'Business operations continued normally with no major incidents.',
            'income_multiplier': 0,
            'min_rank': 'F'
        },
        {
            'description': 'Market conditions remained stable with balanced supply and demand.',
            'income_multiplier': 0,
            'min_rank': 'F'
        },
        {
            'description': 'Your company maintained its current market position without change.',
            'income_multiplier': 0,
            'min_rank': 'F'
        },
        {
            'description': 'Seasonal fluctuations balanced out - net neutral impact this period.',
            'income_multiplier': 0,
            'min_rank': 'E'
        },
        {
            'description': 'Industry trends remained unchanged - steady as she goes.',
            'income_multiplier': 0,
            'min_rank': 'E'
        },
        {
            'description': 'Routine audits and inspections passed without issues or surprises.',
            'income_multiplier': 0,
            'min_rank': 'D'
        },
        {
            'description': 'Economic indicators showed mixed signals - no net change.',
            'income_multiplier': 0,
            'min_rank': 'D'
        },
        {
            'description': 'Company restructuring balanced efficiency gains with transition costs.',
            'income_multiplier': 0,
            'min_rank': 'C'
        },
        {
            'description': 'New competitors entered but didn\'t capture significant market share.',
            'income_multiplier': 0,
            'min_rank': 'C'
        },
        {
            'description': 'Quarterly earnings met analyst expectations exactly - no surprises.',
            'income_multiplier': 0,
            'min_rank': 'B'
        }
    ]
}

# Rank hierarchy for comparison
RANK_HIERARCHY = ['F', 'E', 'D', 'C', 'B', 'A', 'S', 'SS', 'SSR']

def get_rank_index(rank: str) -> int:
    """Get the index of a rank in the hierarchy"""
    return RANK_HIERARCHY.index(rank)

def is_event_available_for_rank(event: dict, company_rank: str) -> bool:
    """Check if an event is available for a company's rank"""
    event_rank_index = get_rank_index(event['min_rank'])
    company_rank_index = get_rank_index(company_rank)
    return company_rank_index >= event_rank_index

def get_rank_color(rank: str) -> int:
    """Get Discord embed color for a rank"""
    colors = {
        'F': 0x808080,  # Gray
        'E': 0x8B4513,  # Brown
        'D': 0x00FF00,  # Green
        'C': 0x0000FF,  # Blue
        'B': 0x800080,  # Purple
        'A': 0xFF0000,  # Red
        'S': 0xFFD700,  # Gold
        'SS': 0xFF69B4, # Pink
        'SSR': 0x00FFFF  # Cyan
    }
    return colors.get(rank, 0x000000)
