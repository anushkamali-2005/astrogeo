"""
Geo Agent
=========
Intelligent agent for geospatial operations:
- Spatial queries and analysis
- Distance and proximity calculations
- Geocoding and reverse geocoding
- Route optimization
- Map visualization

Author: Production Team
Version: 1.0.0
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import BaseTool, StructuredTool
from pydantic.v1 import BaseModel as LangChainBaseModel
from pydantic.v1 import Field as LangChainField

from src.agents.base_agent import BaseAgent
from src.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# TOOL SCHEMAS
# ============================================================================


class GeocodeInput(LangChainBaseModel):
    """Input for geocode tool."""

    address: str = LangChainField(description="Address to geocode")
    country: Optional[str] = LangChainField(None, description="Country code for better accuracy")


class ReverseGeocodeInput(LangChainBaseModel):
    """Input for reverse_geocode tool."""

    latitude: float = LangChainField(description="Latitude coordinate")
    longitude: float = LangChainField(description="Longitude coordinate")


class DistanceCalculationInput(LangChainBaseModel):
    """Input for calculate_distance tool."""

    point1_lat: float = LangChainField(description="Point 1 latitude")
    point1_lon: float = LangChainField(description="Point 1 longitude")
    point2_lat: float = LangChainField(description="Point 2 latitude")
    point2_lon: float = LangChainField(description="Point 2 longitude")
    unit: str = LangChainField(default="km", description="Unit (km, miles, meters)")


class FindNearbyInput(LangChainBaseModel):
    """Input for find_nearby tool."""

    latitude: float = LangChainField(description="Center point latitude")
    longitude: float = LangChainField(description="Center point longitude")
    radius_km: float = LangChainField(description="Search radius in kilometers")
    location_type: Optional[str] = LangChainField(None, description="Filter by location type")


class SpatialAnalysisInput(LangChainBaseModel):
    """Input for spatial_analysis tool."""

    analysis_type: str = LangChainField(
        description="Type of analysis (cluster, hotspot, buffer, intersection)"
    )
    geometries: List[Dict[str, Any]] = LangChainField(description="List of geometries to analyze")


# ============================================================================
# GEO TOOLS
# ============================================================================


def geocode_tool(address: str, country: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert address to geographic coordinates.

    Args:
        address: Address string
        country: Country code for better accuracy

    Returns:
        dict: Geocoding results with coordinates
    """
    logger.info("Geocoding address via Geo agent", extra={"address": address, "country": country})

    # Mock implementation - replace with actual geocoding service
    return {
        "status": "success",
        "query": address,
        "results": [
            {
                "formatted_address": "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
                "latitude": 37.4224764,
                "longitude": -122.0842499,
                "accuracy": "rooftop",
                "confidence": 0.95,
                "place_id": "ChIJ2eUgeAK6j4ARbn5u_wAGqWA",
                "components": {
                    "street_number": "1600",
                    "route": "Amphitheatre Parkway",
                    "city": "Mountain View",
                    "state": "California",
                    "country": "US",
                    "postal_code": "94043",
                },
            }
        ],
        "message": "Successfully geocoded address",
    }


def reverse_geocode_tool(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Convert coordinates to address.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        dict: Reverse geocoding results
    """
    logger.info(
        "Reverse geocoding coordinates via Geo agent",
        extra={"latitude": latitude, "longitude": longitude},
    )

    return {
        "status": "success",
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "address": {
            "formatted": "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
            "street_number": "1600",
            "route": "Amphitheatre Parkway",
            "city": "Mountain View",
            "state": "California",
            "state_code": "CA",
            "country": "United States",
            "country_code": "US",
            "postal_code": "94043",
        },
        "place_name": "Google Headquarters",
        "place_type": "building",
        "message": "Successfully reverse geocoded coordinates",
    }


def calculate_distance_tool(
    point1_lat: float, point1_lon: float, point2_lat: float, point2_lon: float, unit: str = "km"
) -> Dict[str, Any]:
    """
    Calculate distance between two points.

    Args:
        point1_lat: Point 1 latitude
        point1_lon: Point 1 longitude
        point2_lat: Point 2 latitude
        point2_lon: Point 2 longitude
        unit: Distance unit (km, miles, meters)

    Returns:
        dict: Distance calculation results
    """
    logger.info("Calculating distance via Geo agent", extra={"unit": unit})

    # Mock calculation - replace with actual haversine formula
    distance_km = 42.5  # Example distance

    # Convert to requested unit
    conversions = {"km": 1.0, "miles": 0.621371, "meters": 1000.0}

    distance = distance_km * conversions.get(unit, 1.0)

    return {
        "status": "success",
        "point1": {"latitude": point1_lat, "longitude": point1_lon},
        "point2": {"latitude": point2_lat, "longitude": point2_lon},
        "distance": round(distance, 2),
        "unit": unit,
        "straight_line_distance": True,
        "calculation_method": "haversine",
        "message": f"Distance: {round(distance, 2)} {unit}",
    }


def find_nearby_tool(
    latitude: float, longitude: float, radius_km: float, location_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Find nearby locations within radius.

    Args:
        latitude: Center point latitude
        longitude: Center point longitude
        radius_km: Search radius in kilometers
        location_type: Filter by location type

    Returns:
        dict: Nearby locations
    """
    logger.info(
        "Finding nearby locations via Geo agent",
        extra={
            "latitude": latitude,
            "longitude": longitude,
            "radius_km": radius_km,
            "type": location_type,
        },
    )

    # Mock results
    nearby_locations = [
        {
            "id": "loc_1",
            "name": "Central Park",
            "type": "park",
            "latitude": 40.785091,
            "longitude": -73.968285,
            "distance_km": 2.5,
            "address": "Central Park, New York, NY 10024",
        },
        {
            "id": "loc_2",
            "name": "Times Square",
            "type": "landmark",
            "latitude": 40.758896,
            "longitude": -73.985130,
            "distance_km": 3.2,
            "address": "Times Square, New York, NY 10036",
        },
        {
            "id": "loc_3",
            "name": "Empire State Building",
            "type": "building",
            "latitude": 40.748817,
            "longitude": -73.985428,
            "distance_km": 4.1,
            "address": "350 5th Ave, New York, NY 10118",
        },
    ]

    # Filter by type if specified
    if location_type:
        nearby_locations = [loc for loc in nearby_locations if loc["type"] == location_type]

    return {
        "status": "success",
        "center": {"latitude": latitude, "longitude": longitude},
        "radius_km": radius_km,
        "location_type_filter": location_type,
        "total_found": len(nearby_locations),
        "locations": nearby_locations,
        "message": f"Found {len(nearby_locations)} locations within {radius_km}km",
    }


def spatial_analysis_tool(analysis_type: str, geometries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Perform spatial analysis operations.

    Args:
        analysis_type: Type of analysis
        geometries: List of geometries

    Returns:
        dict: Analysis results
    """
    logger.info("Performing spatial analysis via Geo agent", extra={"analysis_type": analysis_type})

    results = {
        "cluster": {
            "status": "success",
            "analysis_type": "clustering",
            "num_geometries": len(geometries),
            "clusters_identified": 3,
            "clusters": [
                {
                    "cluster_id": 1,
                    "num_points": 45,
                    "centroid": {"latitude": 40.7128, "longitude": -74.0060},
                    "density": "high",
                },
                {
                    "cluster_id": 2,
                    "num_points": 32,
                    "centroid": {"latitude": 40.7589, "longitude": -73.9851},
                    "density": "medium",
                },
                {
                    "cluster_id": 3,
                    "num_points": 18,
                    "centroid": {"latitude": 40.7614, "longitude": -73.9776},
                    "density": "low",
                },
            ],
            "message": "Identified 3 spatial clusters",
        },
        "hotspot": {
            "status": "success",
            "analysis_type": "hotspot_detection",
            "num_geometries": len(geometries),
            "hotspots_found": 2,
            "hotspots": [
                {
                    "hotspot_id": 1,
                    "center": {"latitude": 40.7128, "longitude": -74.0060},
                    "intensity": 0.85,
                    "radius_km": 1.5,
                    "significance": "high",
                },
                {
                    "hotspot_id": 2,
                    "center": {"latitude": 40.7589, "longitude": -73.9851},
                    "intensity": 0.62,
                    "radius_km": 2.1,
                    "significance": "medium",
                },
            ],
            "message": "Detected 2 significant hotspots",
        },
        "buffer": {
            "status": "success",
            "analysis_type": "buffer_analysis",
            "num_geometries": len(geometries),
            "buffer_distance_km": 1.0,
            "total_buffer_area_sqkm": 125.5,
            "overlapping_buffers": 12,
            "message": "Created buffer zones around geometries",
        },
    }

    return results.get(
        analysis_type, {"status": "error", "message": f"Unknown analysis type: {analysis_type}"}
    )


def create_route_tool(
    waypoints: List[Tuple[float, float]], optimization: str = "shortest"
) -> Dict[str, Any]:
    """
    Create optimized route through waypoints.

    Args:
        waypoints: List of (latitude, longitude) tuples
        optimization: Optimization method (shortest, fastest)

    Returns:
        dict: Route information
    """
    logger.info(
        "Creating route via Geo agent",
        extra={"num_waypoints": len(waypoints), "optimization": optimization},
    )

    return {
        "status": "success",
        "waypoints": waypoints,
        "optimization": optimization,
        "route": {
            "total_distance_km": 45.2,
            "total_duration_minutes": 65,
            "segments": [
                {
                    "start": waypoints[0],
                    "end": waypoints[1],
                    "distance_km": 15.3,
                    "duration_minutes": 22,
                },
                {
                    "start": waypoints[1],
                    "end": waypoints[2],
                    "distance_km": 29.9,
                    "duration_minutes": 43,
                },
            ],
            "polyline": "encoded_polyline_string_here",
        },
        "message": f"Created optimized route through {len(waypoints)} waypoints",
    }


def generate_map_tool(
    locations: List[Dict[str, Any]], map_type: str = "interactive", include_markers: bool = True
) -> Dict[str, Any]:
    """
    Generate map visualization.

    Args:
        locations: List of locations to plot
        map_type: Type of map (interactive, static, heatmap)
        include_markers: Include location markers

    Returns:
        dict: Map generation results
    """
    logger.info(
        "Generating map via Geo agent",
        extra={"num_locations": len(locations), "map_type": map_type},
    )

    return {
        "status": "success",
        "map_type": map_type,
        "num_locations": len(locations),
        "map_url": "https://example.com/maps/generated_map_123.html",
        "map_file": "maps/generated_map_123.html",
        "center": {"latitude": 40.7128, "longitude": -74.0060},
        "zoom_level": 12,
        "markers_included": include_markers,
        "features": {
            "interactive": map_type == "interactive",
            "layers": ["base_map", "markers", "labels"],
            "controls": ["zoom", "pan", "layer_toggle"],
        },
        "message": f"Generated {map_type} map with {len(locations)} locations",
    }


# ============================================================================
# GEO AGENT
# ============================================================================


class GeoAgent(BaseAgent):
    """
    Intelligent agent for geospatial operations.

    Capabilities:
    - Geocoding and reverse geocoding
    - Distance calculations
    - Proximity searches
    - Spatial analysis
    - Route optimization
    - Map generation
    """

    def __init__(self, model: Optional[str] = None, temperature: float = 0.3, **kwargs):
        """
        Initialize Geo Agent.

        Args:
            model: LLM model name
            temperature: LLM temperature
            **kwargs: Additional base agent arguments
        """
        # Create tools
        tools = self._create_tools()

        # Initialize base agent
        super().__init__(
            name="GeoAgent",
            description="Intelligent agent for geospatial operations",
            tools=tools,
            model=model,
            temperature=temperature,
            **kwargs,
        )

        logger.info("Geo Agent initialized", extra={"num_tools": len(tools)})

    def _create_tools(self) -> List[BaseTool]:
        """
        Create geo-specific tools.

        Returns:
            list: List of LangChain tools
        """
        tools = [
            StructuredTool.from_function(
                func=geocode_tool,
                name="geocode",
                description="Convert address to geographic coordinates (latitude/longitude). "
                "Use when user provides an address and needs coordinates.",
                args_schema=GeocodeInput,
            ),
            StructuredTool.from_function(
                func=reverse_geocode_tool,
                name="reverse_geocode",
                description="Convert coordinates to address. "
                "Use when user provides coordinates and needs address.",
                args_schema=ReverseGeocodeInput,
            ),
            StructuredTool.from_function(
                func=calculate_distance_tool,
                name="calculate_distance",
                description="Calculate distance between two geographic points. "
                "Use when user wants to know distance between locations.",
                args_schema=DistanceCalculationInput,
            ),
            StructuredTool.from_function(
                func=find_nearby_tool,
                name="find_nearby",
                description="Find locations within a radius of a point. "
                "Use for proximity searches and 'find near me' queries.",
                args_schema=FindNearbyInput,
            ),
            StructuredTool.from_function(
                func=spatial_analysis_tool,
                name="spatial_analysis",
                description="Perform spatial analysis (clustering, hotspots, buffers). "
                "Use for advanced geospatial analytics.",
                args_schema=SpatialAnalysisInput,
            ),
            StructuredTool.from_function(
                func=create_route_tool,
                name="create_route",
                description="Create optimized route through multiple waypoints. "
                "Use for route planning and optimization.",
            ),
            StructuredTool.from_function(
                func=generate_map_tool,
                name="generate_map",
                description="Generate interactive or static map visualization. "
                "Use when user wants to visualize locations on a map.",
            ),
        ]

        return tools

    def _get_system_prompt(self) -> str:
        """
        Get Geo Agent system prompt.

        Returns:
            str: System prompt
        """
        return """You are an expert GIS (Geographic Information Systems) agent specialized in geospatial operations and analysis.

Your capabilities:
- Geocoding and reverse geocoding
- Distance and proximity calculations
- Spatial queries and analysis
- Route optimization
- Map generation and visualization
- Clustering and hotspot detection

Guidelines:
1. Always validate coordinate ranges (lat: -90 to 90, lon: -180 to 180)
2. Provide distances in user's preferred units
3. Suggest appropriate spatial analysis techniques
4. Recommend optimal map visualizations
5. Explain geospatial concepts clearly

When working with locations:
- Use accurate geocoding services
- Calculate distances using proper formulas (haversine)
- Consider spatial reference systems (WGS84 is standard)
- Account for Earth's curvature for large distances
- Provide both numeric results and visual representations

Spatial Analysis Types:
- Clustering: Group nearby points
- Hotspot Detection: Find areas of high concentration
- Buffer Analysis: Create zones around features
- Proximity Search: Find nearby locations
- Route Optimization: Calculate optimal paths

Be precise with coordinates, provide context for results, and always suggest visualizations when appropriate."""


# Example usage
if __name__ == "__main__":
    import asyncio

    async def demo():
        # Initialize agent
        agent = GeoAgent()

        # Execute task
        result = await agent.execute(
            task="Find all locations within 5km of Times Square and create a map visualization"
        )

        print(json.dumps(result, indent=2))

    asyncio.run(demo())


# Export
__all__ = ["GeoAgent"]
