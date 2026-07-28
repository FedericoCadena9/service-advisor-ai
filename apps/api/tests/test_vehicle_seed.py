from service_advisor_api.vehicles import CanonicalVehicleStore


def test_seed_is_reproducible_and_limited_to_its_shop() -> None:
    store = CanonicalVehicleStore()

    store.seed()
    store.seed()

    matches = store.search(shop_id="demo-shop", query="civic")

    assert len(matches) == 1
    assert matches[0].is_demo_data is True
    assert matches[0].customer_label == "Demo Customer"
    assert store.search(shop_id="another-shop", query="civic") == []


def test_canonical_vehicle_exposes_prior_mileage_context() -> None:
    store = CanonicalVehicleStore()
    store.seed()

    vehicle = store.get(shop_id="demo-shop", vehicle_id="honda-civic-2019-lx")

    assert vehicle is not None
    assert vehicle.model == "Civic"
    assert vehicle.prior_mileage_km == 42_500
    assert vehicle.prior_mileage_recorded_on == "2026-06-15"
