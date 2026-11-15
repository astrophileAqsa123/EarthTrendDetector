# config.py
"""Variables, guided-investigation presets and demo stories for the Earth System Trend Detective.

All data come from NASA POWER (https://power.larc.nasa.gov), which serves
MERRA-2 reanalysis / GEOS products from NASA GMAO. No API key is needed.
"""

POWER_SOURCE = "NASA POWER (MERRA-2 / GEOS, NASA GMAO), monthly, ~0.5° × 0.625° grid"

CATEGORIES = ["🌡️ Heat", "💧 Water", "🌱 Land & Soil", "☀️ Air, Sun & Energy"]

# Each variable carries plain-language text so non-scientists can follow along.
#   definition  : what is this, in one sentence
#   why         : why anyone should care
#   up_phrase / down_phrase : how to describe a rising / falling trend in everyday words
#   keywords    : used by the offline keyword matcher in the guided mode
VARIABLES = {
    "Mean Air Temperature (°C)": {
        "param": "T2M", "unit": "°C", "category": "🌡️ Heat", "emoji": "🌡️",
        "plain_name": "average air temperature",
        "question": "🌡️ Is it getting warmer or cooler?",
        "story": "Tracks regional warming or cooling over decades.",
        "definition": "The average temperature of the air about 2 metres above the ground (head height).",
        "why": "It is the most familiar sign of climate change and affects health, farming and energy use.",
        "up_phrase": "getting warmer", "down_phrase": "getting cooler",
        "keywords": ["temperature", "warm", "warming", "hot", "heat", "cool", "cold", "climate change"],
        "source": "MERRA-2 2 m air temperature",
    },
    "Daytime High Temperature (°C)": {
        "param": "T2M_MAX", "unit": "°C", "category": "🌡️ Heat", "emoji": "🔥",
        "plain_name": "daytime high temperature",
        "question": "🔥 Are the hottest hours of the day getting hotter?",
        "story": "Shows whether daily peaks are rising, which matters for heatwaves.",
        "definition": "The warmest temperature reached on a typical day, averaged over each month.",
        "why": "Hotter afternoons raise heat-stress risk for people, crops and power grids.",
        "up_phrase": "getting hotter in the daytime", "down_phrase": "getting cooler in the daytime",
        "keywords": ["heatwave", "heat wave", "summer", "hot days", "afternoon", "maximum", "high"],
        "source": "MERRA-2 2 m maximum air temperature",
    },
    "Night-time Low Temperature (°C)": {
        "param": "T2M_MIN", "unit": "°C", "category": "🌡️ Heat", "emoji": "🌙",
        "plain_name": "night-time low temperature",
        "question": "🌙 Are nights getting warmer?",
        "story": "Nights often warm faster than days, which reduces overnight relief from heat.",
        "definition": "The coolest temperature reached on a typical night, averaged over each month.",
        "why": "Warm nights stop the body and the land from cooling down and can melt snow and ice earlier.",
        "up_phrase": "getting warmer at night", "down_phrase": "getting colder at night",
        "keywords": ["night", "minimum", "frost", "cold nights", "low"],
        "source": "MERRA-2 2 m minimum air temperature",
    },
    "Land Surface Temperature (°C)": {
        "param": "TS", "unit": "°C", "category": "🌱 Land & Soil", "emoji": "🏜️",
        "plain_name": "ground surface temperature",
        "question": "🏜️ Is the ground itself heating up?",
        "story": "Skin temperature of the surface, important for cities, deserts and ice.",
        "definition": "How hot the surface of the ground (or ice, or sea) is, rather than the air above it.",
        "why": "Hot ground dries soil, stresses plants and drives heat in cities.",
        "up_phrase": "heating up at the surface", "down_phrase": "cooling at the surface",
        "keywords": ["ground", "surface", "land", "urban", "city heat", "skin"],
        "source": "MERRA-2 Earth skin temperature",
    },
    "Precipitation (mm/day)": {
        "param": "PRECTOTCORR", "unit": "mm/day", "category": "💧 Water", "emoji": "🌧️",
        "plain_name": "rainfall",
        "question": "🌧️ Is rainfall changing?",
        "story": "Reveals 'wet gets wetter, dry gets drier' hydrological shifts.",
        "definition": "How much rain and snow falls, shown as an average depth of water per day.",
        "why": "Rainfall decides water supply, floods, droughts and harvests.",
        "up_phrase": "getting rainier", "down_phrase": "getting drier",
        "keywords": ["rain", "rainfall", "precipitation", "monsoon", "flood", "drought", "wet", "dry", "snow"],
        "source": "MERRA-2 bias-corrected total precipitation (monthly mean of daily rate)",
    },
    "Surface Soil Wetness (0-1)": {
        "param": "GWETTOP", "unit": "fraction", "category": "🌱 Land & Soil", "emoji": "🌱",
        "plain_name": "topsoil wetness",
        "question": "🌱 Are soils getting wetter or drier?",
        "story": "Indicates long-term agricultural drought or soil saturation.",
        "definition": "How damp the top few centimetres of soil are, from 0 (bone dry) to 1 (soaked).",
        "why": "Farmers and wildfire managers watch it closely. Dry topsoil means drought stress.",
        "up_phrase": "getting wetter", "down_phrase": "getting drier",
        "keywords": ["soil", "farm", "agriculture", "crop", "drought", "moisture", "dry"],
        "source": "GEOS/MERRA-2 surface soil wetness (0 = dry, 1 = saturated)",
    },
    "Root-zone Soil Wetness (0-1)": {
        "param": "GWETROOT", "unit": "fraction", "category": "🌱 Land & Soil", "emoji": "🌾",
        "plain_name": "root-zone soil wetness",
        "question": "🌾 Do plant roots have more or less water?",
        "story": "Deeper soil water that crops and forests rely on.",
        "definition": "How damp the soil is where most plant roots grow (roughly the top metre), from 0 to 1.",
        "why": "It reacts more slowly than topsoil, so it shows lasting drought or recovery.",
        "up_phrase": "getting wetter at root depth", "down_phrase": "getting drier at root depth",
        "keywords": ["root", "crop", "forest", "vegetation", "groundwater", "deep soil", "drought"],
        "source": "GEOS/MERRA-2 root-zone soil wetness (0 = dry, 1 = saturated)",
    },
    "Evaporation from Land (mm/day)": {
        "param": "EVLAND", "unit": "mm/day", "category": "💧 Water", "emoji": "♨️",
        "plain_name": "evaporation from land",
        "question": "♨️ Is more water leaving the land into the air?",
        "story": "Links the water and energy cycles. It rises with heat and with available water.",
        "definition": "How much water evaporates from the land surface and plants, as depth per day.",
        "why": "It cools the surface, feeds clouds and rain, and dries out soil and rivers.",
        "up_phrase": "evaporating more", "down_phrase": "evaporating less",
        "keywords": ["evaporation", "evapotranspiration", "water cycle", "river", "lake", "reservoir"],
        "source": "MERRA-2 land evaporation",
    },
    "Relative Humidity (%)": {
        "param": "RH2M", "unit": "%", "category": "☀️ Air, Sun & Energy", "emoji": "💦",
        "plain_name": "air humidity",
        "question": "💦 Is the air getting more or less humid?",
        "story": "Humid heat is harder on the body than dry heat.",
        "definition": "How much water vapour the air holds compared with the most it could hold at that temperature.",
        "why": "It affects comfort, fire risk, mould, crops and how dangerous a heatwave feels.",
        "up_phrase": "getting more humid", "down_phrase": "getting drier (less humid air)",
        "keywords": ["humidity", "humid", "muggy", "fire", "dry air"],
        "source": "MERRA-2 2 m relative humidity",
    },
    "Mean Wind Speed at 10 m (m/s)": {
        "param": "WS10M", "unit": "m/s", "category": "☀️ Air, Sun & Energy", "emoji": "💨",
        "plain_name": "wind speed",
        "question": "💨 Are winds speeding up or slowing down?",
        "story": "Shows shifts in atmospheric circulation and wind-energy potential.",
        "definition": "The average speed of the wind about 10 metres above the ground.",
        "why": "It matters for wind power, dust, storms and how fast wildfires spread.",
        "up_phrase": "speeding up", "down_phrase": "slowing down",
        "keywords": ["wind", "storm", "wind power", "turbine", "dust", "cyclone"],
        "source": "MERRA-2 10 m wind speed",
        "caveat": "Reanalysis wind trends are unreliable: they can be created by changes in the observing "
                  "systems the model assimilates (satellites, stations) and often disagree with station records. "
                  "Treat any wind trend here as a hint, not a finding.",
    },
    "Sunlight at the Surface (kWh/m²/day)": {
        "param": "ALLSKY_SFC_SW_DWN", "unit": "kWh/m²/day", "category": "☀️ Air, Sun & Energy", "emoji": "☀️",
        "plain_name": "sunlight reaching the ground",
        "question": "☀️ Is more or less sunlight reaching the ground?",
        "story": "Important for solar power, crop growth and air pollution (haze dims the sun).",
        "definition": "How much solar energy actually lands on one square metre of ground per day, clouds and haze included.",
        "why": "It decides how much electricity solar panels make and how fast plants can grow.",
        "up_phrase": "getting sunnier", "down_phrase": "getting dimmer",
        "keywords": ["sun", "sunlight", "solar", "solar power", "pollution", "haze", "smog", "radiation"],
        "source": "MERRA-2/CERES all-sky surface shortwave downward irradiance",
    },
    "Cloud Cover (%)": {
        "param": "CLOUD_AMT", "unit": "%", "category": "☀️ Air, Sun & Energy", "emoji": "☁️",
        "plain_name": "cloud cover",
        "question": "☁️ Is the sky getting cloudier or clearer?",
        "story": "Clouds both cool (by blocking sun) and warm (by trapping heat), so changes matter.",
        "definition": "The share of the sky covered by cloud, on average.",
        "why": "Clouds are a major wild card in climate change and affect rain and solar power.",
        "up_phrase": "getting cloudier", "down_phrase": "getting clearer",
        "keywords": ["cloud", "sky", "overcast", "clear sky"],
        "source": "MERRA-2 cloud amount",
    },
}

# Typical places for the guided "build your own investigation" flow.
PLACE_PRESETS = {
    "🏜️ Desert": [
        {"name": "Tamanrasset, Algeria (Sahara)", "lat": 22.785, "lon": 5.5228},
        {"name": "Riyadh, Saudi Arabia", "lat": 24.7136, "lon": 46.6753},
        {"name": "Alice Springs, Australia", "lat": -23.698, "lon": 133.8807},
    ],
    "🌴 Rainforest": [
        {"name": "Manaus, Amazon, Brazil", "lat": -3.119, "lon": -60.0217},
        {"name": "Kisangani, Congo Basin", "lat": 0.5153, "lon": 25.19},
        {"name": "Pontianak, Borneo, Indonesia", "lat": -0.0263, "lon": 109.3425},
    ],
    "🏙️ Megacity": [
        {"name": "Islamabad, Pakistan", "lat": 33.6844, "lon": 73.0479},
        {"name": "Delhi, India", "lat": 28.6139, "lon": 77.209},
        {"name": "Lagos, Nigeria", "lat": 6.5244, "lon": 3.3792},
        {"name": "Beijing, China", "lat": 39.9042, "lon": 116.4074},
    ],
    "🧊 Polar & ice": [
        {"name": "Longyearbyen, Svalbard", "lat": 78.2232, "lon": 15.6267},
        {"name": "Ilulissat, Greenland", "lat": 69.2198, "lon": -51.0986},
        {"name": "Yakutsk, Siberia", "lat": 62.0355, "lon": 129.6755},
    ],
    "⛰️ High mountains": [
        {"name": "Lhasa, Tibetan Plateau", "lat": 29.65, "lon": 91.1},
        {"name": "La Paz, Bolivia (Andes)", "lat": -16.5, "lon": -68.15},
        {"name": "Gilgit, Pakistan (Karakoram)", "lat": 35.9208, "lon": 74.3144},
    ],
    "🌾 Farmland": [
        {"name": "Lahore, Punjab, Pakistan", "lat": 31.5204, "lon": 74.3587},
        {"name": "Des Moines, Iowa, USA", "lat": 41.5868, "lon": -93.625},
        {"name": "Mato Grosso, Brazil (soy belt)", "lat": -13.0, "lon": -56.0},
    ],
    "🏝️ Island & coast": [
        {"name": "Malé, Maldives", "lat": 4.1755, "lon": 73.5093},
        {"name": "Jakarta, Indonesia", "lat": -6.2088, "lon": 106.8456},
        {"name": "Lima, Peru", "lat": -12.0464, "lon": -77.0428},
    ],
}

TIME_WINDOWS = {
    "Last 15 years (2011–2025)": (2011, 2025),
    "Last 25 years (2001–2025)": (2001, 2025),
    "As far back as possible (1981–2025)": (1981, 2025),
}

# Story-driven demos. These are hypotheses to TEST, not guaranteed results: the app reports
# whatever the data actually show (including "no significant trend").
STORIES = {
    "Arctic Amplification": {
        "emoji": "🧊",
        "mystery": "Scientists say the Arctic warms faster than most of the planet. Does a tiny Arctic town "
                   "look different from a South Asian capital?",
        "clues": ["Compare the speed of change (°C per 10 years) at the two places.",
                  "Check how sure we are for each place."],
        "region_a": {"name": "Longyearbyen, Svalbard", "lat": 78.2232, "lon": 15.6267},
        "region_b": {"name": "Islamabad, Pakistan", "lat": 33.6844, "lon": 73.0479},
        "variable": "Mean Air Temperature (°C)",
        "years": (1981, 2025),
    },
    "Rain Across the Indus": {
        "emoji": "🌧️",
        "mystery": "Rain patterns are shifting in many places, sometimes in opposite directions. "
                   "How are the monsoon-fed plains of Punjab doing compared with Scandinavia?",
        "clues": ["Look for opposite directions between the two places.",
                  "Open the 'Is it solid?' tab. Does the answer change with the start year?"],
        "region_a": {"name": "Lahore, Pakistan", "lat": 31.5204, "lon": 74.3587},
        "region_b": {"name": "Stockholm, Sweden", "lat": 59.3293, "lon": 18.0686},
        "variable": "Precipitation (mm/day)",
        "years": (1981, 2025),
    },
    "El Niño's Two Faces": {
        "emoji": "🌊",
        "mystery": "El Niño can bring floods to the Peruvian coast and drought to Indonesia. "
                   "Do the long-term rainfall trends at the two places match?",
        "clues": ["Rainfall here is very erratic. Watch how wide the scatter is around the trend line.",
                  "Is the trend solid, or does it depend on which years you choose?"],
        "region_a": {"name": "Lima, Peru", "lat": -12.0464, "lon": -77.0428},
        "region_b": {"name": "Jakarta, Indonesia", "lat": -6.2088, "lon": 106.8456},
        "variable": "Precipitation (mm/day)",
        "years": (1981, 2025),
    },
    "The Sahel: Recovery or Drought?": {
        "emoji": "🌾",
        "mystery": "The Sahel suffered a devastating drought in the 1970s and 80s. Has rainfall come back "
                   "since 1981, and is the Sahara next door behaving the same way?",
        "clues": ["Compare the Sahel (Niger) with the Sahara (Algeria).",
                  "Check the 'time to significance' note if a trend isn't clear yet."],
        "region_a": {"name": "Niamey, Niger (Sahel)", "lat": 13.5116, "lon": 2.1254},
        "region_b": {"name": "Tamanrasset, Algeria (Sahara)", "lat": 22.785, "lon": 5.5228},
        "variable": "Precipitation (mm/day)",
        "years": (1981, 2025),
    },
    "Amazon: Edge vs. Deep Forest": {
        "emoji": "🌴",
        "mystery": "Parts of the southern Amazon have seen heavy forest clearing. Do the clearing frontier "
                   "and the deep forest show different changes in daytime heat?",
        "clues": ["Porto Velho sits near the 'arc of deforestation'. Manaus is deeper in the forest.",
                  "Remember: a trend alone doesn't prove the cause."],
        "region_a": {"name": "Porto Velho, Rondônia, Brazil", "lat": -8.7612, "lon": -63.9039},
        "region_b": {"name": "Manaus, Amazonas, Brazil", "lat": -3.119, "lon": -60.0217},
        "variable": "Daytime High Temperature (°C)",
        "years": (1981, 2025),
    },
    "The Third Pole: Warming Nights": {
        "emoji": "⛰️",
        "mystery": "The Tibetan Plateau holds the largest ice store outside the poles. Are its nights "
                   "warming, and is it different from the Pakistani lowlands?",
        "clues": ["Compare night-time lows at Lhasa and Islamabad.",
                  "Which place has the steeper trend line?"],
        "region_a": {"name": "Lhasa, Tibetan Plateau", "lat": 29.65, "lon": 91.1},
        "region_b": {"name": "Islamabad, Pakistan", "lat": 33.6844, "lon": 73.0479},
        "variable": "Night-time Low Temperature (°C)",
        "years": (1981, 2025),
    },
}
