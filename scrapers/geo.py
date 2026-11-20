"""Linnavalik: millisesse piirkonda (linn või maakond) mäng kuulub. Seadistus: config.toml [geo]."""

from __future__ import annotations

from dataclasses import dataclass

ALL = "eesti"


@dataclass(frozen=True)
class Region:
    slug: str
    name: str        # valikus näidatav nimi
    in_form: str     # "Tallinnas", "Harjumaal", "Eestis"
    kind: str        # "all" | "city" | "county"

    @property
    def prefix(self) -> str:
        """Kaust lehe juurest: vaikelinn on juurkaustas, teised oma kaustas."""
        return "" if self.slug == Geo.default_slug else f"{self.slug}/"


class Geo:
    default_slug = "tallinn"

    def __init__(self, cfg: dict) -> None:
        geo = cfg.get("geo", {})
        Geo.default_slug = geo.get("default", "tallinn")
        self.foreign = set(geo.get("foreign", []))
        self.cities = {c["name"]: c for c in geo.get("city", [])}
        self.places = dict(geo.get("place", {}))
        self.counties = dict(geo.get("county", {}))
        self.all = Region(ALL, "Kogu Eesti", "Eestis", "all")
        self.city_regions = {name: Region(c["slug"], name, c["in"], "city") for name, c in self.cities.items()}
        self.county_regions = {
            county: Region(v["slug"], self.county_label(county), v["in"], "county") for county, v in self.counties.items()
        }

    def county_of(self, city: str) -> str | None:
        if city in self.cities:
            return self.cities[city]["county"]
        return self.places.get(city)

    def is_estonian(self, city: str) -> bool:
        return city in self.cities or city in self.places

    def is_known(self, city: str) -> bool:
        return self.is_estonian(city) or city in self.foreign

    def region_of(self, city: str) -> Region | None:
        """Linn → linna piirkond; väiksem koht → maakond (nt "Harjumaa (v.a Tallinn)")."""
        if city in self.city_regions:
            return self.city_regions[city]
        county = self.places.get(city)
        return self.county_regions.get(county) if county else None

    def county_label(self, county: str) -> str:
        """Maakonna nimi valikus: kui maakonnas on eraldi linn, lisatakse "(v.a <linn>)"."""
        excluded = [name for name, c in self.cities.items() if c["county"] == county]
        return f"{county} (v.a {', '.join(excluded)})" if excluded else county
