from pydantic import BaseModel


class LatLng(BaseModel):
    lat: float
    lng: float


class GeocodeResult(BaseModel):
    formatted_address: str
    location: LatLng
    place_id: str


class DirectionsStep(BaseModel):
    instruction: str
    distance: str
    duration: str


class DirectionsRoute(BaseModel):
    summary: str
    distance: str
    duration: str
    start_address: str
    end_address: str
    steps: list[DirectionsStep]


class PlaceResult(BaseModel):
    name: str
    address: str
    place_id: str
    rating: float | None = None
    types: list[str] = []
    location: LatLng | None = None


class PlaceDetail(BaseModel):
    name: str
    address: str
    place_id: str
    phone: str | None = None
    website: str | None = None
    rating: float | None = None
    total_ratings: int | None = None
    types: list[str] = []
    location: LatLng | None = None
    url: str | None = None


class DistanceMatrixEntry(BaseModel):
    origin: str
    destination: str
    distance: str | None = None
    duration: str | None = None
    status: str
