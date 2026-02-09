"""
Astronomical Agent
==================
Intelligent agent for astronomical data operations:
- Celestial object tracking
- Astronomical calculations
- Star catalog queries
- Orbit calculations
- Light curve analysis
- Coordinate transformations

Author: Production Team
Version: 1.0.0
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic.v1 import BaseModel as LangChainBaseModel
from pydantic.v1 import Field as LangChainField

from src.agents.base_agent import BaseAgent
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# CONSTANTS (from configuration - avoiding hardcoding)
# ============================================================================

# Astronomical constants (can be moved to settings if needed)
SPEED_OF_LIGHT_KM_S = 299792.458  # km/s
AU_TO_KM = 149597870.7  # Astronomical Unit in km
PARSEC_TO_LY = 3.26156  # Parsecs to Light Years


# ============================================================================
# TOOL SCHEMAS
# ============================================================================


class CelestialTrackInput(LangChainBaseModel):
    """Input for celestial object tracking tool."""

    object_name: str = LangChainField(
        description="Name of celestial object (e.g., 'Mars', 'Sirius', 'M31')"
    )
    observation_time: Optional[str] = LangChainField(
        default=None, description="ISO format datetime (if None, uses current time)"
    )
    observer_lat: float = LangChainField(description="Observer latitude in degrees")
    observer_lon: float = LangChainField(description="Observer longitude in degrees")


class AstroCalculationInput(LangChainBaseModel):
    """Input for astronomical calculations tool."""

    calculation_type: str = LangChainField(
        description="Type of calculation (distance, magnitude, angular_separation, parallax)"
    )
    parameters: Dict[str, Any] = LangChainField(
        description="Calculation parameters (varies by type)"
    )


class StarCatalogQueryInput(LangChainBaseModel):
    """Input for star catalog query tool."""

    catalog: str = LangChainField(
        default="hipparcos", description="Catalog name (hipparcos, tycho, gaia)"
    )
    ra_center: float = LangChainField(description="Right Ascension center (degrees)")
    dec_center: float = LangChainField(description="Declination center (degrees)")
    radius: float = LangChainField(description="Search radius (degrees)")
    max_results: int = LangChainField(default=100, description="Maximum results to return")


class OrbitCalculationInput(LangChainBaseModel):
    """Input for orbit calculation tool."""

    orbit_type: str = LangChainField(
        description="Orbit type (elliptical, circular, parabolic, hyperbolic)"
    )
    semi_major_axis: float = LangChainField(description="Semi-major axis (AU)")
    eccentricity: float = LangChainField(description="Orbital eccentricity")
    inclination: float = LangChainField(description="Orbital inclination (degrees)")
    time_since_perihelion: Optional[float] = LangChainField(
        default=0.0, description="Time since perihelion (days)"
    )


class LightCurveAnalysisInput(LangChainBaseModel):
    """Input for light curve analysis tool."""

    object_name: str = LangChainField(description="Name of variable object")
    time_series: List[Dict[str, Any]] = LangChainField(
        description="List of {time, magnitude} observations"
    )
    analysis_type: str = LangChainField(
        default="period_detection",
        description="Analysis type (period_detection, classification, variability)",
    )


class CoordinateTransformInput(LangChainBaseModel):
    """Input for coordinate transformation tool."""

    ra: float = LangChainField(description="Right Ascension (degrees)")
    dec: float = LangChainField(description="Declination (degrees)")
    from_frame: str = LangChainField(
        default="icrs", description="Source coordinate frame (icrs, galactic, fk5, altaz)"
    )
    to_frame: str = LangChainField(
        description="Target coordinate frame (icrs, galactic, fk5, altaz)"
    )
    observation_time: Optional[str] = LangChainField(
        default=None, description="Observation time (ISO format, for time-dependent frames)"
    )


# ============================================================================
# ASTRONOMICAL TOOLS
# ============================================================================


def track_celestial_object_tool(
    object_name: str, observation_time: Optional[str], observer_lat: float, observer_lon: float
) -> Dict[str, Any]:
    """
    Track position of celestial object.

    Args:
        object_name: Name of celestial object
        observation_time: Observation time (ISO format)
        observer_lat: Observer latitude
        observer_lon: Observer longitude

    Returns:
        dict: Object position and visibility information
    """
    logger.info(
        "Tracking celestial object via Astro agent",
        extra={"object": object_name, "observer_location": f"({observer_lat}, {observer_lon})"},
    )

    # Mock implementation - replace with astropy ephemerides
    # In production, use astropy.coordinates.get_body() or JPL Horizons
    obs_time = observation_time or datetime.utcnow().isoformat()

    return {
        "status": "success",
        "object_name": object_name,
        "observation_time": obs_time,
        "observer_location": {"latitude": observer_lat, "longitude": observer_lon},
        "position": {
            "right_ascension": {"degrees": 83.8221, "hours": "05h 35m 17.3s"},
            "declination": {"degrees": -5.3911, "dms": "-05° 23' 28.0\""},
            "altitude": 45.2,  # degrees above horizon
            "azimuth": 180.5,  # degrees from North
            "distance_au": 1.52,  # Astronomical Units
            "distance_km": 227_000_000,
            "apparent_magnitude": -1.5,
        },
        "visibility": {
            "is_visible": True,
            "is_above_horizon": True,
            "twilight_condition": "astronomical_twilight",
            "best_observation_time": "22:30 UTC",
            "constellation": "Orion",
        },
        "ephemeris": {
            "rise_time": "18:45 UTC",
            "transit_time": "22:30 UTC",
            "set_time": "02:15 UTC",
        },
        "message": f"Successfully tracked {object_name}",
    }


def astronomical_calculation_tool(
    calculation_type: str, parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform astronomical calculations.

    Args:
        calculation_type: Type of calculation
        parameters: Calculation parameters

    Returns:
        dict: Calculation results
    """
    logger.info(
        "Performing astronomical calculation via Astro agent", extra={"type": calculation_type}
    )

    # Distance calculation
    if calculation_type == "distance":
        # In production: use astropy.coordinates.Distance or cosmological calculations
        distance_ly = parameters.get("distance_ly", 4.37)  # Light years
        distance_parsecs = distance_ly / PARSEC_TO_LY

        return {
            "status": "success",
            "calculation_type": "distance",
            "results": {
                "distance_light_years": distance_ly,
                "distance_parsecs": round(distance_parsecs, 4),
                "distance_km": distance_ly * 9.461e12,
                "distance_au": distance_ly * 63241.1,
                "light_travel_time_years": distance_ly,
            },
            "message": f"Distance: {distance_ly} light-years",
        }

    # Magnitude calculation
    elif calculation_type == "magnitude":
        apparent_mag = parameters.get("apparent_magnitude", 1.0)
        distance_pc = parameters.get("distance_parsecs", 10.0)

        # Absolute magnitude formula: M = m - 5(log10(d) - 1)
        import math

        absolute_mag = apparent_mag - 5 * (math.log10(distance_pc) - 1)

        return {
            "status": "success",
            "calculation_type": "magnitude",
            "results": {
                "apparent_magnitude": apparent_mag,
                "absolute_magnitude": round(absolute_mag, 2),
                "distance_parsecs": distance_pc,
                "luminosity_ratio_to_sun": 10 ** ((4.83 - absolute_mag) / 2.5),
            },
            "message": "Magnitude calculation completed",
        }

    # Angular separation
    elif calculation_type == "angular_separation":
        ra1 = parameters.get("ra1", 0.0)
        dec1 = parameters.get("dec1", 0.0)
        ra2 = parameters.get("ra2", 10.0)
        dec2 = parameters.get("dec2", 10.0)

        # Mock calculation - use astropy.coordinates for accurate results
        separation_deg = 14.14  # Example

        return {
            "status": "success",
            "calculation_type": "angular_separation",
            "results": {
                "object1_coords": {"ra": ra1, "dec": dec1},
                "object2_coords": {"ra": ra2, "dec": dec2},
                "separation_degrees": separation_deg,
                "separation_arcminutes": separation_deg * 60,
                "separation_arcseconds": separation_deg * 3600,
            },
            "message": f"Angular separation: {separation_deg}°",
        }

    # Parallax calculation
    elif calculation_type == "parallax":
        parallax_mas = parameters.get("parallax_milliarcsec", 100.0)
        distance_parsecs = 1000.0 / parallax_mas  # Distance in parsecs

        return {
            "status": "success",
            "calculation_type": "parallax",
            "results": {
                "parallax_milliarcseconds": parallax_mas,
                "distance_parsecs": round(distance_parsecs, 2),
                "distance_light_years": round(distance_parsecs * PARSEC_TO_LY, 2),
                "error_estimate": "+/- 0.5 parsecs",
            },
            "message": "Parallax-based distance calculated",
        }

    return {"status": "error", "message": f"Unknown calculation type: {calculation_type}"}


def query_star_catalog_tool(
    catalog: str, ra_center: float, dec_center: float, radius: float, max_results: int = 100
) -> Dict[str, Any]:
    """
    Query astronomical star catalogs.

    Args:
        catalog: Catalog name
        ra_center: Right Ascension center
        dec_center: Declination center
        radius: Search radius
        max_results: Maximum results

    Returns:
        dict: Catalog query results
    """
    logger.info(
        "Querying star catalog via Astro agent",
        extra={"catalog": catalog, "center": f"RA={ra_center}, Dec={dec_center}", "radius": radius},
    )

    # Mock results - replace with actual catalog query
    # In production: use astroquery.vizier or astroquery.gaia
    stars = [
        {
            "star_id": "HIP_12345",
            "name": "Betelgeuse",
            "ra_degrees": 88.7929,
            "dec_degrees": 7.4070,
            "magnitude": 0.50,
            "spectral_type": "M1-2Ia",
            "parallax_mas": 5.95,
            "distance_ly": 548,
            "proper_motion_ra": 27.33,  # mas/yr
            "proper_motion_dec": 10.86,  # mas/yr
            "radial_velocity_km_s": 21.0,
            "color_index_bv": 1.85,
        },
        {
            "star_id": "HIP_67890",
            "name": "Rigel",
            "ra_degrees": 78.6344,
            "dec_degrees": -8.2016,
            "magnitude": 0.13,
            "spectral_type": "B8Ia",
            "parallax_mas": 4.22,
            "distance_ly": 773,
            "proper_motion_ra": 1.87,
            "proper_motion_dec": 0.56,
            "radial_velocity_km_s": 17.8,
            "color_index_bv": -0.03,
        },
    ]

    # Filter by radius (mock filtering)
    filtered_stars = stars[: min(len(stars), max_results)]

    return {
        "status": "success",
        "catalog": catalog.upper(),
        "query_parameters": {
            "ra_center": ra_center,
            "dec_center": dec_center,
            "radius_degrees": radius,
            "max_results": max_results,
        },
        "total_found": len(filtered_stars),
        "stars": filtered_stars,
        "metadata": {"catalog_version": "2023.1", "epoch": "J2000.0", "coordinate_frame": "ICRS"},
        "message": f"Found {len(filtered_stars)} stars in {catalog} catalog",
    }


def calculate_orbit_tool(
    orbit_type: str,
    semi_major_axis: float,
    eccentricity: float,
    inclination: float,
    time_since_perihelion: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate orbital elements and predict positions.

    Args:
        orbit_type: Type of orbit
        semi_major_axis: Semi-major axis (AU)
        eccentricity: Eccentricity
        inclination: Inclination (degrees)
        time_since_perihelion: Time since perihelion (days)

    Returns:
        dict: Orbital calculations
    """
    logger.info(
        "Calculating orbit via Astro agent",
        extra={"orbit_type": orbit_type, "a": semi_major_axis, "e": eccentricity},
    )

    # Mock orbital calculations - use astropy or poliastro for production
    import math

    # Kepler's Third Law: P^2 = a^3 (for solar system)
    orbital_period_years = semi_major_axis**1.5
    orbital_period_days = orbital_period_years * 365.25

    # Perihelion and aphelion distances
    perihelion_au = semi_major_axis * (1 - eccentricity)
    aphelion_au = semi_major_axis * (1 + eccentricity)

    # Current position (simplified - use Kepler's equation for accuracy)
    mean_anomaly = (time_since_perihelion / orbital_period_days) * 360  # degrees

    return {
        "status": "success",
        "orbit_type": orbit_type,
        "orbital_elements": {
            "semi_major_axis_au": semi_major_axis,
            "eccentricity": eccentricity,
            "inclination_degrees": inclination,
            "perihelion_distance_au": round(perihelion_au, 4),
            "aphelion_distance_au": round(aphelion_au, 4),
            "orbital_period_days": round(orbital_period_days, 2),
            "orbital_period_years": round(orbital_period_years, 2),
        },
        "current_position": {
            "time_since_perihelion_days": time_since_perihelion,
            "mean_anomaly_degrees": round(mean_anomaly % 360, 2),
            "estimated_distance_au": round(perihelion_au + 0.5 * (aphelion_au - perihelion_au), 3),
            "orbital_velocity_km_s": 29.78 * math.sqrt(2 / semi_major_axis - 1 / semi_major_axis),
        },
        "characteristics": {
            "is_closed_orbit": eccentricity < 1.0,
            "orbit_shape": "elliptical" if eccentricity < 1.0 else "hyperbolic",
            "energy": "negative" if eccentricity < 1.0 else "positive",
        },
        "message": f"Orbital calculations completed for {orbit_type} orbit",
    }


def analyze_light_curve_tool(
    object_name: str, time_series: List[Dict[str, Any]], analysis_type: str = "period_detection"
) -> Dict[str, Any]:
    """
    Analyze light curves for variability and periodicity.

    Args:
        object_name: Name of object
        time_series: Time series data [{time, magnitude}]
        analysis_type: Type of analysis

    Returns:
        dict: Light curve analysis results
    """
    logger.info(
        "Analyzing light curve via Astro agent",
        extra={
            "object": object_name,
            "num_observations": len(time_series),
            "analysis": analysis_type,
        },
    )

    # Mock analysis - use scipy.signal or astropy.timeseries for production
    num_points = len(time_series)

    if analysis_type == "period_detection":
        return {
            "status": "success",
            "object_name": object_name,
            "analysis_type": "period_detection",
            "num_observations": num_points,
            "detected_periods": [
                {
                    "period_days": 5.37,
                    "amplitude_mag": 0.15,
                    "confidence": 0.92,
                    "significance": "high",
                },
                {
                    "period_days": 10.74,  # Harmonic
                    "amplitude_mag": 0.08,
                    "confidence": 0.75,
                    "significance": "medium",
                },
            ],
            "primary_period": 5.37,
            "variability_type": "periodic",
            "fourier_analysis": {
                "fundamental_frequency": 0.186,  # cycles/day
                "harmonics_detected": 2,
            },
            "message": f"Detected primary period of 5.37 days for {object_name}",
        }

    elif analysis_type == "classification":
        return {
            "status": "success",
            "object_name": object_name,
            "analysis_type": "classification",
            "classification": {
                "variable_type": "Cepheid",
                "subtype": "Classical Cepheid",
                "confidence": 0.88,
                "alternative_types": ["RR Lyrae", "Delta Scuti"],
            },
            "characteristics": {
                "period_days": 5.37,
                "amplitude_mag": 0.15,
                "light_curve_shape": "asymmetric_sawtooth",
                "color_variation": "present",
            },
            "message": f"{object_name} classified as Classical Cepheid variable",
        }

    elif analysis_type == "variability":
        import math

        # Calculate simple statistics
        magnitudes = [obs.get("magnitude", 0) for obs in time_series]
        mean_mag = sum(magnitudes) / len(magnitudes) if magnitudes else 0
        variance = (
            sum((m - mean_mag) ** 2 for m in magnitudes) / len(magnitudes) if magnitudes else 0
        )
        std_dev = math.sqrt(variance)

        return {
            "status": "success",
            "object_name": object_name,
            "analysis_type": "variability",
            "statistics": {
                "mean_magnitude": round(mean_mag, 3),
                "std_deviation": round(std_dev, 3),
                "min_magnitude": min(magnitudes) if magnitudes else 0,
                "max_magnitude": max(magnitudes) if magnitudes else 0,
                "amplitude": round(max(magnitudes) - min(magnitudes), 3) if magnitudes else 0,
            },
            "variability_index": round(std_dev / mean_mag * 100, 2) if mean_mag > 0 else 0,
            "is_variable": std_dev > 0.05,
            "variability_classification": (
                "highly_variable"
                if std_dev > 0.2
                else "moderately_variable" if std_dev > 0.05 else "stable"
            ),
            "message": f"Variability analysis completed for {object_name}",
        }

    return {"status": "error", "message": f"Unknown analysis type: {analysis_type}"}


def transform_coordinates_tool(
    ra: float, dec: float, from_frame: str, to_frame: str, observation_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transform astronomical coordinates between reference frames.

    Args:
        ra: Right Ascension (degrees)
        dec: Declination (degrees)
        from_frame: Source coordinate frame
        to_frame: Target coordinate frame
        observation_time: Observation time (ISO format)

    Returns:
        dict: Transformed coordinates
    """
    logger.info(
        "Transforming coordinates via Astro agent",
        extra={"from": from_frame, "to": to_frame, "coords": f"RA={ra}, Dec={dec}"},
    )

    # Mock transformation - use astropy.coordinates for production
    obs_time = observation_time or datetime.utcnow().isoformat()

    # Example transformations (simplified)
    transformations = {
        ("icrs", "galactic"): {"l": 180.0, "b": -60.0},  # Galactic longitude  # Galactic latitude
        ("icrs", "fk5"): {"ra": ra + 0.001, "dec": dec + 0.0005},  # Minimal precession correction
        ("galactic", "icrs"): {"ra": ra + 10.0, "dec": dec - 5.0},
    }

    key = (from_frame.lower(), to_frame.lower())
    transformed = transformations.get(key, {"ra": ra, "dec": dec})

    return {
        "status": "success",
        "input_coordinates": {
            "frame": from_frame,
            "ra_degrees": ra,
            "dec_degrees": dec,
            "observation_time": obs_time,
        },
        "output_coordinates": {"frame": to_frame, **transformed},
        "transformation_info": {
            "method": "matrix_rotation",
            "precession_applied": to_frame in ["fk5", "fk4"],
            "nutation_applied": False,
            "aberration_corrected": False,
            "epoch": "J2000.0",
        },
        "message": f"Coordinates transformed from {from_frame} to {to_frame}",
    }


# ============================================================================
# ASTRONOMICAL AGENT
# ============================================================================


class AstroAgent(BaseAgent):
    """
    Intelligent agent for astronomical data operations.

    Capabilities:
    - Track celestial objects
    - Perform astronomical calculations
    - Query star catalogs
    - Calculate orbits
    - Analyze light curves
    - Transform coordinate systems

    Performance:
    - Time complexity: O(1) for single calculations, O(n) for catalog queries
    - Space complexity: O(1) per operation, O(n) for catalog results
    """

    def __init__(self, model: Optional[str] = None, temperature: float = 0.3, **kwargs):
        """
        Initialize Astronomical Agent.

        Args:
            model: LLM model name
            temperature: LLM temperature (lower for precise calculations)
            **kwargs: Additional base agent arguments
        """
        # Create tools
        tools = self._create_tools()

        # Initialize base agent
        super().__init__(
            name="AstroAgent",
            description="Intelligent agent for astronomical data operations and calculations",
            tools=tools,
            model=model,
            temperature=temperature,
            **kwargs,
        )

        logger.info("Astronomical Agent initialized", extra={"num_tools": len(tools)})

    def _create_tools(self) -> List[BaseTool]:
        """
        Create astronomy-specific tools.

        Returns:
            list: List of LangChain tools

        Time complexity: O(1)
        Space complexity: O(1)
        """
        tools = [
            StructuredTool.from_function(
                func=track_celestial_object_tool,
                name="track_celestial_object",
                description="Track position and visibility of celestial objects (planets, stars, deep sky objects). "
                "Use when user wants to locate an astronomical object.",
                args_schema=CelestialTrackInput,
            ),
            StructuredTool.from_function(
                func=astronomical_calculation_tool,
                name="astronomical_calculation",
                description="Perform astronomical calculations (distance, magnitude, parallax, angular separation). "
                "Use for precise astrophysical computations.",
                args_schema=AstroCalculationInput,
            ),
            StructuredTool.from_function(
                func=query_star_catalog_tool,
                name="query_star_catalog",
                description="Query astronomical catalogs (Hipparcos, Tycho, Gaia) for star data. "
                "Use when searching for stars in a specific region.",
                args_schema=StarCatalogQueryInput,
            ),
            StructuredTool.from_function(
                func=calculate_orbit_tool,
                name="calculate_orbit",
                description="Calculate orbital elements and predict object positions. "
                "Use for orbital mechanics and solar system object tracking.",
                args_schema=OrbitCalculationInput,
            ),
            StructuredTool.from_function(
                func=analyze_light_curve_tool,
                name="analyze_light_curve",
                description="Analyze brightness variations for period detection and classification. "
                "Use for studying variable stars and periodic phenomena.",
                args_schema=LightCurveAnalysisInput,
            ),
            StructuredTool.from_function(
                func=transform_coordinates_tool,
                name="transform_coordinates",
                description="Transform coordinates between reference frames (ICRS, Galactic, FK5, AltAz). "
                "Use for coordinate system conversions.",
                args_schema=CoordinateTransformInput,
            ),
        ]

        return tools

    def _get_system_prompt(self) -> str:
        """
        Get Astronomical Agent system prompt.

        Returns:
            str: System prompt
        """
        return """You are an expert Astronomer agent specialized in astronomical data operations and calculations.

Your capabilities:
- Track celestial objects (planets, stars, deep-sky objects)
- Perform astronomical calculations (distances, magnitudes, parallax)
- Query astronomical catalogs (Hipparcos, Tycho-2, Gaia)
- Calculate orbital elements and predict positions
- Analyze light curves for variability and periodicity
- Transform between coordinate reference frames

Guidelines:
1. Always validate coordinate ranges (RA: 0-360°, Dec: -90 to +90°)
2. Use appropriate units (AU, light-years, parsecs, magnitudes)
3. Provide context for astronomical calculations
4. Explain observational conditions and visibility
5. Recommend optimal observation times

When performing calculations:
- Use proper astronomical constants and formulas
- Account for coordinate frames (ICRS, Galactic, FK5)
- Consider observational constraints (altitude, twilight)
- Provide error estimates when relevant
- Include both technical and user-friendly explanations

Astronomical Concepts:
- Celestial Coordinates: RA/Dec, Alt/Az, Galactic l/b
- Magnitudes: Apparent vs Absolute
- Distances: AU, light-years, parsecs
- Orbital Elements: a, e, i, Ω, ω, M
- Light Curves: Period, amplitude, phase
- Reference Frames: ICRS, FK5, Galactic

Be precise with calculations, provide observational context, and always cite coordinate frames and epochs."""


# Example usage
if __name__ == "__main__":
    import asyncio

    async def demo():
        # Initialize agent
        agent = AstroAgent()

        # Execute task
        result = await agent.execute(
            task="Track the current position of Mars from New York City and "
            "calculate its distance from Earth in AU and light-years"
        )

        print(json.dumps(result, indent=2))

    asyncio.run(demo())


# Export
__all__ = ["AstroAgent"]
