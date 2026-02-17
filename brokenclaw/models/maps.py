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


class WindInfo(BaseModel):
    speed: str | None = None
    direction: str | None = None
    gust: str | None = None


class CurrentWeather(BaseModel):
    temperature: str | None = None
    feels_like: str | None = None
    humidity: int | None = None
    description: str | None = None
    wind: WindInfo | None = None
    uv_index: int | None = None
    visibility: str | None = None
    cloud_cover: int | None = None
    is_daytime: bool | None = None
    time_zone: str | None = None


class DailyForecast(BaseModel):
    date: str
    high_temperature: str | None = None
    low_temperature: str | None = None
    description: str | None = None
    precipitation_probability: int | None = None


class TimezoneResult(BaseModel):
    time_zone_id: str
    time_zone_name: str
    raw_offset: int
    dst_offset: int
