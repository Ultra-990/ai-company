from app.services.model_routing import executable, route_for_packet, route_for_service


def test_default_route_is_bounded_ollama():
    route = route_for_service(None)
    assert route.service_key == "default"
    assert route.provider == "ollama"
    assert executable(route)


def test_brand_adapter_is_visible_but_not_live():
    route = route_for_service("restaurant_branding")
    assert route.adapter_id == "brand-text-sft-1f0a_7s5"
    assert not route.enabled
    assert not executable(route)


def test_free_form_packet_does_not_change_route():
    route = route_for_packet({"task_context": {"brief": "restaurant branding"}})
    assert route.service_key == "default"

