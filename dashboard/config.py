"""
Dashboard configuration — hospital mappings, coordinates, and populations.
"""

# Hospital -> Region mapping (from preprocessing/cleaning.ipynb)
HOSPITAL_TO_REGION = {
    # HSE Dublin and North East
    "Beaumont Hospital":                        "HSE Dublin and North East",
    "Cavan General Hospital":                   "HSE Dublin and North East",
    "Connolly Hospital":                        "HSE Dublin and North East",
    "Louth County Hospital":                    "HSE Dublin and North East",
    "Mater Misericordiae University Hospital":  "HSE Dublin and North East",
    "National Orthopaedic Hospital Cappagh":    "HSE Dublin and North East",
    "Our Lady of Lourdes Hospital":             "HSE Dublin and North East",
    "Our Lady's Hospital Navan":                "HSE Dublin and North East",

    # HSE Dublin and Midlands
    "CHI at Crumlin":                           "HSE Dublin and Midlands",
    "CHI at Tallaght":                          "HSE Dublin and Midlands",
    "CHI at Temple Street":                     "HSE Dublin and Midlands",
    "MRH Mullingar":                            "HSE Dublin and Midlands",
    "MRH Portlaoise":                           "HSE Dublin and Midlands",
    "MRH Tullamore":                            "HSE Dublin and Midlands",
    "Naas General Hospital":                    "HSE Dublin and Midlands",
    "St. James's Hospital":                     "HSE Dublin and Midlands",
    "St. Luke's Radiation Oncology Network":    "HSE Dublin and Midlands",
    "Tallaght University Hospital":             "HSE Dublin and Midlands",

    # HSE Dublin and South East
    "National Rehabilitation Hospital":         "HSE Dublin and South East",
    "St. Columcille's Hospital":                "HSE Dublin and South East",
    "St Luke's General Hospital Kilkenny":      "HSE Dublin and South East",
    "St. Michael's Hospital":                   "HSE Dublin and South East",
    "St. Vincent's University Hospital":        "HSE Dublin and South East",
    "Tipperary University Hospital":            "HSE Dublin and South East",
    "UH Waterford":                             "HSE Dublin and South East",
    "Wexford General Hospital":                 "HSE Dublin and South East",

    # HSE South West
    "Bantry General Hospital":                      "HSE South West",
    "Cork University Hospital":                     "HSE South West",
    "Mallow General Hospital":                      "HSE South West",
    "Mercy University Hospital":                    "HSE South West",
    "South Infirmary Victoria University Hospital": "HSE South West",
    "UH Kerry":                                     "HSE South West",

    # HSE Mid West
    "Ennis Hospital":                               "HSE Mid West",
    "Nenagh Hospital":                              "HSE Mid West",
    "St. John's Hospital Limerick":                 "HSE Mid West",
    "UH Limerick":                                  "HSE Mid West",

    # HSE West and North West
    "Galway University Hospital":                   "HSE West and North West",
    "Letterkenny University Hospital":              "HSE West and North West",
    "Mayo University Hospital":                     "HSE West and North West",
    "Portiuncula University Hospital":              "HSE West and North West",
    "Roscommon University Hospital":                "HSE West and North West",
    "Sligo University Hospital":                    "HSE West and North West",
}

# Hospital -> (lat, lon) from HSE GeoHive open data
# https://opendata.arcgis.com/api/v3/datasets/feb34881088341bbbf80d86af6a4f333_0
HOSPITAL_COORDS = {
    "Beaumont Hospital":                        (53.3921, -6.2257),
    "Cavan General Hospital":                   (54.0018, -7.3722),
    "Connolly Hospital":                        (53.3886, -6.3681),
    "Louth County Hospital":                    (53.9886, -6.3990),
    "Mater Misericordiae University Hospital":  (53.3594, -6.2682),
    "National Orthopaedic Hospital Cappagh":    (53.3944, -6.3277),
    "Our Lady of Lourdes Hospital":             (53.7227, -6.3549),
    "Our Lady's Hospital Navan":                (53.6503, -6.6971),
    "CHI at Crumlin":                           (53.3260, -6.3186),
    "CHI at Tallaght":                          (53.2906, -6.3783),
    "CHI at Temple Street":                     (53.3569, -6.2620),
    "MRH Mullingar":                            (53.5342, -7.3491),
    "MRH Portlaoise":                           (53.0380, -7.2760),
    "MRH Tullamore":                            (53.2822, -7.4910),
    "Naas General Hospital":                    (53.2115, -6.6616),
    "St. James's Hospital":                     (53.3392, -6.2966),
    "St. Luke's Radiation Oncology Network":    (53.3102, -6.2675),
    "Tallaght University Hospital":             (53.2906, -6.3783),
    "National Rehabilitation Hospital":         (53.2758, -6.1526),
    "St. Columcille's Hospital":                (53.2428, -6.1324),
    "St Luke's General Hospital Kilkenny":      (52.6660, -7.2628),
    "St. Michael's Hospital":                   (53.2938, -6.1385),
    "St. Vincent's University Hospital":        (53.3166, -6.2132),
    "Tipperary University Hospital":            (52.3555, -7.7143),
    "UH Waterford":                             (52.2486, -7.0785),
    "Wexford General Hospital":                 (52.3428, -6.4824),
    "Bantry General Hospital":                  (51.6760, -9.4497),
    "Cork University Hospital":                 (51.8834, -8.5105),
    "Mallow General Hospital":                  (52.1513, -8.6636),
    "Mercy University Hospital":                (51.8988, -8.4824),
    "South Infirmary Victoria University Hospital": (51.8936, -8.4638),
    "UH Kerry":                                 (52.2654, -9.6892),
    "Ennis Hospital":                           (52.8511, -8.9832),
    "Nenagh Hospital":                          (52.8577, -8.1912),
    "St. John's Hospital Limerick":             (52.6630, -8.6171),
    "UH Limerick":                              (52.6359, -8.6533),
    "Galway University Hospital":               (53.2759, -9.0650),
    "Letterkenny University Hospital":          (54.9600, -7.7343),
    "Mayo University Hospital":                 (53.8520, -9.3034),
    "Portiuncula University Hospital":          (53.3266, -8.2346),
    "Roscommon University Hospital":            (53.6248, -8.1751),
    "Sligo University Hospital":                (54.2742, -8.4634),
}

# Region -> Population (from data/encatchment_areas.csv)
REGION_POPULATIONS = {
    "HSE Dublin and North East": 1187082,
    "HSE Dublin and Midlands":   1077639,
    "HSE Dublin and South East": 971093,
    "HSE South West":            740614,
    "HSE Mid West":              413059,
    "HSE West and North West":   759652,
}
