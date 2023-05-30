import pytest
from your_module import update_connect_config, save_variable_to_json, get_variable_from_json

def test_update_connect_config(mocker):
    # Mock the save_variable_to_json and get_variable_from_json functions
    mocker.patch('your_module.save_variable_to_json')
    mocker.patch('your_module.get_variable_from_json', side_effect=lambda key: f"mocked_{key}")

    api_url = "https://example.com"
    api_token = "test_token"

    result = update_connect_config(api_url, api_token)

    # Check if the save_variable_to_json function was called with the correct arguments
    your_module.save_variable_to_json.assert_any_call('api_gateway_url', f"{api_url}/")
    your_module.save_variable_to_json.assert_any_call('api_token', api_token)

    # Check if the get_variable_from_json function was called with the correct arguments
    your_module.get_variable_from_json.assert_any_call('api_gateway_url')
    your_module.get_variable_from_json.assert_any_call('api_token')

    assert result == "config updated to local config!"