"""
Configuration for the HSE TrolleyGAR daily ingestion pipeline.
"""

DB_NAME = "hse_trolleygar"
DB_USER = ""  # empty = use system user (default for brew PostgreSQL)
DB_PASSWORD = ""
DB_HOST = "localhost"
DB_PORT = 5432

def get_connection_string(dbname=None):
    """Build a PostgreSQL connection string."""
    dbname = dbname or DB_NAME
    parts = [f"dbname={dbname}", f"host={DB_HOST}", f"port={DB_PORT}"]
    if DB_USER:
        parts.append(f"user={DB_USER}")
    if DB_PASSWORD:
        parts.append(f"password={DB_PASSWORD}")
    return " ".join(parts)


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

# Region -> Population (from data/encatchment_areas.csv)
REGION_POPULATIONS = {
    "HSE Dublin and North East": 1187082,
    "HSE Dublin and Midlands":   1077639,
    "HSE Dublin and South East": 971093,
    "HSE South West":            740614,
    "HSE Mid West":              413059,
    "HSE West and North West":   759652,
}
