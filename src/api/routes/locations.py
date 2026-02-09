"""
Location/Geospatial Routes
===========================
Geospatial operations with PostGIS integration:
- CRUD operations for locations
- Spatial queries (nearby, within, intersects)
- GeoJSON support
- Distance calculations

Author: Production Team
Version: 1.0.0
"""

from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from pydantic import BaseModel, Field, validator
from geoalchemy2.functions import ST_AsGeoJSON, ST_DWithin, ST_Distance, ST_MakePoint, ST_SetSRID

from src.core.config import settings
from src.core.logging import get_logger
from src.core.security import get_current_user
from src.core.exceptions import (
    RecordNotFoundError,
    ValidationError,
    DatabaseError
)
from src.database.connection import get_db
from src.database.repositories import LocationRepository
from src.database.models import Location


logger = get_logger(__name__)
router = APIRouter(prefix="/locations", tags=["Locations"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry."""
    type: str = Field(default="Point", description="Geometry type")
    coordinates: List[float] = Field(..., description="[longitude, latitude]")
    
    @validator("coordinates")
    def validate_coordinates(cls, v):
        """Validate coordinates format."""
        if len(v) != 2:
            raise ValueError("Coordinates must be [longitude, latitude]")
        lon, lat = v
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v


class LocationCreateRequest(BaseModel):
    """Location creation request."""
    name: str = Field(..., min_length=1, max_length=255, description="Location name")
    description: str | None = Field(None, description="Location description")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    elevation: float | None = Field(None, description="Elevation in meters")
    country: str | None = Field(None, max_length=100, description="Country")
    region: str | None = Field(None, max_length=100, description="Region/state")
    city: str | None = Field(None, max_length=100, description="City")
    location_type: str | None = Field(None, max_length=50, description="Location type")
    metadata: Dict[str, Any] | None = Field(default_factory=dict, description="Additional metadata")


class LocationUpdateRequest(BaseModel):
    """Location update request."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    elevation: float | None = None
    country: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    city: str | None = Field(None, max_length=100)
    location_type: str | None = Field(None, max_length=50)
    metadata: Dict[str, Any] | None = None


class LocationResponse(BaseModel):
    """Location response with GeoJSON geometry."""
    id: UUID
    name: str
    description: str | None
    latitude: float
    longitude: float
    elevation: float | None
    country: str | None
    region: str | None
    city: str | None
    location_type: str | None
    geometry: Dict[str, Any]  # GeoJSON
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class NearbySearchRequest(BaseModel):
    """Nearby location search request."""
    latitude: float = Field(..., ge=-90, le=90, description="Center latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Center longitude")
    radius_km: float = Field(..., gt=0, le=10000, description="Search radius in kilometers")
    location_type: str | None = Field(None, description="Filter by location type")
    limit: int = Field(default=100, le=1000, description="Maximum results")


class LocationWithDistance(BaseModel):
    """Location with distance information."""
    id: UUID
    name: str
    description: str | None
    latitude: float
    longitude: float
    elevation: float | None
    country: str | None
    region: str | None
    city: str | None
    location_type: str | None
    geometry: Dict[str, Any]
    distance_km: float = Field(..., description="Distance from search point in km")
    metadata: Dict[str, Any]


class BulkCreateRequest(BaseModel):
    """Bulk location creation request."""
    locations: List[LocationCreateRequest] = Field(..., max_items=1000)


class BulkCreateResponse(BaseModel):
    """Bulk creation response."""
    created_count: int
    locations: List[LocationResponse]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def location_to_geojson(location: Location) -> Dict[str, Any]:
    """
    Convert location to GeoJSON format.
    
    Args:
        location: Location model instance
        
    Returns:
        dict: GeoJSON Feature
    """
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [location.longitude, location.latitude]
        },
        "properties": {
            "id": str(location.id),
            "name": location.name,
            "description": location.description,
            "elevation": location.elevation,
            "country": location.country,
            "region": location.region,
            "city": location.city,
            "location_type": location.location_type,
            "metadata": location.metadata or {},
            "created_at": location.created_at.isoformat() if location.created_at else None,
            "updated_at": location.updated_at.isoformat() if location.updated_at else None
        }
    }


# ============================================================================
# CRUD ENDPOINTS
# ============================================================================

@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    data: LocationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> LocationResponse:
    """
    Create new location with geometry.
    
    Args:
        data: Location data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        LocationResponse: Created location
    """
    logger.info(
        "Creating location",
        extra={
            "name": data.name,
            "user_id": str(current_user["id"])
        }
    )
    
    location_repo = LocationRepository(db)
    
    # Create location with spatial data
    location = await location_repo.create(
        name=data.name,
        description=data.description,
        latitude=data.latitude,
        longitude=data.longitude,
        elevation=data.elevation,
        country=data.country,
        region=data.region,
        city=data.city,
        location_type=data.location_type,
        metadata=data.metadata or {},
        user_id=UUID(current_user["id"])
    )
    
    logger.info("Location created", extra={"location_id": str(location.id)})
    
    return LocationResponse(
        id=location.id,
        name=location.name,
        description=location.description,
        latitude=location.latitude,
        longitude=location.longitude,
        elevation=location.elevation,
        country=location.country,
        region=location.region,
        city=location.city,
        location_type=location.location_type,
        geometry={
            "type": "Point",
            "coordinates": [location.longitude, location.latitude]
        },
        metadata=location.metadata or {},
        created_at=location.created_at.isoformat() if location.created_at else "",
        updated_at=location.updated_at.isoformat() if location.updated_at else ""
    )


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> LocationResponse:
    """
    Get location by ID.
    
    Args:
        location_id: Location ID
        db: Database session
        
    Returns:
        LocationResponse: Location details
        
    Raises:
        RecordNotFoundError: If location not found
    """
    location_repo = LocationRepository(db)
    location = await location_repo.get_by_id(location_id)
    
    if not location:
        raise RecordNotFoundError("Location", str(location_id))
    
    return LocationResponse(
        id=location.id,
        name=location.name,
        description=location.description,
        latitude=location.latitude,
        longitude=location.longitude,
        elevation=location.elevation,
        country=location.country,
        region=location.region,
        city=location.city,
        location_type=location.location_type,
        geometry={
            "type": "Point",
            "coordinates": [location.longitude, location.latitude]
        },
        metadata=location.metadata or {},
        created_at=location.created_at.isoformat() if location.created_at else "",
        updated_at=location.updated_at.isoformat() if location.updated_at else ""
    )


@router.get("", response_model=List[LocationResponse])
async def list_locations(
    limit: int = Query(default=100, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Results to skip"),
    country: str | None = Query(default=None, description="Filter by country"),
    location_type: str | None = Query(default=None, description="Filter by type"),
    db: AsyncSession = Depends(get_db)
) -> List[LocationResponse]:
    """
    List locations with pagination and filters.
    
    Args:
        limit: Maximum results
        offset: Results to skip
        country: Filter by country
        location_type: Filter by location type
        db: Database session
        
    Returns:
        list: List of locations
    """
    location_repo = LocationRepository(db)
    
    # Build filters
    filters = {}
    if country:
        locations = await location_repo.get_by_country(country, limit=limit)
    elif location_type:
        locations = await location_repo.get_by_type(location_type, limit=limit)
    else:
        locations = await location_repo.get_all(limit=limit, offset=offset)
    
    return [
        LocationResponse(
            id=loc.id,
            name=loc.name,
            description=loc.description,
            latitude=loc.latitude,
            longitude=loc.longitude,
            elevation=loc.elevation,
            country=loc.country,
            region=loc.region,
            city=loc.city,
            location_type=loc.location_type,
            geometry={
                "type": "Point",
                "coordinates": [loc.longitude, loc.latitude]
            },
            metadata=loc.metadata or {},
            created_at=loc.created_at.isoformat() if loc.created_at else "",
            updated_at=loc.updated_at.isoformat() if loc.updated_at else ""
        )
        for loc in locations
    ]


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: UUID,
    data: LocationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> LocationResponse:
    """
    Update location.
    
    Args:
        location_id: Location ID
        data: Update data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        LocationResponse: Updated location
        
    Raises:
        RecordNotFoundError: If location not found
    """
    location_repo = LocationRepository(db)
    
    # Prepare update data
    update_data = {
        k: v for k, v in data.dict(exclude_unset=True).items()
        if v is not None
    }
    
    if not update_data:
        raise ValidationError(
            message="No fields to update",
            details={"provided_fields": list(data.dict(exclude_unset=True).keys())}
        )
    
    # Update location
    location = await location_repo.update(location_id, **update_data)
    
    if not location:
        raise RecordNotFoundError("Location", str(location_id))
    
    logger.info("Location updated", extra={"location_id": str(location.id)})
    
    return LocationResponse(
        id=location.id,
        name=location.name,
        description=location.description,
        latitude=location.latitude,
        longitude=location.longitude,
        elevation=location.elevation,
        country=location.country,
        region=location.region,
        city=location.city,
        location_type=location.location_type,
        geometry={
            "type": "Point",
            "coordinates": [location.longitude, location.latitude]
        },
        metadata=location.metadata or {},
        created_at=location.created_at.isoformat() if location.created_at else "",
        updated_at=location.updated_at.isoformat() if location.updated_at else ""
    )


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> None:
    """
    Delete location (soft delete).
    
    Args:
        location_id: Location ID
        db: Database session
        current_user: Authenticated user
        
    Raises:
        RecordNotFoundError: If location not found
    """
    location_repo = LocationRepository(db)
    success = await location_repo.delete(location_id, soft=True)
    
    if not success:
        raise RecordNotFoundError("Location", str(location_id))
    
    logger.info("Location deleted", extra={"location_id": str(location_id)})


# ============================================================================
# SPATIAL QUERY ENDPOINTS
# ============================================================================

@router.post("/nearby", response_model=List[LocationWithDistance])
async def find_nearby_locations(
    search: NearbySearchRequest,
    db: AsyncSession = Depends(get_db)
) -> List[LocationWithDistance]:
    """
    Find locations within radius using PostGIS spatial query.
    
    Args:
        search: Nearby search parameters
        db: Database session
        
    Returns:
        list: Locations with distance information
        
    Performance: O(log n) with spatial index
    """
    logger.info(
        "Nearby location search",
        extra={
            "center": f"({search.latitude}, {search.longitude})",
            "radius_km": search.radius_km
        }
    )
    
    try:
        # Create center point (SRID 4326 = WGS84)
        center_point = func.ST_SetSRID(
            func.ST_MakePoint(search.longitude, search.latitude),
            4326
        )
        
        # Build query with ST_DWithin for efficiency
        # Convert km to meters and use geography type for accurate earth-surface distance
        radius_meters = search.radius_km * 1000
        
        query = select(
            Location,
            func.ST_Distance(
                func.ST_Transform(Location.geometry, 4326).cast(Geography(geometry_type='POINT')),
                center_point.cast(Geography(geometry_type='POINT'))
            ).label('distance_meters')
        ).where(
            Location.is_deleted == False
        ).where(
            func.ST_DWithin(
                func.ST_Transform(Location.geometry, 4326).cast(Geography(geometry_type='POINT')),
                center_point.cast(Geography(geometry_type='POINT')),
                radius_meters
            )
        )
        
        # Add location type filter if provided
        if search.location_type:
            query = query.where(Location.location_type == search.location_type)
        
        # Order by distance and limit
        query = query.order_by(text('distance_meters')).limit(search.limit)
        
        result = await db.execute(query)
        rows = result.all()
        
        # Convert to response format
        locations_with_distance = [
            LocationWithDistance(
                id=row.Location.id,
                name=row.Location.name,
                description=row.Location.description,
                latitude=row.Location.latitude,
                longitude=row.Location.longitude,
                elevation=row.Location.elevation,
                country=row.Location.country,
                region=row.Location.region,
                city=row.Location.city,
                location_type=row.Location.location_type,
                geometry={
                    "type": "Point",
                    "coordinates": [row.Location.longitude, row.Location.latitude]
                },
                distance_km=round(row.distance_meters / 1000, 2),
                metadata=row.Location.metadata or {}
            )
            for row in rows
        ]
        
        logger.info(
            "Found nearby locations",
            extra={"count": len(locations_with_distance)}
        )
        
        return locations_with_distance
    
    except Exception as e:
        logger.error("Nearby search failed", error=e)
        raise DatabaseError(
            message="Failed to execute spatial query",
            details={"error": str(e)}
        )


@router.get("/geojson", response_model=Dict[str, Any])
async def get_locations_geojson(
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    country: str | None = Query(default=None),
    location_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get locations as GeoJSON FeatureCollection.
    
    Args:
        limit: Maximum results
        offset: Results to skip
        country: Filter by country
        location_type: Filter by location type
        db: Database session
        
    Returns:
        dict: GeoJSON FeatureCollection
    """
    location_repo = LocationRepository(db)
    
    # Get locations
    if country:
        locations = await location_repo.get_by_country(country, limit=limit)
    elif location_type:
        locations = await location_repo.get_by_type(location_type, limit=limit)
    else:
        locations = await location_repo.get_all(limit=limit, offset=offset)
    
    # Build GeoJSON FeatureCollection
    features = [location_to_geojson(loc) for loc in locations]
    
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "count": len(features),
            "limit": limit,
            "offset": offset
        }
    }


# ============================================================================
# BULK OPERATIONS
# ============================================================================

@router.post("/bulk", response_model=BulkCreateResponse, status_code=status.HTTP_201_CREATED)
async def bulk_create_locations(
    data: BulkCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> BulkCreateResponse:
    """
    Create multiple locations in bulk.
    
    Args:
        data: Bulk creation request
        db: Database session
        current_user: Authenticated user
        
    Returns:
        BulkCreateResponse: Created locations
        
    Performance: O(n) with batch insert
    """
    logger.info(
        "Bulk location creation",
        extra={
            "count": len(data.locations),
            "user_id": str(current_user["id"])
        }
    )
    
    location_repo = LocationRepository(db)
    
    # Prepare location data
    locations_data = [
        {
            "name": loc.name,
            "description": loc.description,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "elevation": loc.elevation,
            "country": loc.country,
            "region": loc.region,
            "city": loc.city,
            "location_type": loc.location_type,
            "metadata": loc.metadata or {},
            "user_id": UUID(current_user["id"])
        }
        for loc in data.locations
    ]
    
    # Bulk create
    created_locations = await location_repo.bulk_create(locations_data)
    
    logger.info(
        "Bulk creation completed",
        extra={"created_count": len(created_locations)}
    )
    
    # Convert to response
    location_responses = [
        LocationResponse(
            id=loc.id,
            name=loc.name,
            description=loc.description,
            latitude=loc.latitude,
            longitude=loc.longitude,
            elevation=loc.elevation,
            country=loc.country,
            region=loc.region,
            city=loc.city,
            location_type=loc.location_type,
            geometry={
                "type": "Point",
                "coordinates": [loc.longitude, loc.latitude]
            },
            metadata=loc.metadata or {},
            created_at=loc.created_at.isoformat() if loc.created_at else "",
            updated_at=loc.updated_at.isoformat() if loc.updated_at else ""
        )
        for loc in created_locations
    ]
    
    return BulkCreateResponse(
        created_count=len(created_locations),
        locations=location_responses
    )


# Note: For production, add Geography import
try:
    from geoalchemy2 import Geography
except ImportError:
    # Fallback if geoalchemy2 not fully installed
    Geography = lambda **kwargs: text('geography')


# Export router
__all__ = ["router"]
